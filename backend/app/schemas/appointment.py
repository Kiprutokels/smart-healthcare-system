"""
Appointment Pydantic Schemas
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.appointment import AppointmentStatus, AppointmentType, PriorityLevel


class AppointmentBase(BaseModel):
    """Base appointment schema"""
    appointment_date: datetime
    appointment_type: AppointmentType
    duration_minutes: int = 30
    chief_complaint: Optional[str] = None
    symptoms: Optional[str] = None


class AppointmentCreate(AppointmentBase):
    """Schema for creating a new appointment"""
    doctor_id: int
    patient_id: Optional[int] = None  # Will be set from current user if not provided


class AppointmentUpdate(BaseModel):
    """Schema for updating appointment"""
    appointment_date: Optional[datetime] = None
    appointment_type: Optional[AppointmentType] = None
    status: Optional[AppointmentStatus] = None
    priority: Optional[PriorityLevel] = None
    chief_complaint: Optional[str] = None
    symptoms: Optional[str] = None
    vital_signs: Optional[str] = None
    diagnosis: Optional[str] = None
    prescription: Optional[str] = None
    notes: Optional[str] = None


class AppointmentResponse(AppointmentBase):
    """Schema for appointment response"""
    id: int
    patient_id: int
    doctor_id: int
    status: AppointmentStatus
    priority: PriorityLevel
    estimated_wait_time: Optional[int] = None
    no_show_probability: Optional[float] = None
    queue_position: Optional[int] = None
    checked_in: bool
    reminder_sent: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class AppointmentWithDetails(AppointmentResponse):
    """Schema for appointment with user details"""
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None
    patient_phone: Optional[str] = None
    patient_email: Optional[str] = None


class AppointmentStatusUpdate(BaseModel):
    """Schema for updating appointment status"""
    status: AppointmentStatus
    notes: Optional[str] = None


class AppointmentConfirmation(BaseModel):
    """Schema for appointment confirmation"""
    confirmed: bool
    confirmation_notes: Optional[str] = None