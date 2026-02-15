"""
Queue Management Database Model
"""
from sqlalchemy import Column, Integer, String, DateTime, Enum, Float, Boolean
from sqlalchemy.sql import func
import enum
from app.db.session import Base


class QueueStatus(str, enum.Enum):
    """Queue status enumeration"""
    WAITING = "waiting"
    CALLED = "called"
    IN_SERVICE = "in_service"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    LEFT = "left"


class Queue(Base):
    """Queue model for real-time queue management"""
    
    __tablename__ = "queues"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Queue Information
    queue_date = Column(DateTime(timezone=True), nullable=False, index=True)
    department = Column(String, nullable=False, index=True)
    queue_number = Column(Integer, nullable=False)
    
    # Patient and Appointment
    patient_id = Column(Integer, nullable=False, index=True)
    appointment_id = Column(Integer, nullable=True, index=True)
    patient_name = Column(String, nullable=False)
    
    # Queue Status
    status = Column(Enum(QueueStatus), default=QueueStatus.WAITING, nullable=False)
    priority_level = Column(String, default="medium", nullable=False)
    priority_score = Column(Float, default=1.0, nullable=False)
    
    # Timing Information
    check_in_time = Column(DateTime(timezone=True), nullable=False)
    called_time = Column(DateTime(timezone=True), nullable=True)
    service_start_time = Column(DateTime(timezone=True), nullable=True)
    service_end_time = Column(DateTime(timezone=True), nullable=True)
    estimated_wait_time = Column(Integer, nullable=True)  # in minutes
    actual_wait_time = Column(Integer, nullable=True)  # in minutes
    
    # Service Information
    service_type = Column(String, nullable=False)
    doctor_name = Column(String, nullable=True)
    room_number = Column(String, nullable=True)
    
    # Flags
    is_emergency = Column(Boolean, default=False)
    notified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Queue {self.queue_number} - {self.patient_name} ({self.status})>"