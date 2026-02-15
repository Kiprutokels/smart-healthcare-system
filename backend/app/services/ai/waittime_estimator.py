"""
Wait Time Estimation AI Service
Using LSTM Neural Network for time-series prediction
"""
from __future__ import annotations

import numpy as np
from typing import Dict, Optional
from pathlib import Path

try:
    from tensorflow import keras
    TENSORFLOW_AVAILABLE = True
except ImportError:
    keras = None
    TENSORFLOW_AVAILABLE = False
    print("⚠️  TensorFlow not installed. Wait time model will use heuristic mode.")

from app.core.config import settings
from app.schemas.ai import WaitTimePredictionRequest, WaitTimePredictionResponse


class WaitTimeEstimator:
    """
    AI Service for estimating patient wait times using LSTM

    Fixes:
    - Automatically matches feature dimension to model's expected input_dim
    - Falls back to heuristic if model is incompatible
    """

    def __init__(self):
        self.model = None
        self.sequence_length = 10

        # model compatibility controls
        self.model_enabled: bool = True
        self.model_expected_features: Optional[int] = None  # e.g. 4 vs 6

        self.load_model()

    def load_model(self):
        """Load the trained wait time estimation model"""
        try:
            if not TENSORFLOW_AVAILABLE:
                print("⚠️  TensorFlow not available. Using heuristic wait time estimation.")
                self.model = None
                self.model_enabled = False
                return

            model_path = Path(settings.WAIT_TIME_MODEL_PATH)

            if model_path.exists():
                self.model = keras.models.load_model(str(model_path), compile=False)

                # Try compile (not strictly necessary for inference)
                try:
                    self.model.compile(optimizer="adam", loss="mse")
                except Exception:
                    pass

                # Detect expected input feature dimension from model input shape
                self.model_expected_features = self._infer_expected_feature_dim(self.model)

                if self.model_expected_features is None:
                    print("⚠️  Could not infer model input feature dimension. Using heuristic mode.")
                    self.model_enabled = False
                    self.model = None
                else:
                    print(f"✅ Wait time estimation model loaded from {model_path}")
                    print(f"✅ Model expects {self.model_expected_features} features per timestep.")

            else:
                print(f"⚠️  Wait time model not found at {model_path}. Using heuristic estimation.")
                self.model = None
                self.model_enabled = False

        except Exception as e:
            print(f"❌ Error loading wait time model: {e}")
            print("⚠️  Falling back to heuristic estimation.")
            self.model = None
            self.model_enabled = False
            self.model_expected_features = None

    @staticmethod
    def _infer_expected_feature_dim(model) -> Optional[int]:
        """
        Try to infer expected feature dimension (last dim) from Keras model input.
        Typical LSTM input: (batch, timesteps, features)
        """
        try:
            # Keras models can have input_shape like (None, 10, 4)
            input_shape = getattr(model, "input_shape", None)

            # Some models have multiple inputs; handle list/tuple
            if isinstance(input_shape, list) and input_shape:
                input_shape = input_shape[0]

            if isinstance(input_shape, tuple) and len(input_shape) >= 3:
                feat_dim = input_shape[-1]
                if feat_dim is None:
                    return None
                return int(feat_dim)

            return None
        except Exception:
            return None

    def _base_feature_vector(self, request: WaitTimePredictionRequest) -> np.ndarray:
        """
        Produce the "logical" feature vector we want to use.
        Current design produces 6 features.
        """
        hour = request.appointment_date.hour
        day_of_week = request.appointment_date.weekday()

        time_of_day_map = {"morning": 0, "afternoon": 1, "evening": 2}
        time_of_day_encoded = time_of_day_map.get((request.time_of_day or "morning").lower(), 0)

        appointment_type_map = {
            "consultation": 0, "follow_up": 1, "laboratory": 2,
            "emergency": 3, "vaccination": 4, "checkup": 5
        }
        appointment_type_encoded = appointment_type_map.get((request.appointment_type or "consultation").lower(), 0)

        # 6 features
        return np.array(
            [
                hour / 24.0,
                day_of_week / 7.0,
                time_of_day_encoded / 2.0,
                appointment_type_encoded / 5.0,
                (request.current_queue_length or 0) / 50.0,
                (request.doctor_id or 0) / 100.0,
            ],
            dtype=np.float32,
        )

    @staticmethod
    def _match_feature_dim(vec: np.ndarray, expected_dim: int) -> np.ndarray:
        """
        Slice/pad the feature vector to match expected_dim.
        - If model expects fewer features, slice from the left (keep most general signals first).
        - If model expects more features, pad with zeros.
        """
        if vec.shape[0] == expected_dim:
            return vec

        if vec.shape[0] > expected_dim:
            # slice first expected_dim features
            return vec[:expected_dim]

        # pad with zeros
        pad_len = expected_dim - vec.shape[0]
        return np.concatenate([vec, np.zeros((pad_len,), dtype=np.float32)], axis=0)

    def preprocess_features(self, request: WaitTimePredictionRequest) -> np.ndarray:
        """
        Preprocess input features for LSTM prediction
        Output shape: (1, sequence_length, expected_features)
        """
        base_vec = self._base_feature_vector(request)

        # If model exists and we inferred its expected dim, match it.
        expected = self.model_expected_features or base_vec.shape[0]
        base_vec = self._match_feature_dim(base_vec, expected)

        # Create sequence: repeat same vector across timesteps
        sequence = np.tile(base_vec, (self.sequence_length, 1)).astype(np.float32)
        sequence = sequence.reshape(1, self.sequence_length, expected)
        return sequence

    def predict(self, request: WaitTimePredictionRequest) -> WaitTimePredictionResponse:
        """
        Predict wait time for an appointment
        """
        use_model = bool(self.model and TENSORFLOW_AVAILABLE and self.model_enabled and self.model_expected_features)

        if use_model:
            try:
                features = self.preprocess_features(request)
                prediction = self.model.predict(features, verbose=0)

                # Handle common output shapes:
                # (1,1), (1,), or nested
                pred_value = float(np.array(prediction).reshape(-1)[0])

                # Guard against nonsense outputs
                if np.isnan(pred_value) or np.isinf(pred_value):
                    raise ValueError("Model produced NaN/Inf prediction")

                estimated_wait_time = int(max(0, round(pred_value)))

                confidence_interval = {
                    "min": max(0, estimated_wait_time - 10),
                    "max": estimated_wait_time + 10,
                }

            except Exception as e:
                # ✅ Auto-disable model after a hard compatibility error to stop repeated logs
                print(f"❌ Wait time prediction error (disabling model, using heuristic): {e}")
                self.model_enabled = False

                estimated_wait_time = self._fallback_estimation(request)
                confidence_interval = {
                    "min": max(0, estimated_wait_time - 15),
                    "max": estimated_wait_time + 15,
                }
        else:
            estimated_wait_time = self._fallback_estimation(request)
            confidence_interval = {
                "min": max(0, estimated_wait_time - 15),
                "max": estimated_wait_time + 15,
            }

        queue_position = (request.current_queue_length or 0) + 1

        return WaitTimePredictionResponse(
            appointment_id=request.appointment_id,
            estimated_wait_time=int(estimated_wait_time),
            confidence_interval=confidence_interval,
            queue_position=int(queue_position),
        )

    def _fallback_estimation(self, request: WaitTimePredictionRequest) -> int:
        """
        Heuristic-based wait time estimation when model is not available
        """
        base_wait_per_patient = 20

        appointment_type_multipliers = {
            "consultation": 1.5,
            "follow_up": 0.8,
            "laboratory": 0.6,
            "emergency": 0.3,
            "vaccination": 0.4,
            "checkup": 1.0,
        }
        multiplier = appointment_type_multipliers.get((request.appointment_type or "consultation").lower(), 1.0)

        queue_len = request.current_queue_length or 0
        wait_time = base_wait_per_patient * queue_len * multiplier

        hour = request.appointment_date.hour
        if 9 <= hour <= 11:
            wait_time *= 1.2
        elif 14 <= hour <= 16:
            wait_time *= 1.15

        day_map = {
            "monday": 1.2, "tuesday": 1.1, "wednesday": 1.0,
            "thursday": 1.1, "friday": 1.15, "saturday": 0.9, "sunday": 0.8,
        }
        day_multiplier = day_map.get((request.day_of_week or "").lower(), 1.0)
        wait_time *= day_multiplier

        return int(max(0, round(wait_time)))


wait_time_estimator = WaitTimeEstimator()
