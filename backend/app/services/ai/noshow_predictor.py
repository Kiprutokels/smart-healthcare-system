"""
No-Show Prediction AI Service
Using XGBoost for predicting appointment no-shows
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import joblib
import pandas as pd

from app.core.config import settings
from app.schemas.ai import NoShowPredictionRequest, NoShowPredictionResponse


class NoShowPredictor:
    """
    AI Service for predicting patient no-shows using XGBoost
    """

    def __init__(self):
        self.model = None
        self.feature_names = [
            "age",
            "gender_encoded",
            "appointment_type_encoded",
            "lead_time_days",
            "previous_no_shows",
            "previous_appointments",
            "sms_reminder",
            "day_of_week",
            "hour_of_day",
            "month",
            "no_show_rate",
            "appointment_history_score",
        ]
        self.load_model()

    def load_model(self):
        """Load the trained no-show prediction model"""
        try:
            model_path = settings.NO_SHOW_MODEL_PATH
            Path(model_path).parent.mkdir(parents=True, exist_ok=True)

            if os.path.exists(model_path):
                self.model = joblib.load(model_path)
                print(f"✅ No-show prediction model loaded from {model_path}")
            else:
                print(f"⚠️  No-show model not found at {model_path}")
                print("⚠️  Using fallback predictions. Train model using: python scripts/train_models.py")
                self.model = None
        except Exception as e:
            print(f"❌ Error loading no-show model: {e}")
            self.model = None

    @staticmethod
    def _safe_now_like(dt: datetime) -> datetime:
        """
        Return a 'now' datetime compatible with dt regarding timezone awareness.
        If dt is timezone-aware -> return aware now in UTC.
        If dt is naive -> return naive now.
        """
        if isinstance(dt, datetime) and dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None:
            return datetime.now(timezone.utc)
        return datetime.now()

    def preprocess_features(self, request: NoShowPredictionRequest) -> pd.DataFrame:
        prev_appts = int(request.previous_appointments or 0)
        prev_noshows = int(request.previous_no_shows or 0)

        # Compute lead_time_days safely with timezone handling
        if request.lead_time_days is not None:
            lead_time_days = int(request.lead_time_days)
        else:
            now_dt = self._safe_now_like(request.appointment_date)
            delta_days = (request.appointment_date - now_dt).days
            lead_time_days = int(delta_days)

        # Clamp lead time to reasonable bounds
        lead_time_days = max(0, min(lead_time_days, 3650))

        no_show_rate = (prev_noshows / prev_appts) if prev_appts > 0 else 0.0
        appointment_history_score = min(prev_appts / 10.0, 1.0)

        gender_map = {"male": 0, "female": 1, "other": 2, None: -1}
        gender_key = request.gender.lower() if request.gender else None
        gender_encoded = gender_map.get(gender_key, -1)

        appointment_type_map = {
            "consultation": 0,
            "follow_up": 1,
            "laboratory": 2,
            "emergency": 3,
            "vaccination": 4,
            "checkup": 5,
        }
        appointment_type_encoded = appointment_type_map.get((request.appointment_type or "").lower(), 0)

        day_of_week = request.appointment_date.weekday()
        hour_of_day = request.appointment_date.hour
        month = request.appointment_date.month

        features = {
            "age": int(request.age or 35),
            "gender_encoded": int(gender_encoded),
            "appointment_type_encoded": int(appointment_type_encoded),
            "lead_time_days": int(lead_time_days),
            "previous_no_shows": int(prev_noshows),
            "previous_appointments": int(prev_appts),
            "sms_reminder": int(bool(request.sms_reminder)),
            "day_of_week": int(day_of_week),
            "hour_of_day": int(hour_of_day),
            "month": int(month),
            "no_show_rate": float(no_show_rate),
            "appointment_history_score": float(appointment_history_score),
        }

        return pd.DataFrame([features], columns=self.feature_names)

    def predict(self, request: NoShowPredictionRequest) -> NoShowPredictionResponse:
        features_df = self.preprocess_features(request)

        if self.model:
            try:
                no_show_probability = float(self.model.predict_proba(features_df)[0][1])
                confidence = 0.85
            except Exception as e:
                print(f"❌ Prediction error: {e}")
                no_show_probability = self._fallback_prediction(request)
                confidence = 0.60
        else:
            no_show_probability = self._fallback_prediction(request)
            confidence = 0.60

        if no_show_probability >= 0.7:
            risk_level = "high"
        elif no_show_probability >= 0.4:
            risk_level = "medium"
        else:
            risk_level = "low"

        factors = self._identify_factors(features_df)

        return NoShowPredictionResponse(
            appointment_id=request.appointment_id,
            no_show_probability=round(no_show_probability, 3),
            risk_level=risk_level,
            confidence=round(confidence, 3),
            factors=factors,
        )

    def _fallback_prediction(self, request: NoShowPredictionRequest) -> float:
        base_rate = 0.20

        prev_appts = int(request.previous_appointments or 0)
        prev_noshows = int(request.previous_no_shows or 0)

        if prev_appts > 0:
            history_rate = prev_noshows / prev_appts
            base_rate = (base_rate + history_rate) / 2

        lead_time = int(request.lead_time_days or 1)
        lead_time = max(0, lead_time)

        if lead_time > 30:
            base_rate += 0.15
        elif lead_time > 14:
            base_rate += 0.10
        elif lead_time > 7:
            base_rate += 0.05

        if request.sms_reminder:
            base_rate *= 0.7

        return min(max(base_rate, 0.01), 0.95)

    def _identify_factors(self, features_df: pd.DataFrame) -> List[Dict[str, float]]:
        factors: List[Dict[str, float]] = []

        if float(features_df["no_show_rate"].values[0]) > 0.3:
            factors.append({"factor": "High previous no-show rate", "impact": 0.35})

        if int(features_df["lead_time_days"].values[0]) > 30:
            factors.append({"factor": "Long lead time (>30 days)", "impact": 0.15})

        if int(features_df["sms_reminder"].values[0]) == 0:
            factors.append({"factor": "No SMS reminder sent", "impact": 0.10})

        if float(features_df["appointment_history_score"].values[0]) < 0.3:
            factors.append({"factor": "Limited appointment history", "impact": 0.08})

        return factors


no_show_predictor = NoShowPredictor()
