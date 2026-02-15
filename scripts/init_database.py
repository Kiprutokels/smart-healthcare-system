"""
Database initialization and seed data script
"""

import os
import sys

# Add backend/ to PYTHONPATH so "app" can be imported
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
sys.path.insert(0, BACKEND_DIR)

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random

from app.db.session import SessionLocal, init_db
from app.models.user import User, UserRole
from app.models.appointment import Appointment, AppointmentStatus, AppointmentType, PriorityLevel
from app.core.security import get_password_hash


def create_sample_users(db: Session):
    """
    Create sample users for testing
    """
    print("👥 Creating sample users...")
    
    # Admin user
    admin = User(
        email="admin@shams.com",
        phone="+254700000001",
        hashed_password=get_password_hash("admin123"),
        first_name="System",
        last_name="Administrator",
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True
    )
    db.add(admin)
    
    # Doctors
    doctors_data = [
        {"first_name": "James", "last_name": "Mwangi", "specialization": "General Medicine", "phone": "+254700000002"},
        {"first_name": "Sarah", "last_name": "Kamau", "specialization": "Pediatrics", "phone": "+254700000003"},
        {"first_name": "David", "last_name": "Ochieng", "specialization": "Cardiology", "phone": "+254700000004"},
        {"first_name": "Grace", "last_name": "Akinyi", "specialization": "Dermatology", "phone": "+254700000005"},
    ]
    
    doctors = []
    for idx, doctor_data in enumerate(doctors_data):
        doctor = User(
            email=f"{doctor_data['first_name'].lower()}.{doctor_data['last_name'].lower()}@shams.com",
            phone=doctor_data['phone'],
            hashed_password=get_password_hash("doctor123"),
            first_name=doctor_data['first_name'],
            last_name=doctor_data['last_name'],
            role=UserRole.DOCTOR,
            specialization=doctor_data['specialization'],
            department="Medical",
            license_number=f"DOC{10001 + idx}",
            is_active=True,
            is_verified=True
        )
        doctors.append(doctor)
        db.add(doctor)
    
    # Patients
    patients_data = [
        {"first_name": "John", "last_name": "Kimani", "phone": "+254700000010", "age": 35},
        {"first_name": "Mary", "last_name": "Wanjiru", "phone": "+254700000011", "age": 28},
        {"first_name": "Peter", "last_name": "Otieno", "phone": "+254700000012", "age": 45},
        {"first_name": "Jane", "last_name": "Njeri", "phone": "+254700000013", "age": 52},
        {"first_name": "Michael", "last_name": "Karanja", "phone": "+254700000014", "age": 67},
        {"first_name": "Lucy", "last_name": "Chebet", "phone": "+254700000015", "age": 23},
        {"first_name": "Daniel", "last_name": "Omondi", "phone": "+254700000016", "age": 31},
        {"first_name": "Rose", "last_name": "Wambui", "phone": "+254700000017", "age": 58},
    ]
    
    patients = []
    for patient_data in patients_data:
        birth_year = 2024 - patient_data['age']
        patient = User(
            email=f"{patient_data['first_name'].lower()}.{patient_data['last_name'].lower()}@example.com",
            phone=patient_data['phone'],
            hashed_password=get_password_hash("patient123"),
            first_name=patient_data['first_name'],
            last_name=patient_data['last_name'],
            role=UserRole.PATIENT,
            date_of_birth=datetime(birth_year, random.randint(1, 12), random.randint(1, 28)),
            gender=random.choice(["male", "female"]),
            address="Nairobi, Kenya",
            is_active=True,
            is_verified=True
        )
        patients.append(patient)
        db.add(patient)
    
    db.commit()
    print(f"✅ Created {len(doctors)} doctors and {len(patients)} patients")
    
    return doctors, patients


def create_sample_appointments(db: Session, doctors, patients):
    """
    Create sample appointments
    """
    print("📅 Creating sample appointments...")
    
    appointment_types = list(AppointmentType)
    priority_levels = list(PriorityLevel)
    
    appointments_created = 0
    
    # Create appointments for the next 7 days
    for day_offset in range(7):
        appointment_date = datetime.now() + timedelta(days=day_offset)
        
        # 3-5 appointments per day
        num_appointments = random.randint(3, 5)
        
        for _ in range(num_appointments):
            hour = random.randint(8, 16)
            minute = random.choice([0, 30])
            
            appointment = Appointment(
                patient_id=random.choice(patients).id,
                doctor_id=random.choice(doctors).id,
                appointment_date=appointment_date.replace(hour=hour, minute=minute, second=0),
                appointment_type=random.choice(appointment_types),
                status=random.choice([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]),
                priority=random.choice(priority_levels),
                duration_minutes=random.choice([30, 45, 60]),
                chief_complaint=random.choice([
                    "Routine checkup",
                    "Follow-up visit",
                    "Flu symptoms",
                    "Chest pain",
                    "Headache",
                    "Skin rash",
                    "Back pain"
                ])
            )
            db.add(appointment)
            appointments_created += 1
    
    db.commit()
    print(f"✅ Created {appointments_created} appointments")


def main():
    """
    Main initialization script
    """
    print("=" * 60)
    print("  Smart Healthcare System - Database Initialization")
    print("=" * 60)
    
    # Initialize database tables
    print("\n📊 Initializing database tables...")
    init_db()
    
    # Create session
    db = SessionLocal()
    
    try:
        # Check if data already exists
        existing_users = db.query(User).count()
        
        if existing_users > 0:
            print(f"\n⚠️  Database already contains {existing_users} users.")
            response = input("Do you want to reset and seed data? (yes/no): ")
            
            if response.lower() != "yes":
                print("❌ Initialization cancelled.")
                return
            
            # Clear existing data
            print("🗑️  Clearing existing data...")
            db.query(Appointment).delete()
            db.query(User).delete()
            db.commit()
        
        # Create sample data
        doctors, patients = create_sample_users(db)
        create_sample_appointments(db, doctors, patients)
        
        print("\n" + "=" * 60)
        print("  ✅ Database initialization complete!")
        print("=" * 60)
        print("\n📝 Sample Credentials:")
        print("\n   Admin:")
        print("   Email: admin@shams.com")
        print("   Password: admin123")
        print("\n   Doctor:")
        print("   Email: james.mwangi@shams.com")
        print("   Password: doctor123")
        print("\n   Patient:")
        print("   Email: john.kimani@example.com")
        print("   Password: patient123")
        
    except Exception as e:
        print(f"\n❌ Initialization error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()