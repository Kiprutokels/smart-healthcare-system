"""
API Testing Script
Tests all endpoints of the Smart Healthcare System
"""
import requests
import json
from datetime import datetime, timedelta

# Base URL
BASE_URL = "http://localhost:8000/api/v1"


def safe_response_payload(resp: requests.Response):
    """
    Always return something printable, even if backend returns HTML/plaintext on errors.
    """
    try:
        return resp.json()
    except Exception:
        text = (resp.text or "").strip()
        return {
            "non_json_response": text[:2000],  # prevent huge dumps
            "content_type": resp.headers.get("content-type"),
        }


def print_error_details(resp: requests.Response, label: str = "Request failed"):
    """
    Print rich diagnostics without crashing.
    """
    print(f"❌ {label}")
    print(f"   Status: {resp.status_code}")
    print(f"   URL: {resp.request.method} {resp.url}")
    # headers can be large; print minimal useful parts
    print(f"   Content-Type: {resp.headers.get('content-type')}")
    payload = safe_response_payload(resp)
    print("   Body:")
    print(json.dumps(payload, indent=2) if isinstance(payload, dict) else str(payload))


class TestClient:
    def __init__(self):
        self.base_url = BASE_URL
        self.access_token = None

    def test_health(self):
        """Test health endpoint"""
        print("\n🔍 Testing Health Endpoint...")
        response = requests.get(f"{self.base_url.replace('/api/v1', '')}/health")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            print(f"Response: {json.dumps(safe_response_payload(response), indent=2)}")
            return True
        else:
            print_error_details(response, "Health endpoint failed")
            return False

    def test_register(self, user_data):
        """Test user registration"""
        print("\n🔍 Testing User Registration...")
        response = requests.post(f"{self.base_url}/auth/register", json=user_data)
        print(f"Status: {response.status_code}")

        if response.status_code == 201:
            data = safe_response_payload(response)
            email = data.get("email") if isinstance(data, dict) else None
            print(f"✅ User registered: {email or '(email missing in response)'}")
            return True

        print_error_details(response, "Registration failed")
        return False

    def test_login(self, email, password):
        """Test user login"""
        print(f"\n🔍 Testing Login for {email}...")
        response = requests.post(
            f"{self.base_url}/auth/login-json",
            json={"email": email, "password": password},
        )
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = safe_response_payload(response)
            if not isinstance(data, dict) or "access_token" not in data:
                print("❌ Login response missing access_token")
                print(json.dumps(data, indent=2) if isinstance(data, dict) else data)
                return False

            self.access_token = data["access_token"]
            print("✅ Login successful")
            print(f"   Access Token: {self.access_token[:50]}...")
            return True

        print_error_details(response, "Login failed")
        return False

    def get_headers(self):
        """Get authorization headers"""
        return {"Authorization": f"Bearer {self.access_token}"}

    def test_get_profile(self):
        """Test get current user profile"""
        print("\n🔍 Testing Get Profile...")
        response = requests.get(f"{self.base_url}/auth/me", headers=self.get_headers())
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            user = safe_response_payload(response)
            if isinstance(user, dict):
                print(f"✅ Profile retrieved: {user.get('first_name', '')} {user.get('last_name', '')}".strip())
            else:
                print("✅ Profile retrieved (non-dict response)")
            return user

        print_error_details(response, "Get profile failed")
        return None

    def test_create_appointment(self, appointment_data):
        """Test create appointment"""
        print("\n🔍 Testing Create Appointment...")
        response = requests.post(
            f"{self.base_url}/appointments/",
            json=appointment_data,
            headers=self.get_headers(),
        )
        print(f"Status: {response.status_code}")

        if response.status_code == 201:
            apt = safe_response_payload(response)
            if isinstance(apt, dict):
                print(f"✅ Appointment created: ID {apt.get('id')}")
                print(f"   Date: {apt.get('appointment_date')}")
                print(f"   Type: {apt.get('appointment_type')}")
            else:
                print("✅ Appointment created (unexpected response format)")
            return apt

        print_error_details(response, "Create appointment failed")
        return None

    def test_list_appointments(self):
        """Test list appointments"""
        print("\n🔍 Testing List Appointments...")
        response = requests.get(f"{self.base_url}/appointments/", headers=self.get_headers())
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            appointments = safe_response_payload(response)
            if isinstance(appointments, list):
                print(f"✅ Retrieved {len(appointments)} appointments")
            else:
                print("✅ Retrieved appointments (unexpected response format)")
            return appointments if isinstance(appointments, list) else []

        print_error_details(response, "List appointments failed")
        return []

    def test_noshow_prediction(self, appointment_id):
        """Test no-show prediction"""
        print(f"\n🔍 Testing No-Show Prediction for Appointment {appointment_id}...")

        # Get appointment details first
        apt_response = requests.get(
            f"{self.base_url}/appointments/{appointment_id}",
            headers=self.get_headers(),
        )
        if apt_response.status_code != 200:
            print_error_details(apt_response, "Could not fetch appointment for prediction")
            return None

        apt = safe_response_payload(apt_response)
        if not isinstance(apt, dict):
            print("❌ Appointment fetch returned unexpected format")
            print(apt)
            return None

        prediction_data = {
            "appointment_id": appointment_id,
            "patient_id": apt.get("patient_id"),
            "appointment_date": apt.get("appointment_date"),
            "appointment_type": apt.get("appointment_type"),
            "previous_no_shows": 0,
            "previous_appointments": 5,
            "sms_reminder": True,
        }

        response = requests.post(
            f"{self.base_url}/ai/predict-noshow",
            json=prediction_data,
            headers=self.get_headers(),
        )
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            prediction = safe_response_payload(response)
            if isinstance(prediction, dict):
                print("✅ No-Show Prediction:")
                try:
                    print(f"   Probability: {float(prediction['no_show_probability']):.2%}")
                except Exception:
                    print(f"   Probability: {prediction.get('no_show_probability')}")
                print(f"   Risk Level: {prediction.get('risk_level')}")
                try:
                    print(f"   Confidence: {float(prediction['confidence']):.2%}")
                except Exception:
                    print(f"   Confidence: {prediction.get('confidence')}")
            else:
                print("✅ No-Show Prediction (unexpected response format)")
            return prediction

        print_error_details(response, "No-show prediction failed")
        return None

    def test_waittime_estimation(self, doctor_id):
        """Test wait time estimation"""
        print(f"\n🔍 Testing Wait Time Estimation for Doctor {doctor_id}...")

        estimation_data = {
            "doctor_id": doctor_id,
            "appointment_date": (datetime.now() + timedelta(days=1)).isoformat(),
            "appointment_type": "consultation",
            "current_queue_length": 3,
            "time_of_day": "morning",
            "day_of_week": "Monday",
        }

        response = requests.post(
            f"{self.base_url}/ai/estimate-wait-time",
            json=estimation_data,
            headers=self.get_headers(),
        )
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            estimation = safe_response_payload(response)
            if isinstance(estimation, dict):
                print("✅ Wait Time Estimation:")
                print(f"   Estimated: {estimation.get('estimated_wait_time')} minutes")
                ci = estimation.get("confidence_interval") or {}
                print(f"   Range: {ci.get('min')}-{ci.get('max')} min")
                print(f"   Queue Position: {estimation.get('queue_position', 'N/A')}")
            else:
                print("✅ Wait time estimation (unexpected response format)")
            return estimation

        print_error_details(response, "Wait time estimation failed")
        return None

    def test_priority_classification(self, patient_id):
        """Test priority classification"""
        print(f"\n🔍 Testing Priority Classification for Patient {patient_id}...")

        classification_data = {
            "patient_id": patient_id,
            "chief_complaint": "Severe chest pain and difficulty breathing",
            "symptoms": "Chest pain, shortness of breath, dizziness",
            "vital_signs": {
                "temperature": 37.5,
                "bp_systolic": 150,
                "bp_diastolic": 95,
                "heart_rate": 110,
                "spo2": 92,
            },
            "age": 58,
            "appointment_type": "emergency",
        }

        response = requests.post(
            f"{self.base_url}/ai/classify-priority",
            json=classification_data,
            headers=self.get_headers(),
        )
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            classification = safe_response_payload(response)
            if isinstance(classification, dict):
                print("✅ Priority Classification:")
                level = classification.get("priority_level")
                print(f"   Priority Level: {(level or 'N/A').upper() if isinstance(level, str) else level}")
                try:
                    print(f"   Priority Score: {float(classification.get('priority_score')):.2%}")
                except Exception:
                    print(f"   Priority Score: {classification.get('priority_score')}")
                print(f"   Recommended Action: {classification.get('recommended_action')}")
                reasoning = classification.get("reasoning") or []
                if isinstance(reasoning, list):
                    print(f"   Reasoning: {', '.join(reasoning)}")
                else:
                    print(f"   Reasoning: {reasoning}")
            else:
                print("✅ Priority classification (unexpected response format)")
            return classification

        print_error_details(response, "Priority classification failed")
        return None

    def test_ai_health(self):
        """Test AI service health"""
        print("\n🔍 Testing AI Service Health...")
        response = requests.get(f"{self.base_url}/ai/health", headers=self.get_headers())
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            health = safe_response_payload(response)
            if isinstance(health, dict):
                print("✅ AI Services Status:")
                print(f"   No-Show Predictor: {'✓' if health.get('no_show_predictor') else '✗'}")
                print(f"   Wait Time Estimator: {'✓' if health.get('wait_time_estimator') else '✗'}")
                print(f"   Priority Classifier: {'✓' if health.get('priority_classifier') else '✗'}")
            else:
                print("✅ AI health returned unexpected format")
            return health

        print_error_details(response, "AI health failed")
        return None


