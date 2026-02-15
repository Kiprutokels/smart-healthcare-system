# Dataset Setup and Model Training Guide

## 📦 Dataset Information

### Primary Dataset: Medical Appointment No Shows
- **Source**: Kaggle
- **URL**: https://www.kaggle.com/datasets/joniarroba/noshowappointments
- **File**: KaggleV2-May-2016.csv
- **Size**: ~300MB
- **Records**: 110,527 appointments

### Dataset Description
This dataset contains information about medical appointments in Brazil, including:
- Patient demographics (Age, Gender)
- Medical conditions (Diabetes, Hypertension, Alcoholism, Disability)
- Appointment details (Scheduled date, Appointment date, SMS reminders)
- Outcome (No-show status)

## 🚀 Quick Start

### Step 1: Download Dataset

#### Method 1: Using Kaggle CLI (Recommended)
```bash
# Install Kaggle CLI
pip install kaggle

# Setup Kaggle credentials
# 1. Go to https://www.kaggle.com/account
# 2. Click "Create New API Token"
# 3. Save kaggle.json to ~/.kaggle/

# Download dataset
cd smart-healthcare-system/ml_models/data
kaggle datasets download -d joniarroba/noshowappointments
unzip noshowappointments.zip
```

#### Method 2: Manual Download
1. Visit: https://www.kaggle.com/datasets/joniarroba/noshowappointments
2. Click "Download" button
3. Save `KaggleV2-May-2016.csv` to `smart-healthcare-system/ml_models/data/`

### Step 2: Verify Dataset
```bash
cd smart-healthcare-system/ml_models/data
ls -lh KaggleV2-May-2016.csv
```

Expected output:
```
-rw-r--r-- 1 user user 37M KaggleV2-May-2016.csv
```

### Step 3: Train Models
```bash
cd smart-healthcare-system
python scripts/train_models.py
```

## 📊 Model Training Details

### 1. No-Show Prediction Model
- **Algorithm**: XGBoost Classifier
- **Training Time**: ~5-10 minutes
- **Features Used**:
  - Patient demographics (Age, Gender)
  - Medical history (Diabetes, Hypertension, etc.)
  - Appointment characteristics (Lead time, SMS reminder)
  - Temporal features (Day of week, Month, Hour)
- **Expected Performance**:
  - Accuracy: ~80-85%
  - AUC-ROC: ~0.88
  - Precision: ~0.55 (for no-show class)
  - Recall: ~0.60 (for no-show class)

### 2. Wait Time Estimation Model
- **Algorithm**: LSTM Neural Network
- **Training Time**: ~15-20 minutes
- **Features Used**:
  - Time of day
  - Day of week
  - Current queue length
  - Appointment type
- **Expected Performance**:
  - MAE: <10 minutes
  - RMSE: <15 minutes

### 3. Priority Classification Model
- **Algorithm**: Random Forest Classifier
- **Training Time**: ~3-5 minutes
- **Features Used**:
  - Age
  - Medical conditions
  - Symptoms keywords
  - Vital signs
- **Expected Performance**:
  - Accuracy: ~85-90%
  - F1-Score: ~0.87

## 🛠️ Training Script Usage

### Basic Training
```bash
python scripts/train_models.py
```

### Custom Training
Edit `scripts/train_models.py` to customize:
- Model hyperparameters
- Feature engineering
- Train/test split ratio
- Cross-validation settings

## 📁 Expected Output

After training, you should see:
```
smart-healthcare-system/
└── ml_models/
    └── trained_models/
        ├── noshow_model.pkl         # XGBoost model (~5MB)
        ├── priority_model.pkl       # Random Forest model (~10MB)
        └── waittime_model.h5        # LSTM model (~2MB)
```

## 🔍 Model Verification

### Test Models Locally
```python
import joblib
from tensorflow import keras

# Load models
noshow_model = joblib.load('ml_models/trained_models/noshow_model.pkl')
priority_model = joblib.load('ml_models/trained_models/priority_model.pkl')
waittime_model = keras.models.load_model('ml_models/trained_models/waittime_model.h5')

print("✅ All models loaded successfully!")
```

## 📈 Model Performance Monitoring

### Real-time Metrics
The API provides model health checks:
```bash
curl http://localhost:8000/api/v1/ai/health
```

Response:
```json
{
  "no_show_predictor": true,
  "wait_time_estimator": true,
  "priority_classifier": true,
  "status": "healthy"
}
```

## 🔄 Retraining Models

### When to Retrain
- Monthly: Update with new appointment data
- After significant changes in clinic operations
- When model performance degrades

### Retraining Process
```bash
# 1. Export new data from database
python scripts/export_training_data.py

# 2. Retrain models
python scripts/train_models.py

# 3. Evaluate new models
python scripts/evaluate_models.py

# 4. Deploy if performance improved
cp ml_models/trained_models/*.pkl ml_models/production/
```

## 🚨 Troubleshooting

### Issue: Dataset Not Found
```
❌ Dataset not found!
```
**Solution**: Ensure KaggleV2-May-2016.csv is in `ml_models/data/` directory

### Issue: TensorFlow Import Error
```
⚠️ TensorFlow not available
```
**Solution**: Install TensorFlow:
```bash
pip install tensorflow==2.18.0
```

### Issue: Memory Error During Training
**Solution**: Reduce batch size or use smaller dataset sample:
```python
# In train_models.py
df = df.sample(n=50000, random_state=42)  # Use 50k samples instead of all
```

### Issue: Model Performance is Poor
**Solutions**:
- Collect more diverse training data
- Perform feature engineering
- Tune hyperparameters
- Use cross-validation
- Check for data quality issues

## 📚 Additional Resources

- [XGBoost Documentation](https://xgboost.readthedocs.io/)
- [TensorFlow LSTM Guide](https://www.tensorflow.org/guide/keras/rnn)
- [Scikit-learn Random Forest](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html)
- [Medical No-Show Research Paper](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0177661)

## 💡 Tips for Better Models

1. **Feature Engineering**: Create domain-specific features
2. **Class Imbalance**: Use SMOTE for no-show prediction
3. **Ensemble Methods**: Combine multiple models
4. **Regular Updates**: Retrain with recent data
5. **A/B Testing**: Test model versions in production

## 🎯 Next Steps

1. ✅ Download dataset
2. ✅ Train models
3. ✅ Verify models load correctly
4. ✅ Start FastAPI backend
5. ✅ Test AI endpoints
6. ✅ Monitor performance
7. ✅ Schedule retraining