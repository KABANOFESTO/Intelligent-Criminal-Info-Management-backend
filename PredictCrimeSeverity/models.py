from django.db import models
from django.utils import timezone

class CrimePrediction(models.Model):
    SEVERITY_CHOICES = [
        ('Severe', 'Severe'),
        ('Not Severe', 'Not Severe'),
    ]
    
    # Input data
    crime_type = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    
    # ML processing data
    encoded_crime_type = models.IntegerField()
    
    # Prediction results
    predicted_severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    prediction_value = models.IntegerField()  # Raw model output (0 or 1)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'crime_predictions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['crime_type']),
            models.Index(fields=['predicted_severity']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.crime_type} - {self.predicted_severity} ({self.created_at})"