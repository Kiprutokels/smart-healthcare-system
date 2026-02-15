"""
Machine Learning Model Training Script
Trains all AI models for the Smart Healthcare System

Run from project root: python scripts/train_models.py
"""
import sys
import json
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, roc_auc_score
import joblib

from app.core.config import settings

try:
    from tensorflow import keras
    from tensorflow.keras import layers
    TENSORFLOW_AVAILABLE = True
except ImportError:
    print("⚠️  TensorFlow not available. Install with: pip install tensorflow")
    TENSORFLOW_AVAILABLE = False


def load_dataset():
    print("\n📊 Loading dataset...")
    data_path = project_root / "ml_models" / "data" / "KaggleV2-May-2016.csv"

    if not data_path.exists():
        print(f"❌ Dataset not found at: {data_path}")
        data_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {data_path.parent}")
        return None

    df = pd.read_csv(data_path)
    print(f"✅ Dataset loaded from {data_path}")
    print(f"   Shape: {df.shape}")
    return df


# -----------------------------
# 1) No-show model
# -----------------------------
def train_noshow_model(df: pd.DataFrame):
    print("\n" + "=" * 70)
    print("1️⃣  Training No-Show Prediction Model (XGBoost)")
    print("=" * 70)

    df = df.copy()
    df["ScheduledDay"] = pd.to_datetime(df["ScheduledDay"])
    df["AppointmentDay"] = pd.to_datetime(df["AppointmentDay"])
    df["LeadTime"] = (df["AppointmentDay"] - df["ScheduledDay"]).dt.days
    df["DayOfWeek"] = df["AppointmentDay"].dt.dayofweek
    df["Month"] = df["AppointmentDay"].dt.month
    df["Hour"] = df["ScheduledDay"].dt.hour

    df["No-show"] = df["No-show"].map({"No": 0, "Yes": 1})
    df["Gender"] = df["Gender"].map({"F": 1, "M": 0})
    df["AppointmentHistory"] = df.groupby("PatientId").cumcount()

    features = [
        "Age", "Gender", "Scholarship", "Hipertension", "Diabetes",
        "Alcoholism", "Handcap", "SMS_received", "LeadTime",
        "DayOfWeek", "Month", "Hour"
    ]

    X = df[features].fillna(0)
    y = df["No-show"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        random_state=42,
        eval_metric="logloss",
        use_label_encoder=False,
    )
    model.fit(X_train, y_train, verbose=False)

    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    print("\n📈 No-Show Model Performance:")
    print(classification_report(y_test, y_pred, target_names=["Show", "No-Show"]))
    print(f"   AUC-ROC Score: {roc_auc_score(y_test, y_pred_proba):.4f}")

    model_dir = project_root / "ml_models" / "trained_models"
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "noshow_model.pkl"
    joblib.dump(model, model_path)
    print(f"✅ Saved: {model_path}")
    return model


# -----------------------------
# 2) Priority model
# -----------------------------
EMERGENCY_KEYWORDS = [
    "chest pain", "difficulty breathing", "severe bleeding", "unconscious",
    "stroke", "heart attack", "severe trauma", "poisoning", "seizure",
    "severe allergic reaction", "suicide attempt", "severe burn"
]
HIGH_PRIORITY_KEYWORDS = [
    "high fever", "severe pain", "vomiting", "dizziness", "confusion",
    "severe headache", "abdominal pain", "shortness of breath"
]

def _make_synthetic_text(row: pd.Series) -> str:
    parts = []
    age = int(row.get("Age", 35))

    if int(row.get("Hipertension", 0)) == 1:
        parts.append("hypertension")
    if int(row.get("Diabetes", 0)) == 1:
        parts.append("diabetes")
    if int(row.get("Alcoholism", 0)) == 1:
        parts.append("alcoholism")
    if float(row.get("Handcap", 0)) > 0:
        parts.append("disability")

    r = np.random.random()
    if age >= 75 and r < 0.25:
        parts.append("chest pain")
    elif age >= 65 and r < 0.25:
        parts.append("shortness of breath")
    elif r < 0.10:
        parts.append("severe headache")

    if not parts:
        parts.append("routine checkup")

    return " ".join(parts)

