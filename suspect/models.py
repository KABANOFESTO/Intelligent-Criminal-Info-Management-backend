from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import json

class Suspect(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    
    RISK_LEVEL_CHOICES = [
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
    ]
    
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    alias = models.CharField(max_length=100, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    age = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(150)])
    national_id = models.CharField(max_length=16, unique=True)
    known_addresses = models.TextField()
    criminal_record_summary = models.TextField()
    biometric_data = models.JSONField(blank=True, null=True)
    behavior_patterns = models.JSONField(blank=True, null=True)
    
    # ML Prediction fields
    predicted_risk_level = models.CharField(max_length=10, choices=RISK_LEVEL_CHOICES, blank=True, null=True)
    risk_score = models.FloatField(blank=True, null=True, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    prediction_confidence = models.FloatField(blank=True, null=True, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    last_prediction_date = models.DateTimeField(auto_now=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['predicted_risk_level']),
            models.Index(fields=['national_id']),
            models.Index(fields=['last_prediction_date']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_predicted_risk_level_display() or 'Unassessed'})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_risk_color(self):
        """Return color code for risk level visualization"""
        colors = {
            'low': '#28a745',      # Green
            'medium': '#ffc107',   # Yellow
            'high': '#dc3545',     # Red
        }
        return colors.get(self.predicted_risk_level, '#6c757d')  # Gray for unassessed


class CrimeIncident(models.Model):
    CRIME_TYPE_CHOICES = [
        ('theft', 'Theft'),
        ('assault', 'Assault'),
        ('burglary', 'Burglary'),
        ('fraud', 'Fraud'),
        ('drug_offense', 'Drug Offense'),
        ('vandalism', 'Vandalism'),
        ('robbery', 'Robbery'),
        ('domestic_violence', 'Domestic Violence'),
        ('cybercrime', 'Cybercrime'),
        ('other', 'Other'),
    ]
    
    LOCATION_TYPE_CHOICES = [
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('public', 'Public Space'),
        ('educational', 'Educational'),
        ('transport', 'Transportation'),
        ('other', 'Other'),
    ]
    
    incident_id = models.CharField(max_length=20, unique=True)
    crime_type = models.CharField(max_length=50, choices=CRIME_TYPE_CHOICES)
    location_type = models.CharField(max_length=50, choices=LOCATION_TYPE_CHOICES)
    latitude = models.FloatField()
    longitude = models.FloatField()
    region_code = models.CharField(max_length=10)
    description = models.TextField()
    
    # ML Prediction fields
    is_severe = models.BooleanField(default=False)
    severity_score = models.FloatField(blank=True, null=True, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    prediction_confidence = models.FloatField(blank=True, null=True, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    
    # Related suspects
    suspects = models.ManyToManyField(Suspect, blank=True, related_name='incidents')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['crime_type']),
            models.Index(fields=['region_code']),
            models.Index(fields=['is_severe']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.incident_id} - {self.get_crime_type_display()}"


class RegionRiskSummary(models.Model):
    region_code = models.CharField(max_length=10, unique=True)
    total_cases = models.PositiveIntegerField(default=0)
    severe_cases = models.PositiveIntegerField(default=0)
    risk_score = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)])
    most_common_crime = models.CharField(max_length=50, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-risk_score']
        verbose_name_plural = "Region Risk Summaries"
        
    def __str__(self):
        return f"Region {self.region_code} - Risk: {self.risk_score:.1f}%"