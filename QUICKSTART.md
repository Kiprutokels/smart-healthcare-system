# 🚀 Quick Start Guide - Smart Healthcare Appointment Management System

## Prerequisites

- Python 3.10 or higher
- PostgreSQL 14+
- Redis 7+ (optional but recommended)
- Git

## 📥 Installation Steps

### 1. Setup Project

```bash
# Navigate to project directory
cd smart-healthcare-system/backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Setup Database

#### Install PostgreSQL
```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS (using Homebrew)
brew install postgresql

# Start PostgreSQL service
sudo service postgresql start  # Linux
brew services start postgresql  # macOS
```

#### Create Database
```bash
# Access PostgreSQL
sudo -u postgres psql

# Create database and user
CREATE DATABASE shams_db;
CREATE USER shams_user WITH PASSWORD 'yourpassword';
GRANT ALL PRIVILEGES ON DATABASE shams_db TO shams_user;
\q
```

### 3. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
nano .env  # or use any text editor
```

**Important Settings to Update:**
```env
DATABASE_URL=postgresql://shams_user:yourpassword@localhost:5432/shams_db
SECRET_KEY=<generate-using-openssl-rand-hex-32>
TWILIO_ACCOUNT_SID=<your-twilio-sid>
TWILIO_AUTH_TOKEN=<your-twilio-token>
```

### 4. Initialize Database

```bash
# Run database initialization script
cd ..
python scripts/init_database.py
```

This will create tables and seed sample data:
- 1 Admin user
- 4 Doctors
- 8 Patients
- ~30 Appointments

### 5. Download Dataset and Train Models

```bash
# Create data directory
mkdir -p ml_models/data

# Download dataset (see DATASET_GUIDE.md for details)
cd ml_models/data
kaggle datasets download -d joniarroba/noshowappointments
unzip noshowappointments.zip

# Train models
cd ../..
python scripts/train_models.py
```

Expected output:
```
✅ No-show model saved
✅ Priority model saved  
✅ Wait time model saved
```

### 6. Start Backend Server

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Server will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 7. Test API

Open a new terminal and run:
```bash
python scripts/test_api.py
```

## 🔑 Default Credentials

### Admin
- Email: `admin@shams.com`
- Password: `admin123`

### Doctor
- Email: `james.mwangi@shams.com`
- Password: `doctor123`

### Patient
- Email: `john.kimani@example.com`
- Password: `patient123`

## 🎯 Quick API Test

### 1. Get Access Token
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login-json" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john.kimani@example.com",
    "password": "patient123"
  }'
```

### 2. Create Appointment
```bash
curl -X POST "http://localhost:8000/api/v1/appointments/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "doctor_id": 2,
    "appointment_date": "2026-02-20T10:00:00",
    "appointment_type": "consultation",
    "duration_minutes": 30,
    "chief_complaint": "Routine checkup"
  }'
```

### 3. Predict No-Show
```bash
curl -X POST "http://localhost:8000/api/v1/ai/predict-noshow" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": 6,
    "appointment_date": "2026-02-20T10:00:00",
    "appointment_type": "consultation",
    "previous_no_shows": 0,
    "previous_appointments": 5,
    "sms_reminder": true
  }'
```

## 🐳 Docker Deployment (Alternative)

### Using Docker Compose
```bash
# Build and start all services
docker-compose up -d

# Check logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

Services:
- Backend: http://localhost:8000
- PostgreSQL: localhost:5432
- Redis: localhost:6379

## 📊 Accessing API Documentation

Once the server is running:

1. **Swagger UI**: http://localhost:8000/docs
   - Interactive API documentation
   - Test endpoints directly in browser

2. **ReDoc**: http://localhost:8000/redoc
   - Clean, readable API reference

## 🔧 Troubleshooting

### Issue: Database Connection Error
```
sqlalchemy.exc.OperationalError: could not connect to server
```
**Solution**:
- Ensure PostgreSQL is running: `sudo service postgresql status`
- Check DATABASE_URL in .env file
- Verify database credentials

### Issue: Module Not Found
```
ModuleNotFoundError: No module named 'fastapi'
```
**Solution**:
- Activate virtual environment
- Reinstall requirements: `pip install -r requirements.txt`

### Issue: Port Already in Use
```
ERROR: [Errno 98] Address already in use
```
**Solution**:
- Change port: `uvicorn app.main:app --port 8001`
- Or kill existing process: `kill $(lsof -t -i:8000)`

### Issue: AI Models Not Found
```
⚠️ No-show model not found
```
**Solution**:
- Run training script: `python scripts/train_models.py`
- Ensure models are in `ml_models/trained_models/`

## 📱 Next Steps

1. ✅ **Setup Frontend** (React)
   - Follow frontend/README.md

2. ✅ **Configure Notifications**
   - Setup Twilio for SMS
   - Setup SendGrid for Email
   - Configure Firebase for push notifications

3. ✅ **Deploy to Production**
   - Use cloud providers (AWS, GCP, Azure)
   - Setup SSL certificates
   - Configure domain names

4. ✅ **Monitor Performance**
   - Setup logging and monitoring
   - Track API performance
   - Monitor AI model accuracy

## 📚 Additional Resources

- [Full Documentation](./docs/)
- [Dataset Guide](./ml_models/DATASET_GUIDE.md)
- [API Testing Guide](./scripts/test_api.py)
- [Deployment Guide](./docs/DEPLOYMENT.md)

## 🆘 Getting Help

If you encounter issues:
1. Check troubleshooting section above
2. Review logs: `docker-compose logs` or terminal output
3. Consult documentation in `/docs`
4. Check model health: `curl http://localhost:8000/api/v1/ai/health`

## 🎉 Success!

Your Smart Healthcare Appointment Management System is now ready! 

Access the API at: **http://localhost:8000/docs**