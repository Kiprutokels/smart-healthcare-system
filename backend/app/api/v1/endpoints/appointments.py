"""
Appointment Management API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.db.session import get_db
from app.models.user import User
from app.models.appointment import Appointment, AppointmentStatus
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentResponse,
    AppointmentWithDetails,
    AppointmentStatusUpdate
)
from app.core.security import get_current_user
from app.services.ai.noshow_predictor import no_show_predictor
from app.schemas.ai import NoShowPredictionRequest

router = APIRouter(prefix="/appointments", tags=["Appointments"])


def _enum_to_str(v):
    if v is None:
        return None
    return v.value if hasattr(v, "value") else str(v)


@router.post("/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    appointment_data: AppointmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new appointment
    """
    # Set patient_id from current user if not provided (for patient role)
    if current_user.role == "patient":
        patient_id = current_user.id
    else:
        patient_id = appointment_data.patient_id or current_user.id

    # Verify doctor exists
    doctor = db.query(User).filter(User.id == appointment_data.doctor_id).first()
    if not doctor or doctor.role not in ["doctor", "nurse"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )

    # Check for appointment conflicts
    existing = db.query(Appointment).filter(
        Appointment.doctor_id == appointment_data.doctor_id,
        Appointment.appointment_date == appointment_data.appointment_date,
        Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED])
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Doctor already has an appointment at this time"
        )

    # Create appointment
    new_appointment = Appointment(
        patient_id=patient_id,
        doctor_id=appointment_data.doctor_id,
        appointment_date=appointment_data.appointment_date,
        appointment_type=appointment_data.appointment_type,
        duration_minutes=appointment_data.duration_minutes,
        chief_complaint=appointment_data.chief_complaint,
        symptoms=appointment_data.symptoms,
        status=AppointmentStatus.SCHEDULED
    )

    db.add(new_appointment)
    db.commit()
    db.refresh(new_appointment)

    # Predict no-show probability
    try:
        patient = db.query(User).filter(User.id == patient_id).first()

        previous_appointments = db.query(Appointment).filter(
            Appointment.patient_id == patient_id
        ).count()

        previous_no_shows = db.query(Appointment).filter(
            Appointment.patient_id == patient_id,
            Appointment.status == AppointmentStatus.NO_SHOW
        ).count()

        lead_time_days = int((appointment_data.appointment_date - datetime.now()).days)
        lead_time_days = max(0, lead_time_days)  # clamp negative

        prediction_request = NoShowPredictionRequest(
            appointment_id=new_appointment.id,
            patient_id=patient_id,
            appointment_date=appointment_data.appointment_date,
            appointment_type=_enum_to_str(appointment_data.appointment_type) or "consultation",
            age=None,  # Calculate from patient DOB if available
            gender=getattr(patient, "gender", None) if patient else None,
            previous_no_shows=previous_no_shows,
            previous_appointments=previous_appointments,
            sms_reminder=False,
            lead_time_days=lead_time_days
        )

        prediction = no_show_predictor.predict(prediction_request)
        new_appointment.no_show_probability = prediction.no_show_probability
        db.commit()
        db.refresh(new_appointment)

    except Exception as e:
        # keep as print to avoid breaking appointment creation
        print(f"⚠️ No-show prediction failed: {e}")

    return new_appointment


@router.get("/", response_model=List[AppointmentWithDetails])
def list_appointments(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[AppointmentStatus] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List appointments with filtering
    """
    query = db.query(Appointment)

    # Filter based on user role
    if current_user.role == "patient":
        query = query.filter(Appointment.patient_id == current_user.id)
    elif current_user.role == "doctor":
        query = query.filter(Appointment.doctor_id == current_user.id)
    # Admins can see all appointments

    # Apply filters
    if status:
        query = query.filter(Appointment.status == status)
    if date_from:
        query = query.filter(Appointment.appointment_date >= date_from)
    if date_to:
        query = query.filter(Appointment.appointment_date <= date_to)

    query = query.order_by(Appointment.appointment_date.desc())
    appointments = query.offset(skip).limit(limit).all()

    result = []
    for apt in appointments:
        patient = db.query(User).filter(User.id == apt.patient_id).first()
        doctor = db.query(User).filter(User.id == apt.doctor_id).first()

        apt_dict = {
            **apt.__dict__,
            "patient_name": patient.full_name if patient else None,
            "doctor_name": doctor.full_name if doctor else None,
            "patient_phone": patient.phone if patient else None,
            "patient_email": patient.email if patient else None
        }
        result.append(apt_dict)

    return result


@router.get("/{appointment_id}", response_model=AppointmentWithDetails)
def get_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get appointment details
    """
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )

    # Check authorization
    if current_user.role == "patient" and appointment.patient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this appointment"
        )
    elif current_user.role == "doctor" and appointment.doctor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this appointment"
        )

    patient = db.query(User).filter(User.id == appointment.patient_id).first()
    doctor = db.query(User).filter(User.id == appointment.doctor_id).first()

    return {
        **appointment.__dict__,
        "patient_name": patient.full_name if patient else None,
        "doctor_name": doctor.full_name if doctor else None,
        "patient_phone": patient.phone if patient else None,
        "patient_email": patient.email if patient else None
    }


@router.put("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: int,
    appointment_data: AppointmentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update appointment details
    """
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )

    # Check authorization
    if current_user.role == "patient" and appointment.patient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this appointment"
        )

    update_data = appointment_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(appointment, field, value)

    appointment.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(appointment)

    return appointment


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancel an appointment
    """
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )

    # Check authorization
    if current_user.role == "patient" and appointment.patient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to cancel this appointment"
        )

    appointment.status = AppointmentStatus.CANCELLED
    appointment.updated_at = datetime.utcnow()
    db.commit()

    return None


@router.patch("/{appointment_id}/status", response_model=AppointmentResponse)
def update_appointment_status(
    appointment_id: int,
    status_update: AppointmentStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update appointment status (for doctors/admins)
    """
    if current_user.role not in ["doctor", "nurse", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update appointment status"
        )

    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )

    appointment.status = status_update.status
    if status_update.notes:
        appointment.notes = status_update.notes

    if status_update.status == AppointmentStatus.IN_PROGRESS:
        appointment.actual_start_time = datetime.utcnow()
    elif status_update.status == AppointmentStatus.COMPLETED:
        appointment.actual_end_time = datetime.utcnow()

    appointment.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(appointment)

    return appointment
