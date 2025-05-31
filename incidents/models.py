from django.db import models

class Incident(models.Model):
    URGENCY_LEVELS = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]

    crime_type = models.CharField(max_length=100)
    location = models.CharField(max_length=255)
    date = models.DateField()
    time = models.TimeField()
    urgency = models.CharField(max_length=10, choices=URGENCY_LEVELS)
    description = models.TextField()
    evidence = models.FileField(upload_to='evidence/', null=True, blank=True)
    
    contact_name = models.CharField(max_length=100)
    contact_phone = models.CharField(max_length=20)
    contact_email = models.EmailField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.crime_type} at {self.location}"
