"""
Priority Classification AI Service
Using Random Forest for patient priority classification
"""
from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from typing import List
from pathlib import Path

from app.core.config import settings
from app.schemas.ai import PriorityClassificationRequest, PriorityClassificationResponse


class PriorityClassifier:
    """
    AI Service for classifying patient priority using Random Forest
    Falls back to rule-based when model is missing or incompatible.
    """

    def __init__(self):
        self.model = None
        self.label_encoder = None
        self.model_enabled = True  # auto-disable if incompatible

        self.emergency_keywords = [
            "chest pain", "difficulty breathing", "severe bleeding", "unconscious",
            "stroke", "heart attack", "severe trauma", "poisoning", "seizure",
            "severe allergic reaction", "suicide attempt", "severe burn"
        ]
        self.high_priority_keywords = [
            "high fever", "severe pain", "vomiting", "dizziness", "confusion",
            "severe headache", "abdominal pain", "shortness of breath"
        ]
        self.load_model()

    def load_model(self):
        try:
            model_path = Path(settings.PRIORITY_MODEL_PATH)
            model_path.parent.mkdir(parents=True, exist_ok=True)

            if not model_path.exists():
                print(f"⚠️  Priority model not found at {model_path}. Using rule-based classification.")
                self.model = None
                self.label_encoder = None
                return

            loaded = joblib.load(model_path)

            if isinstance(loaded, tuple) and len(loaded) == 2:
                self.model, self.label_encoder = loaded
            else:
                self.model = loaded
                self.label_encoder = None

            print(f"✅ Priority classification model loaded from {model_path}")

        except Exception as e:
            print(f"❌ Error loading priority model: {e}")
            self.model = None
            self.label_encoder = None

    def preprocess_features(self, request: PriorityClassificationRequest):
        text_combined = f"{request.chief_complaint} {request.symptoms or ''}".lower()

        has_emergency_keyword = any(k in text_combined for k in self.emergency_keywords)
        has_high_priority_keyword = any(k in text_combined for k in self.high_priority_keywords)

        vital_score = 0.0
        if request.vital_signs:
            temp = request.vital_signs.get("temperature", 37.0)
            if temp > 39.0 or temp < 35.0:
                vital_score += 0.3

            bp_systolic = request.vital_signs.get("bp_systolic", 120)
            bp_diastolic = request.vital_signs.get("bp_diastolic", 80)
            if bp_systolic > 180 or bp_systolic < 90 or bp_diastolic > 110:
                vital_score += 0.4

            heart_rate = request.vital_signs.get("heart_rate", 75)
            if heart_rate > 120 or heart_rate < 50:
                vital_score += 0.2

            spo2 = request.vital_signs.get("spo2", 98)
            if spo2 < 90:
                vital_score += 0.5

        age_risk = 0.0
        if request.age >= 65:
            age_risk = 0.2
        elif request.age <= 5:
            age_risk = 0.15

        appointment_type_map = {
            "emergency": 1.0,
            "consultation": 0.4,
            "follow_up": 0.3,
            "laboratory": 0.2,
            "vaccination": 0.1,
            "checkup": 0.2
        }
        appointment_urgency = appointment_type_map.get((request.appointment_type or "").lower(), 0.3)

        history_risk = 0.0
        if request.medical_history:
            high_risk_conditions = [
                "diabetes", "hypertension", "heart disease", "cancer",
                "chronic", "kidney", "liver", "asthma", "copd"
            ]
            history_text = request.medical_history.lower()
            history_risk = sum(0.1 for c in high_risk_conditions if c in history_text)
            history_risk = min(history_risk, 0.5)

        features = {
            "has_emergency_keyword": int(has_emergency_keyword),
            "has_high_priority_keyword": int(has_high_priority_keyword),
            "vital_score": float(vital_score),
            "age_risk": float(age_risk),
            "appointment_urgency": float(appointment_urgency),
            "history_risk": float(history_risk),
            "age": float(request.age) / 100.0,
            "text_length": float(len(text_combined)) / 1000.0
        }

        return pd.DataFrame([features]), text_combined

    def classify(self, request: PriorityClassificationRequest) -> PriorityClassificationResponse:
        features_df, _ = self.preprocess_features(request)

        # Default: fallback
        priority_level, priority_score = self._fallback_classification(features_df)

        # Try model only if enabled
        if self.model is not None and self.model_enabled:
            try:
                probabilities = self.model.predict_proba(features_df)[0]
                class_idx = int(np.argmax(probabilities))
                priority_score = float(np.max(probabilities))

                if self.label_encoder is not None:
                    priority_level = str(self.label_encoder.inverse_transform([class_idx])[0])
                else:
                    priority_classes = ["low", "medium", "high", "emergency"]
                    priority_level = priority_classes[class_idx] if class_idx < len(priority_classes) else "medium"

            except Exception as e:
                # ✅ auto-disable incompatible model to stop repeated errors
                print(f"❌ Classification error (disabling model, using fallback): {e}")
                self.model_enabled = False
                priority_level, priority_score = self._fallback_classification(features_df)

        recommended_action = self._get_recommended_action(priority_level)
        reasoning = self._generate_reasoning(features_df, priority_level)

        return PriorityClassificationResponse(
            appointment_id=request.appointment_id,
            priority_level=priority_level,
            priority_score=round(priority_score, 3),
            recommended_action=recommended_action,
            reasoning=reasoning
        )

    def _fallback_classification(self, features_df: pd.DataFrame):
        if int(features_df["has_emergency_keyword"].values[0]) == 1:
            return "emergency", 0.95

        total_score = 0.0
        total_score += float(features_df["vital_score"].values[0]) * 2.0
        total_score += float(features_df["age_risk"].values[0]) * 1.5
        total_score += float(features_df["appointment_urgency"].values[0]) * 1.2
        total_score += float(features_df["history_risk"].values[0]) * 1.0

        if int(features_df["has_high_priority_keyword"].values[0]) == 1:
            total_score += 0.5

        total_score = min(total_score, 3.0) / 3.0

        if total_score >= 0.75:
            return "high", total_score
        elif total_score >= 0.45:
            return "medium", total_score
        else:
            return "low", total_score

    def _get_recommended_action(self, priority_level: str) -> str:
        actions = {
            "emergency": "Immediate attention required. Direct to emergency department.",
            "high": "Prioritize in queue. See within 30 minutes.",
            "medium": "Standard queue processing. See within 1-2 hours.",
            "low": "Regular appointment scheduling. Can wait up to 3-4 hours."
        }
        return actions.get(priority_level, "Standard processing")

    def _generate_reasoning(self, features_df: pd.DataFrame, priority_level: str) -> List[str]:
        reasoning = []

        if int(features_df["has_emergency_keyword"].values[0]) == 1:
            reasoning.append("Emergency keywords detected in symptoms")
        if float(features_df["vital_score"].values[0]) > 0.3:
            reasoning.append("Abnormal vital signs requiring attention")
        if float(features_df["age_risk"].values[0]) > 0.0:
            reasoning.append("Age-related risk factor present")
        if float(features_df["history_risk"].values[0]) > 0.2:
            reasoning.append("Pre-existing medical conditions increase priority")
        if int(features_df["has_high_priority_keyword"].values[0]) == 1:
            reasoning.append("High-priority symptoms identified")

        if not reasoning:
            reasoning.append(f"Standard {priority_level} priority based on overall assessment")

        return reasoning


priority_classifier = PriorityClassifier()
