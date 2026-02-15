# Project Structure Overview

```
smart-healthcare-system/
│
├── README.md                          # Project overview and documentation
├── QUICKSTART.md                      # Quick start guide for setup
├── docker-compose.yml                 # Docker orchestration configuration
│
├── backend/                           # FastAPI Backend Application
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI application entry point
│   │   │
│   │   ├── api/                      # API Routes
│   │   │   └── v1/
│   │   │       └── endpoints/
│   │   │           ├── auth.py       # Authentication endpoints
│   │   │           ├── appointments.py # Appointment management
│   │   │           └── ai.py         # AI/ML prediction endpoints
│   │   │
│   │   ├── core/                     # Core configurations
│   │   │   ├── config.py            # Application settings
│   │   │   └── security.py          # Authentication & security
│   │   │
│   │   ├── models/                   # SQLAlchemy database models
│   │   │   ├── __init__.py
│   │   │   ├── user.py              # User model
│   │   │   ├── appointment.py       # Appointment model
│   │   │   ├── queue.py             # Queue management model
│   │   │   └── notification.py      # Notification model
│   │   │
│   │   ├── schemas/                  # Pydantic schemas (validation)
│   │   │   ├── user.py              # User schemas
│   │   │   ├── appointment.py       # Appointment schemas
│   │   │   └── ai.py                # AI prediction schemas
│   │   │
│   │   ├── services/                 # Business logic services
│   │   │   └── ai/                  # AI/ML services
│   │   │       ├── noshow_predictor.py     # No-show prediction
│   │   │       ├── waittime_estimator.py   # Wait time estimation
│   │   │       └── priority_classifier.py  # Priority classification
│   │   │
│   │   ├── db/                       # Database utilities
│   │   │   └── session.py           # Database session management
│   │   │
│   │   └── utils/                    # Utility functions
│   │       └── notifications.py     # SMS/Email notifications
│   │
│   ├── tests/                        # Unit and integration tests
│   ├── requirements.txt              # Python dependencies
│   ├── .env.example                  # Environment variables template
│   └── Dockerfile                    # Backend Docker configuration
│
├── ml_models/                         # Machine Learning Models
│   ├── trained_models/               # Serialized trained models
│   │   ├── noshow_model.pkl         # XGBoost no-show predictor
│   │   ├── priority_model.pkl       # Random Forest priority classifier
│   │   └── waittime_model.h5        # LSTM wait time estimator
│   │
│   ├── notebooks/                    # Jupyter notebooks for experiments
│   │   ├── 01_exploratory_analysis.ipynb
│   │   ├── 02_noshow_model_training.ipynb
│   │   └── 03_model_evaluation.ipynb
│   │
│   ├── data/                         # Training datasets
│   │   └── KaggleV2-May-2016.csv    # Medical appointments dataset
│   │
│   └── DATASET_GUIDE.md             # Dataset documentation
│
├── scripts/                          # Utility scripts
│   ├── init_database.py             # Database initialization & seeding
│   ├── train_models.py              # ML model training script
│   ├── test_api.py                  # API testing script
│   └── export_training_data.py      # Export data for retraining
│
├── frontend/                         # React Frontend (to be implemented)
│   ├── src/
│   │   ├── components/              # React components
│   │   ├── pages/                   # Page components
│   │   ├── services/                # API service calls
│   │   └── App.js                   # Main app component
│   │
│   ├── public/
│   ├── package.json
│   └── Dockerfile
│
└── docs/                             # Documentation
    ├── API.md                        # API documentation
    ├── DEPLOYMENT.md                 # Deployment guide
    ├── ARCHITECTURE.md               # System architecture
    └── CONTRIBUTING.md               # Contribution guidelines
```

## 📂 Key Directories Explained

### `/backend/app/`
Main application code for the FastAPI backend:
- **api/**: RESTful API endpoints organized by version
- **models/**: Database table definitions using SQLAlchemy
- **schemas/**: Request/response validation using Pydantic
- **services/**: Business logic and AI model integration
- **core/**: Configuration, security, and shared utilities

### `/ml_models/`
Machine learning related files:
- **trained_models/**: Serialized model files (.pkl, .h5)
- **notebooks/**: Jupyter notebooks for experimentation
- **data/**: Training datasets (110K+ medical appointments)

### `/scripts/`
Automation and utility scripts:
- **init_database.py**: Creates tables and seeds sample data
- **train_models.py**: Trains all 3 AI models from scratch
- **test_api.py**: Automated API endpoint testing

### `/frontend/`
React.js frontend application (to be developed):
- Patient portal for booking appointments
- Doctor dashboard for managing schedules
- Admin panel for system configuration

## 🔑 Key Files

| File | Purpose |
|------|---------|
| `backend/app/main.py` | FastAPI application initialization |
| `backend/app/core/config.py` | Centralized configuration management |
| `backend/app/services/ai/noshow_predictor.py` | XGBoost no-show prediction |
| `scripts/train_models.py` | Complete ML training pipeline |
| `docker-compose.yml` | Multi-container orchestration |
| `README.md` | Project documentation |

## 🚀 Getting Started

1. **Backend Setup**: Follow `QUICKSTART.md`
2. **Train Models**: Run `scripts/train_models.py`
3. **Start Server**: `uvicorn app.main:app --reload`
4. **Test API**: Run `scripts/test_api.py`

## 📊 Data Flow

```
Frontend (React) 
    ↓
FastAPI Backend
    ↓
├── Database (PostgreSQL) - User data, appointments
├── Redis (Cache) - Session management, queue state
└── AI Models - Predictions and classifications
    ├── XGBoost → No-show probability
    ├── LSTM → Wait time estimation
    └── Random Forest → Priority classification
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Test specific module
pytest tests/test_appointments.py

# Test with coverage
pytest --cov=app tests/
```

## 📦 Dependencies

- **FastAPI**: Modern web framework
- **SQLAlchemy**: ORM for database operations
- **XGBoost**: Gradient boosting for no-show prediction
- **TensorFlow**: Deep learning for wait time estimation
- **Scikit-learn**: Priority classification
- **Twilio/SendGrid**: Notifications

## 🔐 Security Features

- JWT-based authentication
- Password hashing with bcrypt
- Role-based access control (Admin, Doctor, Patient)
- SQL injection prevention
- CORS configuration
- Rate limiting (planned)