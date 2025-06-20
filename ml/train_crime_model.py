# ml/train_crime_model_extended.py

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report
from imblearn.over_sampling import SMOTE
import joblib
import os

# Load dataset
df = pd.read_csv("ml/icimps_crime_incidents.csv")

# Drop rows missing required fields including location_type
df.dropna(subset=[
    'crime_type', 'Latitude', 'Longitude', 
    'is_severe', 'region_code', 'location_type'
], inplace=True)

# Show original class balance
print("\n📊 Original class distribution (before SMOTE):")
print(df['is_severe'].value_counts())

# Encode categorical fields
le_crime = LabelEncoder()
df['crime_type_encoded'] = le_crime.fit_transform(df['crime_type'])

le_location = LabelEncoder()
df['location_type_encoded'] = le_location.fit_transform(df['location_type'])

# Prepare features and target
X = df[['crime_type_encoded', 'Latitude', 'Longitude', 'location_type_encoded']]
y = df['is_severe']

# Apply SMOTE for balancing
sm = SMOTE(random_state=42)
X_resampled, y_resampled = sm.fit_resample(X, y)

# Show resampled class balance
print("\n✅ Resampled class distribution (after SMOTE):")
unique, counts = np.unique(y_resampled, return_counts=True)
print(dict(zip(unique, counts)))

# Split data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(
    X_resampled, y_resampled, test_size=0.2, random_state=42
)

# Train the model
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Evaluate model
y_pred = model.predict(X_test)
print("\n📈 Classification Report:")
print(classification_report(y_test, y_pred))

# Save trained model and encoders
os.makedirs("ml", exist_ok=True)
joblib.dump(model, "ml/crime_severity_model.pkl")
joblib.dump(le_crime, "ml/crime_label_encoder.pkl")
joblib.dump(le_location, "ml/location_label_encoder.pkl")
joblib.dump(le_crime.classes_.tolist(), "ml/crime_labels_list.pkl")
joblib.dump(le_location.classes_.tolist(), "ml/location_labels_list.pkl")

# Region risk score analysis
df['predicted_severity'] = model.predict(X)
region_risk_summary = df.groupby('region_code').agg(
    total_cases=('incident_id', 'count'),
    severe_cases=('predicted_severity', 'sum'),
    most_common_crime=('crime_type', lambda x: x.mode().iloc[0])
).reset_index()
region_risk_summary['risk_score'] = (region_risk_summary['severe_cases'] / region_risk_summary['total_cases']) * 100
region_risk_summary.to_csv("ml/region_risk_summary.csv", index=False)

print("\n📌 Region-based risk scores:")
print(region_risk_summary[['region_code', 'risk_score', 'most_common_crime']].head())

# Suspect risk level analysis
suspects = pd.read_csv("ml/icmps_suspects.csv")
suspects['risk_level'] = suspects['criminal_record_summary'].apply(
    lambda x: 'high' if 'Repeat' in str(x) else 'medium' if 'Gang' in str(x) else 'low'
)
le_risk = LabelEncoder()
suspects['risk_level_encoded'] = le_risk.fit_transform(suspects['risk_level'])
joblib.dump(le_risk, "ml/suspect_risk_label_encoder.pkl")
suspects.to_csv("ml/suspects_with_risk.csv", index=False)

print("\n✅ All models trained and saved successfully including suspects.")
