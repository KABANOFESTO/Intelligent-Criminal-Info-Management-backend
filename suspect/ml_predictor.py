import joblib
import pandas as pd
import numpy as np
from django.conf import settings
import os
import logging

logger = logging.getLogger(__name__)

class CrimePredictor:
    def __init__(self):
        self.model_path = os.path.join(settings.BASE_DIR, 'ml')
        self.crime_model = None
        self.crime_encoder = None
        self.location_encoder = None
        self.suspect_risk_encoder = None
        self.load_models()
    
    def load_models(self):
        try:
            self.crime_model = joblib.load(os.path.join(self.model_path, 'crime_severity_model.pkl'))
            self.crime_encoder = joblib.load(os.path.join(self.model_path, 'crime_label_encoder.pkl'))
            self.location_encoder = joblib.load(os.path.join(self.model_path, 'location_label_encoder.pkl'))
            self.suspect_risk_encoder = joblib.load(os.path.join(self.model_path, 'suspect_risk_label_encoder.pkl'))
            logger.info("ML models loaded successfully")
        except Exception as e:
            logger.error(f"Error loading ML models: {e}")
            
    def predict_crime_severity(self, crime_type, latitude, longitude, location_type):
        try:
            if not all([self.crime_model, self.crime_encoder, self.location_encoder]):
                return None, None
            
            # Encode categorical variables
            crime_encoded = self.crime_encoder.transform([crime_type])[0]
            location_encoded = self.location_encoder.transform([location_type])[0]
            
            # Create feature array
            features = np.array([[crime_encoded, latitude, longitude, location_encoded]])
            
            # Predict
            prediction = self.crime_model.predict(features)[0]
            confidence = self.crime_model.predict_proba(features)[0].max()
            
            return bool(prediction), float(confidence)
        except Exception as e:
            logger.error(f"Error predicting crime severity: {e}")
            return None, None
    
    def predict_suspect_risk(self, criminal_record_summary):
        try:
            if not self.suspect_risk_encoder:
                return None, None
            
            # Determine risk level based on criminal record
            risk_level = 'high' if 'Repeat' in str(criminal_record_summary) else \
                        'medium' if 'Gang' in str(criminal_record_summary) else 'low'
            
            # Calculate risk score (simplified)
            risk_scores = {'low': 0.2, 'medium': 0.6, 'high': 0.9}
            risk_score = risk_scores.get(risk_level, 0.2)
            
            return risk_level, risk_score
        except Exception as e:
            logger.error(f"Error predicting suspect risk: {e}")
            return None, None


# Initialize predictor
predictor = CrimePredictor()