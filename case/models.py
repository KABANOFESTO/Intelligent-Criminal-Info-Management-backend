from django.db import models
from django.conf import settings

class Case(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('investigating', 'Investigating'),
        ('closed', 'Closed')
    ]

    title = models.CharField(max_length=100)
    description = models.TextField()
    case_id = models.CharField(max_length=100, unique=True)  # Ensure uniqueness
    assigned_officers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True
    )
    related_incidents = models.ManyToManyField(
        "incidents.Incident",
        related_name="cases",
        blank=True
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    priority = models.CharField(max_length=10)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.case_id

    def save(self, *args, **kwargs):
        if not self.case_id:
            # Auto-generate case_id if not provided (optional)
            last_case = Case.objects.order_by('-id').first()
            new_id = last_case.id + 1 if last_case else 1
            self.case_id = f"CASE-{new_id:04d}"
        super().save(*args, **kwargs)