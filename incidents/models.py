from django.db import models
from django.core.exceptions import ValidationError
import joblib
import numpy as np
import os

class Incident(models.Model):
    URGENCY_LEVELS = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]

    crime_type = models.CharField(max_length=100)
    location = models.CharField(max_length=255)  # Assume this maps to 'location_type'
    date = models.DateField()
    time = models.TimeField()
    urgency = models.CharField(max_length=10, choices=URGENCY_LEVELS)
    description = models.TextField()
    evidence = models.FileField(upload_to='evidence/', null=True, blank=True)

    contact_name = models.CharField(max_length=100)
    contact_phone = models.CharField(max_length=20)
    contact_email = models.EmailField()

    predicted_severity = models.BooleanField(null=True, blank=True)  
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        
        if self.crime_type and self.location:
            try:
                model_path = os.path.join('ml', 'crime_severity_model.pkl')
                crime_encoder_path = os.path.join('ml', 'crime_label_encoder.pkl')
                location_encoder_path = os.path.join('ml', 'location_label_encoder.pkl')

                model = joblib.load(model_path)
                crime_encoder = joblib.load(crime_encoder_path)
                location_encoder = joblib.load(location_encoder_path)

                crime_encoded = crime_encoder.transform([self.crime_type])[0]
                location_encoded = location_encoder.transform([self.location])[0]

                latitude = -1.95  
                longitude = 30.05

                features = np.array([[crime_encoded, latitude, longitude, location_encoded]])
                prediction = model.predict(features)[0]

                self.predicted_severity = bool(prediction)
            except Exception as e:
                raise ValidationError(f"Prediction failed: {e}")

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.crime_type} at {self.location}"
