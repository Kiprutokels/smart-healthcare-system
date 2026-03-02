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

from app.core.internal_auth import verify_internal_api_key
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

router = APIRouter(prefix="/ai", tags=["AI Services"])


# ── Helpers ──────────────────────────────────────────────────────────────────

def _enum_to_str(v) -> str | None:
    """Safely convert an Enum (or plain value) to string."""
    if v is None:
        return None
    return v.value if hasattr(v, "value") else str(v)


def _time_of_day(hour: int) -> str:
    if hour < 12:
        return "morning"
    if hour < 17:
        return "afternoon"
    return "evening"


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/predict-noshow", response_model=NoShowPredictionResponse)
def predict_no_show(
    request: NoShowPredictionRequest,
    _: str = Depends(verify_internal_api_key),
    db: Session = Depends(get_db),
):
    """
    Predict no-show probability.

    • Mode 1 — appointment_id supplied → enrich all fields from DB automatically.
    • Mode 2 — full payload supplied    → use payload as-is.
    """
    if request.appointment_id:
        appt = db.query(Appointment).filter(Appointment.id == request.appointment_id).first()
        if not appt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

        request.patient_id         = appt.patient_id
        request.appointment_date   = appt.appointment_date
        request.appointment_type   = _enum_to_str(appt.appointment_type) or request.appointment_type
        request.previous_appointments = (
            db.query(Appointment)
            .filter(Appointment.patient_id == appt.patient_id)
            .count()
        )
        request.previous_no_shows = (
            db.query(Appointment)
            .filter(
                Appointment.patient_id == appt.patient_id,
                Appointment.status == AppointmentStatus.NO_SHOW,
            )
            .count()
        )

    prediction = no_show_predictor.predict(request)

    # Persist probability back to DB
    if request.appointment_id:
        appt = db.query(Appointment).filter(Appointment.id == request.appointment_id).first()
        if appt:
            appt.no_show_probability = prediction.no_show_probability
            db.commit()

    return prediction


@router.post("/estimate-wait-time", response_model=WaitTimePredictionResponse)
def estimate_wait_time(
    request: WaitTimePredictionRequest,
    _: str = Depends(verify_internal_api_key),
    db: Session = Depends(get_db),
):
    """Estimate wait time for an appointment."""
    if request.current_queue_length is None:
        request.current_queue_length = (
            db.query(Appointment)
            .filter(
                Appointment.doctor_id == request.doctor_id,
                func.date(Appointment.appointment_date) == request.appointment_date.date(),
                Appointment.status.in_([
                    AppointmentStatus.SCHEDULED,
                    AppointmentStatus.CONFIRMED,
                    AppointmentStatus.IN_PROGRESS,
                ]),
            )
            .count()
        )

    if not request.time_of_day:
        request.time_of_day = _time_of_day(request.appointment_date.hour)
    if not request.day_of_week:
        request.day_of_week = request.appointment_date.strftime("%A")

    estimation = wait_time_estimator.predict(request)

    if request.appointment_id:
        appt = db.query(Appointment).filter(Appointment.id == request.appointment_id).first()
        if appt:
            appt.estimated_wait_time = estimation.estimated_wait_time
            appt.queue_position      = estimation.queue_position
            db.commit()

    return estimation


