# Smart Healthcare Appointment Management System (SHAMS)

## 🏥 Overview
SHAMS is an AI-powered healthcare appointment management system designed to optimize patient scheduling, reduce no-shows, and improve clinic efficiency through machine learning predictions.

## 🚀 Features

### Core Features
- **Patient Portal**: Registration, appointment booking, rescheduling, and cancellation
- **Healthcare Provider Dashboard**: Schedule management, patient records, real-time status updates
- **Admin Panel**: User management, clinic configuration, analytics reports
- **Real-time Notifications**: SMS and email reminders via Twilio and SendGrid
- **Queue Management**: Live queue status and estimated wait times

### AI/ML Features
1. **No-Show Prediction**: XGBoost model predicting appointment attendance (85%+ accuracy)
2. **Wait Time Estimation**: LSTM neural network for real-time wait time forecasting
3. **Priority Classification**: AI-based triage system (High/Medium/Low priority)
4. **Dynamic Slot Optimization**: Intelligent queue reordering based on predictions

## 📁 Project Structure

```
smart-healthcare-system/
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── api/v1/endpoints/  # API routes
│   │   ├── core/              # Configuration
│   │   ├── models/            # Database models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic
│   │   │   └── ai/           # AI/ML services
│   │   ├── db/               # Database utilities
│   │   └── utils/            # Helper functions
│   ├── tests/                # Unit tests
│   └── requirements.txt      # Python dependencies
├── ml_models/                 # Machine Learning
│   ├── trained_models/       # Serialized models
│   ├── notebooks/            # Jupyter notebooks
│   └── data/                 # Training datasets
├── frontend/                  # React frontend
├── docs/                      # Documentation
└── scripts/                   # Deployment scripts
```

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI 0.115.0
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Caching**: Redis
- **Task Queue**: Celery
- **Authentication**: JWT (python-jose)

### AI/ML Stack
- **Framework**: TensorFlow 2.18.0, Scikit-learn 1.6.1
- **Models**: XGBoost, LightGBM, LSTM
- **Data Processing**: Pandas, NumPy

### External Services
- **SMS**: Twilio API
- **Email**: SendGrid
- **Real-time**: Firebase Admin SDK

## 📊 Machine Learning Models

### 1. No-Show Prediction Model
- **Algorithm**: XGBoost Classifier
- **Features**: Demographics, appointment history, lead time, SMS reminders
- **Performance**: 85%+ accuracy, 0.88 AUC-ROC
- **Output**: Probability of patient showing up (0-1)

### 2. Wait Time Estimation Model
- **Algorithm**: LSTM Neural Network
- **Features**: Historical wait times, time of day, day of week, queue length
- **Performance**: RMSE < 10 minutes
- **Output**: Estimated wait time in minutes

### 3. Priority Classification Model
- **Algorithm**: Random Forest Classifier
- **Features**: Symptoms, vitals, medical history, age, urgency
- **Performance**: 90%+ accuracy
- **Output**: Priority level (High/Medium/Low)

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL 14+
- Redis 7+
- Node.js 18+ (for frontend)

### Backend Setup

1. **Clone and Navigate**
```bash
cd smart-healthcare-system/backend
```

2. **Create Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

4. **Environment Variables**
Create `.env` file:
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/shams_db

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Twilio
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_PHONE_NUMBER=your-twilio-phone

# SendGrid
SENDGRID_API_KEY=your-sendgrid-key
SENDGRID_FROM_EMAIL=noreply@shams.com

# Firebase
FIREBASE_CREDENTIALS_PATH=path/to/firebase-credentials.json
```

5. **Database Migration**
```bash
alembic upgrade head
```

6. **Train ML Models**
```bash
python scripts/train_models.py
```

7. **Run Server**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at: `http://localhost:8000`
API Documentation: `http://localhost:8000/docs`

### Dataset Setup

Download datasets from Kaggle:
```bash
# Medical Appointment No Shows Dataset
kaggle datasets download -d joniarroba/noshowappointments -p ml_models/data/

# Unzip
cd ml_models/data
unzip noshowappointments.zip
```

## 📚 API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login user
- `POST /api/v1/auth/refresh` - Refresh token

### Appointments
- `GET /api/v1/appointments/` - List appointments
- `POST /api/v1/appointments/` - Create appointment
- `GET /api/v1/appointments/{id}` - Get appointment details
- `PUT /api/v1/appointments/{id}` - Update appointment
- `DELETE /api/v1/appointments/{id}` - Cancel appointment

### AI Predictions
- `POST /api/v1/ai/predict-noshow` - Predict no-show probability
- `POST /api/v1/ai/estimate-wait-time` - Estimate wait time
- `POST /api/v1/ai/classify-priority` - Classify patient priority
- `POST /api/v1/ai/optimize-queue` - Optimize appointment queue

### Queue Management
- `GET /api/v1/queue/` - Get current queue status
- `GET /api/v1/queue/{patient_id}/position` - Get patient position
- `PUT /api/v1/queue/{appointment_id}/status` - Update appointment status

### Reports
- `GET /api/v1/reports/no-show-rate` - No-show statistics
- `GET /api/v1/reports/wait-times` - Wait time analytics
- `GET /api/v1/reports/attendance` - Attendance reports

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_appointments.py
```

## 🔒 Security Features
- JWT-based authentication
- Password hashing with bcrypt
- Role-based access control (Patient, Doctor, Admin)
- SQL injection prevention via ORM
- CORS configuration
- Rate limiting

## 📈 Performance Optimizations
- Redis caching for frequently accessed data
- Async database operations
- Connection pooling
- Batch processing for notifications
- Model prediction caching

## 🤝 Contributing
1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📝 License
This project is part of academic research at Maasai Mara University.

## 👨‍💻 Author
**Festus Kipyegon**
- Reg No: SB06/JR/MN/14056/2022
- Supervisor: Dr. Okemwa
- Department: Computing and Information Sciences

## 📧 Support
For issues and questions, please open an issue on GitHub or contact the development team.

## 🙏 Acknowledgments
- Maasai Mara University
- Dr. Okemwa (Project Supervisor)
- Kaggle community for datasets
- Open-source contributors