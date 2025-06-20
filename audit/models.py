from django.db import models
from django.conf import settings

class AuditLog(models.Model):
    action_type = models.CharField(max_length=100)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    affected_model = models.CharField(max_length=100)
    model_instance_id = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.TextField()

    def __str__(self):
        return f"{self.action_type} by {self.performed_by} on {self.timestamp}"
