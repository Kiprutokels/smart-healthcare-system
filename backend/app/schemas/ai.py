"""
AI/ML Prediction Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Literal
from datetime import datetime


class NoShowPredictionRequest(BaseModel):
    """Request schema for no-show prediction"""
    appointment_id: Optional[int] = None
    patient_id: int
    appointment_date: datetime
    appointment_type: str
    age: Optional[int] = None
    gender: Optional[str] = None
    previous_no_shows: int = 0
    previous_appointments: int = 0
    sms_reminder: bool = False
    lead_time_days: Optional[int] = None


class NoShowPredictionResponse(BaseModel):
    """Response schema for no-show prediction"""
    appointment_id: Optional[int] = None
    no_show_probability: float = Field(..., ge=0.0, le=1.0)
    risk_level: str  # "low", "medium", "high"
    confidence: float = Field(..., ge=0.0, le=1.0)
    factors: List[Dict[str, float]]


class WaitTimePredictionRequest(BaseModel):
    """
    Request schema for wait time prediction

    Efficiency fix:
    - current_queue_length is Optional so API can auto-fill when missing,
      while still allowing an explicit 0 if you want.
    """
    appointment_id: Optional[int] = None
    doctor_id: int
    appointment_date: datetime
    appointment_type: str

    current_queue_length: Optional[int] = None

    time_of_day: str
    day_of_week: str

    # Optional additions (do not break old clients)
    age: Optional[int] = None
    gender: Optional[str] = None


class WaitTimePredictionResponse(BaseModel):
    """Response schema for wait time prediction"""
    appointment_id: Optional[int] = None
    estimated_wait_time: int
    confidence_interval: Dict[str, int]
    queue_position: Optional[int] = None


class PriorityClassificationRequest(BaseModel):
    """Request schema for priority classification"""
    appointment_id: Optional[int] = None
    patient_id: int
    chief_complaint: str
    symptoms: Optional[str] = None
    vital_signs: Optional[Dict[str, float]] = None
    age: int
    medical_history: Optional[str] = None
    appointment_type: str


class PriorityClassificationResponse(BaseModel):
    """Response schema for priority classification"""
    appointment_id: Optional[int] = None
    priority_level: str  # "emergency", "high", "medium", "low"
    priority_score: float = Field(..., ge=0.0, le=1.0)
    recommended_action: str
    reasoning: List[str]


class QueueOptimizationRequest(BaseModel):
    """Request schema for queue optimization"""
    date: datetime
    department: Optional[str] = None
    doctor_id: Optional[int] = None
    include_predictions: bool = True


class QueueOptimizationResponse(BaseModel):
    """Response schema for queue optimization"""
    optimized_queue: List[Dict]
    total_appointments: int
    estimated_completion_time: datetime
    efficiency_score: float
    changes_made: int


class BatchPredictionRequest(BaseModel):
    """Request schema for batch predictions"""
    appointment_ids: List[int]
    prediction_type: Literal["no_show", "wait_time", "priority"]


class BatchPredictionResponse(BaseModel):
    """Response schema for batch predictions"""
    predictions: List[Dict]
    total_processed: int
    failed_predictions: List[int]
