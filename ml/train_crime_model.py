# ml/train_crime_model.py

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report
from imblearn.over_sampling import SMOTE
import joblib
import os

# Load dataset
df = pd.read_csv("ml/icimps_crime_dataset_sample.csv")

# Drop missing values
df.dropna(subset=['crime_type', 'Latitude', 'Longitude', 'is_severe'], inplace=True)

# Check label distribution
print("🔍 Severity label distribution:")
print(df['is_severe'].value_counts())

# Encode 'crime_type'
le = LabelEncoder()
df['crime_type_encoded'] = le.fit_transform(df['crime_type'])

# Feature engineering (future-friendly placeholder)
# You could add more here, like time of day, region codes, etc.

# Select features
X = df[['crime_type_encoded', 'Latitude', 'Longitude']]
y = df['is_severe']

# Handle class imbalance using SMOTE (Optional but important if data is skewed)
sm = SMOTE(random_state=42)
X_resampled, y_resampled = sm.fit_resample(X, y)

# Split data
X_train, X_test, y_train, y_test = train_test_split(X_resampled, y_resampled, test_size=0.2, random_state=42)

# Train model
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Evaluate model
y_pred = model.predict(X_test)
print("\n📊 Classification Report:")
print(classification_report(y_test, y_pred))

# Save model and encoder
os.makedirs("ml", exist_ok=True)
joblib.dump(model, "ml/crime_severity_model.pkl")
joblib.dump(le, "ml/crime_label_encoder.pkl")

print("\n✅ Model and encoder trained and saved successfully.")
