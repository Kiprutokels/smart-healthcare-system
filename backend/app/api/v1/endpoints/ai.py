"""
AI Services API Endpoints
"""
from __future__ import annotations

from datetime import datetime
from typing import List

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.appointment import Appointment, AppointmentStatus
from app.models.user import User
from app.schemas.ai import (
    BatchPredictionRequest,
    BatchPredictionResponse,
    NoShowPredictionRequest,
    NoShowPredictionResponse,
    PriorityClassificationRequest,
    PriorityClassificationResponse,
    QueueOptimizationRequest,
    QueueOptimizationResponse,
    WaitTimePredictionRequest,
    WaitTimePredictionResponse,
)
from app.services.ai.noshow_predictor import no_show_predictor
from app.services.ai.priority_classifier import priority_classifier
from app.services.ai.waittime_estimator import wait_time_estimator
from backend.app.core.internal_auth import verify_internal_api_key

router = APIRouter(prefix="/ai", tags=["AI Services"])


def _enum_to_str(v):
    """Convert Enum-like values to string safely."""
    if v is None:
        return None
    return v.value if hasattr(v, "value") else str(v)


def _time_of_day_from_hour(hour: int) -> str:
    if hour < 12:
        return "morning"
    if hour < 17:
        return "afternoon"
    return "evening"


@router.post("/predict-noshow", response_model=NoShowPredictionResponse)
def predict_no_show(
    request: NoShowPredictionRequest,
    _: str = Depends(verify_internal_api_key),
    db: Session = Depends(get_db),
):
    """
    Predict no-show probability.

    Modes:
    1) appointment_id provided -> enrich from DB
    2) full payload provided -> use payload
    """
    if request.appointment_id:
        appointment = db.query(Appointment).filter(Appointment.id == request.appointment_id).first()
        if not appointment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

        request.patient_id = appointment.patient_id
        request.appointment_date = appointment.appointment_date
        request.appointment_type = _enum_to_str(appointment.appointment_type) or request.appointment_type

        request.previous_appointments = (
            db.query(Appointment).filter(Appointment.patient_id == appointment.patient_id).count()
        )

        request.previous_no_shows = (
            db.query(Appointment)
            .filter(
                Appointment.patient_id == appointment.patient_id,
                Appointment.status == AppointmentStatus.NO_SHOW,
            )
            .count()
        )

    prediction = no_show_predictor.predict(request)

    if request.appointment_id:
        appointment = db.query(Appointment).filter(Appointment.id == request.appointment_id).first()
        if appointment:
            appointment.no_show_probability = prediction.no_show_probability
            db.commit()

    return prediction


@router.post("/estimate-wait-time", response_model=WaitTimePredictionResponse)
def estimate_wait_time(
    request: WaitTimePredictionRequest,
    _: str = Depends(verify_internal_api_key),
    db: Session = Depends(get_db),
):
    """
    Estimate wait time.
    
    """
    if request.current_queue_length is None:
        request.current_queue_length = (
            db.query(Appointment)
            .filter(
                Appointment.doctor_id == request.doctor_id,
                func.date(Appointment.appointment_date) == request.appointment_date.date(),
                Appointment.status.in_(
                    [
                        AppointmentStatus.SCHEDULED,
                        AppointmentStatus.CONFIRMED,
                        AppointmentStatus.IN_PROGRESS,
                    ]
                ),
            )
            .count()
        )

    # If caller passed junk/blank strings for these, normalize
    if not request.time_of_day:
        request.time_of_day = _time_of_day_from_hour(request.appointment_date.hour)
    if not request.day_of_week:
        request.day_of_week = request.appointment_date.strftime("%A")

    estimation = wait_time_estimator.predict(request)

    if request.appointment_id:
        appointment = db.query(Appointment).filter(Appointment.id == request.appointment_id).first()
        if appointment:
            appointment.estimated_wait_time = estimation.estimated_wait_time
            appointment.queue_position = estimation.queue_position
            db.commit()

    return estimation