def _make_synthetic_vitals(row: pd.Series) -> dict:
    age = float(row.get("Age", 35))
    has_htn = int(row.get("Hipertension", 0)) == 1
    has_dm = int(row.get("Diabetes", 0)) == 1

    temp = 37.0 + np.random.normal(0, 0.3)
    hr = 75 + np.random.normal(0, 8)
    spo2 = 98 + np.random.normal(0, 1)
    bp_sys = 120 + np.random.normal(0, 10)
    bp_dia = 80 + np.random.normal(0, 6)

    if has_htn:
        bp_sys += 20
        bp_dia += 10
    if has_dm:
        hr += 8
    if age >= 75 and np.random.random() < 0.15:
        spo2 -= 10

    return {
        "temperature": float(np.clip(temp, 34.0, 41.0)),
        "bp_systolic": float(np.clip(bp_sys, 80.0, 220.0)),
        "bp_diastolic": float(np.clip(bp_dia, 50.0, 130.0)),
        "heart_rate": float(np.clip(hr, 40.0, 160.0)),
        "spo2": float(np.clip(spo2, 70.0, 100.0)),
    }

def _priority_label_from_row(row: pd.Series) -> str:
    age = int(row.get("Age", 0))
    htn = int(row.get("Hipertension", 0))
    dm = int(row.get("Diabetes", 0))
    handcap = float(row.get("Handcap", 0))

    if age >= 75 and (htn == 1 or dm == 1):
        return "emergency"
    if age >= 65 or (htn == 1 and dm == 1) or handcap > 1:
        return "high"
    if (50 <= age < 65) or (htn == 1) or (dm == 1) or handcap == 1:
        return "medium"
    return "low"

def _runtime_priority_features(chief_complaint: str, symptoms: str | None, vital_signs: dict | None,
                               age: int, medical_history: str | None, appointment_type: str) -> dict:
    text_combined = f"{chief_complaint} {symptoms or ''}".lower()

    has_emergency_keyword = any(k in text_combined for k in EMERGENCY_KEYWORDS)
    has_high_priority_keyword = any(k in text_combined for k in HIGH_PRIORITY_KEYWORDS)

    vital_score = 0.0
    if vital_signs:
        temp = vital_signs.get("temperature", 37.0)
        if temp > 39.0 or temp < 35.0:
            vital_score += 0.3

        bp_systolic = vital_signs.get("bp_systolic", 120)
        bp_diastolic = vital_signs.get("bp_diastolic", 80)
        if bp_systolic > 180 or bp_systolic < 90 or bp_diastolic > 110:
            vital_score += 0.4

        heart_rate = vital_signs.get("heart_rate", 75)
        if heart_rate > 120 or heart_rate < 50:
            vital_score += 0.2

        spo2 = vital_signs.get("spo2", 98)
        if spo2 < 90:
            vital_score += 0.5

    age_risk = 0.0
    if age >= 65:
        age_risk = 0.2
    elif age <= 5:
        age_risk = 0.15

    appointment_type_map = {
        "emergency": 1.0,
        "consultation": 0.4,
        "follow_up": 0.3,
        "laboratory": 0.2,
        "vaccination": 0.1,
        "checkup": 0.2
    }
    appointment_urgency = appointment_type_map.get((appointment_type or "").lower(), 0.3)

    history_risk = 0.0
    if medical_history:
        high_risk_conditions = [
            "diabetes", "hypertension", "heart disease", "cancer",
            "chronic", "kidney", "liver", "asthma", "copd"
        ]
        history_text = medical_history.lower()
        history_risk = sum(0.1 for c in high_risk_conditions if c in history_text)
        history_risk = min(history_risk, 0.5)

    return {
        "has_emergency_keyword": int(has_emergency_keyword),
        "has_high_priority_keyword": int(has_high_priority_keyword),
        "vital_score": float(vital_score),
        "age_risk": float(age_risk),
        "appointment_urgency": float(appointment_urgency),
        "history_risk": float(history_risk),
        "age": float(age) / 100.0,
        "text_length": float(len(text_combined)) / 1000.0,
    }

