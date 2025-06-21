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
    location = models.CharField(max_length=255)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
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

                # Handle unseen crime types
                try:
                    crime_encoded = crime_encoder.transform([self.crime_type])[0]
                except ValueError:
                    print(f"Warning: Unknown crime type '{self.crime_type}'. Using default.")
                    crime_encoded = 0

                # Handle unseen locations with GUARANTEED fallback
                try:
                    location_encoded = location_encoder.transform([self.location])[0]
                except ValueError:
                    print(f"Warning: Unknown location '{self.location}'. Trying fallback strategies.")
                    
                    # Strategy 1: Try to find a similar location (partial match)
                    location_found = False
                    location_lower = self.location.lower()
                    
                    for class_label in location_encoder.classes_:
                        if location_lower in class_label.lower() or class_label.lower() in location_lower:
                            try:
                                location_encoded = location_encoder.transform([class_label])[0]
                                location_found = True
                                print(f"Found similar location: {class_label}")
                                break
                            except ValueError:
                                continue  # This shouldn't happen, but just in case
                    
                    if not location_found:
                        # Strategy 2: Use coordinates to find the closest known location
                        rwanda_locations = {
                            'kigali': {'lat': -1.9441, 'lng': 30.0619},
                            'nyarugenge': {'lat': -1.9500, 'lng': 30.0588},
                            'gasabo': {'lat': -1.9411, 'lng': 30.1062},
                            'kicukiro': {'lat': -1.9891, 'lng': 30.1028},
                            'musanze': {'lat': -1.4833, 'lng': 29.6333},
                            'huye': {'lat': -2.5967, 'lng': 29.7378},
                        }
                        
                        current_location = self.location.lower()
                        if current_location in rwanda_locations:
                            # Find closest known location from encoder classes
                            min_distance = float('inf')
                            closest_location = None
                            current_coords = rwanda_locations[current_location]
                            
                            for class_label in location_encoder.classes_:
                                class_label_lower = class_label.lower()
                                if class_label_lower in rwanda_locations:
                                    known_coords = rwanda_locations[class_label_lower]
                                    distance = ((current_coords['lat'] - known_coords['lat'])**2 + 
                                              (current_coords['lng'] - known_coords['lng'])**2)**0.5
                                    if distance < min_distance:
                                        min_distance = distance
                                        closest_location = class_label
                            
                            if closest_location:
                                try:
                                    # CRITICAL FIX: Ensure closest_location is actually in encoder classes
                                    if closest_location in location_encoder.classes_:
                                        location_encoded = location_encoder.transform([closest_location])[0]
                                        print(f"Using closest location: {closest_location}")
                                    else:
                                        # Fallback to guaranteed safe option
                                        location_encoded = 0
                                        print("Closest location not in encoder classes, using default")
                                except ValueError:
                                    location_encoded = 0
                                    print("Transform failed for closest location, using default")
                            else:
                                location_encoded = 0
                                print("No closest location found, using default")
                        else:
                            location_encoded = 0
                            print("Location not in coordinate mapping, using default")

                # IMPROVED: Get available encoder classes for debugging
                print(f"Available location classes: {list(location_encoder.classes_)}")
                print(f"Available crime classes: {list(crime_encoder.classes_)}")

                # Set coordinates based on location
                location_coordinates = {
                    'nyarugenge': {'lat': -1.9500, 'lng': 30.0588},
                    'gasabo': {'lat': -1.9411, 'lng': 30.1062},
                    'kicukiro': {'lat': -1.9891, 'lng': 30.1028},
                    'kigali': {'lat': -1.9441, 'lng': 30.0619},
                    'musanze': {'lat': -1.4833, 'lng': 29.6333},
                    'huye': {'lat': -2.5967, 'lng': 29.7378},
                }
                
                location_key = self.location.lower()
                if location_key in location_coordinates:
                    latitude = location_coordinates[location_key]['lat']
                    longitude = location_coordinates[location_key]['lng']
                else:
                    # Default coordinates for Kigali
                    latitude = -1.95
                    longitude = 30.05

                features = np.array([[crime_encoded, latitude, longitude, location_encoded]])
                prediction = model.predict(features)[0]

                self.predicted_severity = bool(prediction)
                print(f"Prediction successful: {self.predicted_severity}")
                
            except Exception as e:
                print(f"Prediction error: {e}")
                # Set a default prediction instead of raising error
                self.predicted_severity = None
                # Only raise if you want the save to fail completely
                # raise ValidationError(f"Prediction failed: {e}")

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.crime_type} at {self.location}"


# OPTIONAL: Add a utility method to check what locations are supported
class IncidentManager(models.Manager):
    def get_supported_locations(self):
        """Return list of locations that the ML model was trained on"""
        try:
            location_encoder_path = os.path.join('ml', 'location_label_encoder.pkl')
            location_encoder = joblib.load(location_encoder_path)
            return list(location_encoder.classes_)
        except:
            return []
    
    def get_supported_crime_types(self):
        """Return list of crime types that the ML model was trained on"""
        try:
            crime_encoder_path = os.path.join('ml', 'crime_label_encoder.pkl')
            crime_encoder = joblib.load(crime_encoder_path)
            return list(crime_encoder.classes_)
        except:
            return []

# Add the manager to your model
# Incident.objects = IncidentManager()