@router.post("/classify-priority", response_model=PriorityClassificationResponse)
def classify_priority(
    request: PriorityClassificationRequest,
    _: str = Depends(verify_internal_api_key),
    db: Session = Depends(get_db),
):
    """Classify patient priority based on symptoms and medical information."""
    patient = db.query(User).filter(User.id == request.patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    if not request.medical_history and getattr(patient, "medical_history", None):
        request.medical_history = patient.medical_history

    classification = priority_classifier.classify(request)

    if request.appointment_id:
        appt = db.query(Appointment).filter(Appointment.id == request.appointment_id).first()
        if appt:
            appt.ai_priority_score = classification.priority_score
            appt.priority          = classification.priority_level
            db.commit()

    return classification


@router.post("/optimize-queue", response_model=QueueOptimizationResponse)
def optimize_queue(
    request: QueueOptimizationRequest,
    _: str = Depends(verify_internal_api_key),
    db: Session = Depends(get_db),
):
    """Optimise the appointment queue using AI priority scores."""
    query = (
        db.query(Appointment)
        .filter(
            func.date(Appointment.appointment_date) == request.date.date(),
            Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]),
        )
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

    scored: List[dict] = []
    for apt in appointments:
        score      = 0.0
        apt_priority = _enum_to_str(getattr(apt, "priority", None)) or "medium"
        score += priority_weights.get(apt_priority, 2.0)
        if apt.no_show_probability is not None:
            score += (1.0 - float(apt.no_show_probability)) * 0.5
        if apt.ai_priority_score is not None:
            score += float(apt.ai_priority_score) * 2.0

        scored.append({
            "appointment_id":    apt.id,
            "patient_id":        apt.patient_id,
            "priority_score":    score,
            "priority_level":    apt_priority,
            "no_show_probability": apt.no_show_probability,
            "appointment_time":  apt.appointment_date.isoformat(),
            "original_position": apt.queue_position or 0,
        })

    scored.sort(key=lambda x: x["priority_score"], reverse=True)

    changes_made = 0
    for idx, apt_data in enumerate(scored, start=1):
        apt_data["new_position"] = idx
        if apt_data["original_position"] != idx:
            changes_made += 1
            row = db.query(Appointment).filter(Appointment.id == apt_data["appointment_id"]).first()
            if row:
                row.queue_position = idx

    db.commit()

    total_duration = sum(
        int(
            (db.query(Appointment).filter(Appointment.id == a["appointment_id"]).first() or object).__dict__.get(
                "duration_minutes", 0
            ) or 0
        )
        for a in scored
    )
    estimated_completion = request.date + pd.Timedelta(minutes=total_duration)
    efficiency_score     = (1.0 - changes_made / len(scored)) if scored else 0.0

    return QueueOptimizationResponse(
        optimized_queue=scored,
        total_appointments=len(scored),
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
    """Run batch predictions across multiple appointments."""
    predictions: List[dict]  = []
    failed_predictions: List = []

    for appointment_id in request.appointment_ids:
        try:
            appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
            if not appt:
                failed_predictions.append(appointment_id)
                continue

            if request.prediction_type == "no_show":
                pred_req = NoShowPredictionRequest(
                    appointment_id=appointment_id,
                    patient_id=appt.patient_id,
                    appointment_date=appt.appointment_date,
                    appointment_type=_enum_to_str(appt.appointment_type) or "consultation",
                    previous_no_shows=0,
                    previous_appointments=0,
                )
                result = no_show_predictor.predict(pred_req)
                predictions.append({
                    "appointment_id": appointment_id,
                    "type":          "no_show",
                    "result":        result.model_dump(),
                })

            elif request.prediction_type == "wait_time":
                pred_req = WaitTimePredictionRequest(
                    appointment_id=appointment_id,
                    doctor_id=appt.doctor_id,
                    appointment_date=appt.appointment_date,
                    appointment_type=_enum_to_str(appt.appointment_type) or "consultation",
                    current_queue_length=0,
                    time_of_day=_time_of_day(appt.appointment_date.hour),
                    day_of_week=appt.appointment_date.strftime("%A"),
                )
                result = wait_time_estimator.predict(pred_req)
                predictions.append({
                    "appointment_id": appointment_id,
                    "type":          "wait_time",
                    "result":        result.model_dump(),
                })

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
def ai_health_check():
    """
    Health check for all AI models — NO auth required.
    Call this first to verify the service is up before sending predictions.
    """
    return {
        "no_show_predictor":    no_show_predictor.model is not None,
        "wait_time_estimator":  wait_time_estimator.model is not None,
        "priority_classifier":  priority_classifier.model is not None,
        "status":               "healthy",
    }