def main():
    """
    Main testing function
    """
    print("=" * 70)
    print("  Smart Healthcare System - API Testing Suite")
    print("=" * 70)

    client = TestClient()

    # Test health
    if not client.test_health():
        print("\n❌ Backend is not running! Start the server first:")
        print("   cd backend && uvicorn app.main:app --reload")
        return

    # Test login with seeded user
    print("\n--- Testing Authentication ---")
    if not client.test_login("john.kimani@example.com", "patient123"):
        print("\n⚠️  Login failed. Run database initialization first:")
        print("   python scripts/init_database.py")
        return

    # Get profile
    user = client.test_get_profile()
    if not user:
        return

    # Test appointments
    print("\n--- Testing Appointments ---")

    appointment_data = {
        "doctor_id": 2,  # Dr. James Mwangi from seed data
        "appointment_date": (datetime.now() + timedelta(days=3, hours=10)).isoformat(),
        "appointment_type": "consultation",
        "duration_minutes": 30,
        "chief_complaint": "Regular checkup",
        "symptoms": "Feeling tired recently",
    }

    appointment = client.test_create_appointment(appointment_data)

    # List appointments
    appointments = client.test_list_appointments()

    # Test AI Services
    print("\n--- Testing AI Services ---")
    client.test_ai_health()

    if isinstance(appointment, dict) and appointment.get("id"):
        client.test_noshow_prediction(appointment["id"])
        client.test_waittime_estimation(appointment.get("doctor_id"))
        client.test_priority_classification(appointment.get("patient_id"))

    print("\n" + "=" * 70)
    print("  ✅ API Testing Complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
