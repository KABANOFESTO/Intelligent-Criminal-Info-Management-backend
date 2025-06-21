from rest_framework import serializers
from .models import Incident
import joblib
import numpy as np
import os

class IncidentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Incident
        fields = '__all__'

    def create(self, validated_data):
        crime_type = validated_data.get("crime_type")
        location = validated_data.get("location")

        # Default Rwanda coordinates (can be improved with frontend geolocation)
        latitude = -1.95
        longitude = 30.05

        # Paths
        model_path = os.path.join('ml', 'crime_severity_model.pkl')
        crime_encoder_path = os.path.join('ml', 'crime_label_encoder.pkl')
        location_encoder_path = os.path.join('ml', 'location_label_encoder.pkl')

        try:
            # Load model and encoders
            model = joblib.load(model_path)
            crime_encoder = joblib.load(crime_encoder_path)
            location_encoder = joblib.load(location_encoder_path)

            # Check for unseen categories
            if crime_type not in crime_encoder.classes_:
                raise ValueError(f"Unknown crime_type: {crime_type}")
            if location not in location_encoder.classes_:
                raise ValueError(f"Unknown location_type: {location}")

            # Encode inputs
            crime_encoded = crime_encoder.transform([crime_type])[0]
            location_encoded = location_encoder.transform([location])[0]

            # Build feature vector
            features = np.array([[crime_encoded, latitude, longitude, location_encoded]])
            prediction = model.predict(features)[0]
            validated_data['predicted_severity'] = bool(prediction)

        except Exception as e:
            # Log or raise depending on desired behavior
            print(f"⚠️ Prediction error: {e}")
            validated_data['predicted_severity'] = None

        return super().create(validated_data)
