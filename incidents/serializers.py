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

        # Get latitude and longitude from validated_data
        # Use provided coordinates or fall back to default Rwanda coordinates
        latitude = validated_data.get("latitude")
        longitude = validated_data.get("longitude")
        
        # If coordinates are not provided, use default Rwanda coordinates
        if latitude is None or longitude is None:
            latitude = -1.95
            longitude = 30.05
            print("⚠️ Using default Rwanda coordinates. Consider implementing frontend geolocation.")
        
        # Only add latitude/longitude to validated_data if they exist as model fields
        # This prevents the TypeError when creating the incident
        if hasattr(Incident, 'latitude'):
            validated_data['latitude'] = latitude
        if hasattr(Incident, 'longitude'):
            validated_data['longitude'] = longitude

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

            # Build feature vector using actual coordinates
            features = np.array([[crime_encoded, latitude, longitude, location_encoded]])
            prediction = model.predict(features)[0]
            validated_data['predicted_severity'] = bool(prediction)

            print(f"✅ Prediction made using coordinates: ({latitude}, {longitude})")

        except Exception as e:
            # Log or raise depending on desired behavior
            print(f"⚠️ Prediction error: {e}")
            validated_data['predicted_severity'] = None

        return super().create(validated_data)