@router.post("/classify-priority", response_model=PriorityClassificationResponse)
def classify_priority(
    request: PriorityClassificationRequest,
    _: str = Depends(verify_internal_api_key),
    db: Session = Depends(get_db),
):
    """
    Classify patient priority based on symptoms and medical information
    """
    patient = db.query(User).filter(User.id == request.patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    if not request.medical_history and getattr(patient, "medical_history", None):
        request.medical_history = patient.medical_history

    classification = priority_classifier.classify(request)

    if request.appointment_id:
        appointment = db.query(Appointment).filter(Appointment.id == request.appointment_id).first()
        if appointment:
            appointment.ai_priority_score = classification.priority_score
            appointment.priority = classification.priority_level
            db.commit()

    return classification


@router.post("/optimize-queue", response_model=QueueOptimizationResponse)
def optimize_queue(
    request: QueueOptimizationRequest,
    _: str = Depends(verify_internal_api_key),
    db: Session = Depends(get_db),
):
    """
    Optimize appointment queue based on AI predictions
    """
    if current_user.role not in ["doctor", "nurse", "admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to optimize queue")

    query = db.query(Appointment).filter(
        func.date(Appointment.appointment_date) == request.date.date(),
        Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]),
    )

    if request.doctor_id:
        query = query.filter(Appointment.doctor_id == request.doctor_id)

    appointments = query.all()

    if not appointments:
        return QueueOptimizationResponse(
            optimized_queue=[],
            total_appointments=0,
            estimated_completion_time=request.date,
            efficiency_score=0.0,
            changes_made=0,
        )

    priority_weights = {"emergency": 4.0, "high": 3.0, "medium": 2.0, "low": 1.0}

    scored_appointments = []
    for apt in appointments:
        score = 0.0

        apt_priority = _enum_to_str(getattr(apt, "priority", None)) or "medium"
        score += priority_weights.get(apt_priority, 2.0)

        if apt.no_show_probability is not None:
            score += (1.0 - float(apt.no_show_probability)) * 0.5

        if apt.ai_priority_score is not None:
            score += float(apt.ai_priority_score) * 2.0

        scored_appointments.append(
            {
                "appointment_id": apt.id,
                "patient_id": apt.patient_id,
                "priority_score": score,
                "priority_level": apt_priority,
                "no_show_probability": apt.no_show_probability,
                "appointment_time": apt.appointment_date.isoformat(),
                "original_position": apt.queue_position or 0,
            }
        )

    scored_appointments.sort(key=lambda x: x["priority_score"], reverse=True)

    changes_made = 0
    for idx, apt_data in enumerate(scored_appointments, start=1):
        apt_data["new_position"] = idx
        if apt_data["original_position"] != idx:
            changes_made += 1
            row = db.query(Appointment).filter(Appointment.id == apt_data["appointment_id"]).first()
            if row:
                row.queue_position = idx

    db.commit()

    total_duration = 0
    for apt_data in scored_appointments:
        row = db.query(Appointment).filter(Appointment.id == apt_data["appointment_id"]).first()
        if row:
            total_duration += int(row.duration_minutes or 0)

    estimated_completion = request.date + pd.Timedelta(minutes=total_duration)
    efficiency_score = 1.0 - (changes_made / len(scored_appointments)) if scored_appointments else 0.0

    return QueueOptimizationResponse(
        optimized_queue=scored_appointments,
        total_appointments=len(scored_appointments),
        estimated_completion_time=estimated_completion,
        efficiency_score=round(efficiency_score, 3),
        changes_made=changes_made,
    )


@router.post("/batch-predict", response_model=BatchPredictionResponse)
def batch_predict(
    request: BatchPredictionRequest,
    _: str = Depends(verify_internal_api_key),
    db: Session = Depends(get_db),
):
    """
    Run batch predictions on multiple appointments
    """
    predictions = []
    failed_predictions = []

    for appointment_id in request.appointment_ids:
        try:
            appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
            if not appointment:
                failed_predictions.append(appointment_id)
                continue

            if request.prediction_type == "no_show":
                pred_request = NoShowPredictionRequest(
                    appointment_id=appointment_id,
                    patient_id=appointment.patient_id,
                    appointment_date=appointment.appointment_date,
                    appointment_type=_enum_to_str(appointment.appointment_type) or "consultation",
                    previous_no_shows=0,
                    previous_appointments=0,
                )
                result = no_show_predictor.predict(pred_request)
                predictions.append({"appointment_id": appointment_id, "type": "no_show", "result": result.model_dump()})

            elif request.prediction_type == "wait_time":
                pred_request = WaitTimePredictionRequest(
                    appointment_id=appointment_id,
                    doctor_id=appointment.doctor_id,
                    appointment_date=appointment.appointment_date,
                    appointment_type=_enum_to_str(appointment.appointment_type) or "consultation",
                    current_queue_length=0,
                    time_of_day=_time_of_day_from_hour(appointment.appointment_date.hour),
                    day_of_week=appointment.appointment_date.strftime("%A"),
                )
                result = wait_time_estimator.predict(pred_request)
                predictions.append({"appointment_id": appointment_id, "type": "wait_time", "result": result.model_dump()})

            else:
                failed_predictions.append(appointment_id)

        except Exception:
            failed_predictions.append(appointment_id)

    return BatchPredictionResponse(
        predictions=predictions,
        total_processed=len(predictions),
        failed_predictions=failed_predictions,
    )


@router.get("/health")
def check_ai_service_health():
    """
    Check if AI services are loaded and healthy
    """
    return {
        "no_show_predictor": no_show_predictor.model is not None,
        "wait_time_estimator": wait_time_estimator.model is not None,
        "priority_classifier": priority_classifier.model is not None,
        "status": "healthy",
    }