def train_priority_model_runtime_features(df: pd.DataFrame):
    print("\n" + "=" * 70)
    print("2️⃣  Training Priority Model (RF) - Runtime Feature Space ")
    print("=" * 70)

    df = df.copy()
    df["Age"] = df["Age"].fillna(35).astype(int)
    np.random.seed(42)

    rows = []
    labels = []

    for _, row in df.iterrows():
        age = int(row.get("Age", 35))
        chief = _make_synthetic_text(row)
        symptoms = ""
        vitals = _make_synthetic_vitals(row)

        mh_parts = []
        if int(row.get("Diabetes", 0)) == 1:
            mh_parts.append("diabetes")
        if int(row.get("Hipertension", 0)) == 1:
            mh_parts.append("hypertension")
        if int(row.get("Alcoholism", 0)) == 1:
            mh_parts.append("alcoholism")
        medical_history = ", ".join(mh_parts) if mh_parts else None

        r = np.random.random()
        if r < 0.10:
            appointment_type = "emergency"
        elif r < 0.70:
            appointment_type = "consultation"
        elif r < 0.85:
            appointment_type = "follow_up"
        else:
            appointment_type = "checkup"

        feats = _runtime_priority_features(
            chief_complaint=chief,
            symptoms=symptoms,
            vital_signs=vitals,
            age=age,
            medical_history=medical_history,
            appointment_type=appointment_type,
        )

        rows.append(feats)
        labels.append(_priority_label_from_row(row))

    X = pd.DataFrame(rows)
    y = pd.Series(labels).astype(str)

    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_enc, test_size=0.2, random_state=42, stratify=y_enc
    )

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=12,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print("\n📈 Priority Model Performance:")
    print(classification_report(y_test, y_pred, target_names=le.classes_))

    model_dir = project_root / "ml_models" / "trained_models"
    model_dir.mkdir(parents=True, exist_ok=True)
    out_path = model_dir / "priority_model.pkl"
    joblib.dump((model, le), out_path)

    print(f"✅ Saved: {out_path}")
    print(f"✅ Feature columns: {list(X.columns)}")
    return model


