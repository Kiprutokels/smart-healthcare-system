"""
Appointment Database Model
"""
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Float, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.session import Base


class AppointmentStatus(str, enum.Enum):
    """Appointment status enumeration"""
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    RESCHEDULED = "rescheduled"


class AppointmentType(str, enum.Enum):
    """Appointment type enumeration"""
    CONSULTATION = "consultation"
    FOLLOW_UP = "follow_up"
    LABORATORY = "laboratory"
    EMERGENCY = "emergency"
    VACCINATION = "vaccination"
    CHECKUP = "checkup"


class PriorityLevel(str, enum.Enum):
    """Priority level enumeration"""
    EMERGENCY = "emergency"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Appointment(Base):
    """Appointment model for managing patient appointments"""
    
    __tablename__ = "appointments"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Appointment Details
    appointment_date = Column(DateTime(timezone=True), nullable=False, index=True)
    appointment_type = Column(Enum(AppointmentType), nullable=False)
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.SCHEDULED, nullable=False)
    priority = Column(Enum(PriorityLevel), default=PriorityLevel.MEDIUM, nullable=False)
    
    # Duration and Timing
    duration_minutes = Column(Integer, default=30, nullable=False)
    estimated_wait_time = Column(Integer, nullable=True)  # in minutes
    actual_start_time = Column(DateTime(timezone=True), nullable=True)
    actual_end_time = Column(DateTime(timezone=True), nullable=True)
    
    # AI Predictions
    no_show_probability = Column(Float, nullable=True)  # Predicted probability of no-show
    predicted_duration = Column(Integer, nullable=True)  # Predicted appointment duration
    ai_priority_score = Column(Float, nullable=True)  # AI-calculated priority score
    
    # Clinical Information
    chief_complaint = Column(String, nullable=True)
    symptoms = Column(Text, nullable=True)
    vital_signs = Column(Text, nullable=True)  # JSON string
    diagnosis = Column(Text, nullable=True)
    prescription = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Notifications
    reminder_sent = Column(Boolean, default=False)
    reminder_sent_at = Column(DateTime(timezone=True), nullable=True)
    confirmation_required = Column(Boolean, default=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Queue Management
    queue_position = Column(Integer, nullable=True)
    checked_in = Column(Boolean, default=False)
    check_in_time = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    patient = relationship("User", back_populates="appointments", foreign_keys=[patient_id])
    doctor = relationship("User", back_populates="doctor_appointments", foreign_keys=[doctor_id])
    notifications = relationship("Notification", back_populates="appointment")
    
    def __repr__(self):
        return f"<Appointment {self.id} - {self.appointment_type} on {self.appointment_date}>"