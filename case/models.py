from django.db import models
from django.conf import settings


class Case(models.Model):
    STATUS_CHOICES = [('open', 'Open'), ('investigating', 'Investigating'), ('closed', 'Closed')]

    title = models.CharField(max_length=100)
    description = models.TextField()
    case_number = models.CharField(max_length=50, unique=True)
    assigned_officers = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True)
    related_incidents = models.ManyToManyField("incidents.Incident", related_name="cases", blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    priority = models.CharField(max_length=10)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.case_number