# -----------------------------
# 3) Wait time model
# -----------------------------
def train_waittime_model(df: pd.DataFrame):
    if not TENSORFLOW_AVAILABLE:
        print("\n" + "=" * 70)
        print("3️⃣  Skipping Wait Time Model (TensorFlow not available)")
        print("=" * 70)
        return None

    print("\n" + "=" * 70)
    print("3️⃣  Training Wait Time Estimation Model (LSTM) - Rich Inputs (6 features)")
    print("=" * 70)

    df = df.copy()
    np.random.seed(42)

    df["ScheduledDay"] = pd.to_datetime(df["ScheduledDay"])
    df["AppointmentDay"] = pd.to_datetime(df["AppointmentDay"])
    df["Hour"] = df["ScheduledDay"].dt.hour
    df["DayOfWeek"] = df["AppointmentDay"].dt.dayofweek

    # Synthetic doctor and queue (since Kaggle lacks them)
    df["DoctorId"] = (df["AppointmentID"].astype(int) % 50) + 1
    df["QueueLen"] = np.random.randint(0, 25, size=len(df))

    def tod(h):
        if h < 12:
            return "morning"
        if h < 17:
            return "afternoon"
        return "evening"

    df["TimeOfDay"] = df["Hour"].apply(tod)

    # Synthetic appointment type distribution
    appt_types = ["consultation", "follow_up", "laboratory", "emergency", "vaccination", "checkup"]
    probs = np.array([0.55, 0.15, 0.10, 0.05, 0.05, 0.10])
    df["AppointmentType"] = np.random.choice(appt_types, size=len(df), p=probs)

    time_of_day_map = {"morning": 0, "afternoon": 1, "evening": 2}
    appointment_type_map = {t: i for i, t in enumerate(appt_types)}

    # Generate synthetic wait time (target) influenced by queue, type, hour, dow
    type_multiplier = df["AppointmentType"].map({
        "consultation": 1.5,
        "follow_up": 0.8,
        "laboratory": 0.6,
        "emergency": 0.3,
        "vaccination": 0.4,
        "checkup": 1.0,
    }).fillna(1.0)

    base_wait = 10
    df["WaitTime"] = (
        base_wait
        + df["QueueLen"] * 7 * type_multiplier
        + (df["Hour"] - 12).abs() * 1.5
        + df["DayOfWeek"] * 2.0
        + np.random.normal(0, 6, len(df))
    ).clip(1, 180)

    # Build features (6) in same order runtime uses
    hour = df["Hour"].astype(np.float32).values
    dow = df["DayOfWeek"].astype(np.float32).values
    tod_enc = df["TimeOfDay"].map(time_of_day_map).astype(np.float32).values
    appt_enc = df["AppointmentType"].map(appointment_type_map).astype(np.float32).values
    queue = df["QueueLen"].astype(np.float32).values
    doctor = df["DoctorId"].astype(np.float32).values

    # scalers to keep stable
    scalers = {
        "hour_div": 24.0,
        "dow_div": 7.0,
        "tod_div": 2.0,
        "appt_type_div": 5.0,
        "queue_div": 50.0,
        "doctor_div": 100.0,
        "y_div": 180.0,
    }

    X = np.stack([
        hour / scalers["hour_div"],
        dow / scalers["dow_div"],
        tod_enc / scalers["tod_div"],
        appt_enc / scalers["appt_type_div"],
        queue / scalers["queue_div"],
        doctor / scalers["doctor_div"],
    ], axis=1).astype(np.float32)

    y = (df["WaitTime"].astype(np.float32).values / scalers["y_div"]).astype(np.float32)

    # reshape to (N, 1, 6)
    X = X.reshape(X.shape[0], 1, X.shape[1])

    split_idx = int(0.8 * len(X))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    model = keras.Sequential([
        layers.LSTM(64, input_shape=(1, 6), return_sequences=True),
        layers.Dropout(0.2),
        layers.LSTM(32),
        layers.Dropout(0.2),
        layers.Dense(16, activation="relu"),
        layers.Dense(1),
    ])
    model.compile(optimizer="adam", loss="mse", metrics=["mae"])

    model.fit(
        X_train, y_train,
        epochs=10,
        batch_size=64,
        validation_split=0.2,
        verbose=1
    )

    loss, mae = model.evaluate(X_test, y_test, verbose=0)
    print(f"\n📈 Wait Time Model - Test MAE: {mae * scalers['y_div']:.2f} minutes")

    model_dir = project_root / "ml_models" / "trained_models"
    model_dir.mkdir(parents=True, exist_ok=True)

    out_path = model_dir / "waittime_model.keras"
    model.save(out_path)
    print(f"✅ Saved model: {out_path}")

    # Save meta used by runtime
    meta = {
        "time_of_day_map": time_of_day_map,
        "appointment_type_map": appointment_type_map,
        "scalers": scalers,
        "feature_order": [
            "hour", "day_of_week", "time_of_day_encoded", "appointment_type_encoded", "queue_length", "doctor_id"
        ],
        "target": "wait_time_minutes",
    }

    meta_path = model_dir / "waittime_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"✅ Saved meta: {meta_path}")
    return model


def main():
    print("=" * 70)
    print("  🏥 Smart Healthcare System - ML Model Training Pipeline")
    print("=" * 70)

    df = load_dataset()
    if df is None:
        print("\n❌ Cannot proceed without dataset. Exiting.")
        return

    train_noshow_model(df.copy())
    train_priority_model_runtime_features(df.copy())
    train_waittime_model(df.copy())

    print("\n✅ Training complete.")
    print(f"📁 Models at: {project_root / 'ml_models' / 'trained_models'}")


if __name__ == "__main__":
    main()