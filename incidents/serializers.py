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
        # Attempt prediction before saving
        try:
            crime_type = validated_data.get("crime_type")
            location = validated_data.get("location")

            # Load encoders and model
            model_path = os.path.join('ml', 'crime_severity_model.pkl')
            crime_encoder_path = os.path.join('ml', 'crime_label_encoder.pkl')
            location_encoder_path = os.path.join('ml', 'location_label_encoder.pkl')

            model = joblib.load(model_path)
            crime_encoder = joblib.load(crime_encoder_path)
            location_encoder = joblib.load(location_encoder_path)

            # Encode inputs
            crime_encoded = crime_encoder.transform([crime_type])[0]
            location_encoded = location_encoder.transform([location])[0]

            # Dummy coordinates for Rwanda (you can enhance this later with actual geolocation input)
            latitude = -1.95
            longitude = 30.05

            features = np.array([[crime_encoded, latitude, longitude, location_encoded]])
            predicted_severity = model.predict(features)[0]

            # Add prediction result to the model instance
            validated_data['predicted_severity'] = bool(predicted_severity)

        except Exception as e:
            print(f"⚠️ Prediction error: {e}")
            validated_data['predicted_severity'] = None

        return super().create(validated_data)
