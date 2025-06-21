from django.db import models
from django.conf import settings
from django.core.validators import MinLengthValidator
from case.models import Case

class CommunicationLog(models.Model):
    MESSAGE_PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ]
    
    MESSAGE_TYPE_CHOICES = [
        ('general', 'General Communication'),
        ('case_update', 'Case Update'),
        ('alert', 'Alert'),
        ('instruction', 'Instruction'),
        ('report', 'Report'),
        ('request', 'Request')
    ]
    
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='sent_logs'
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='received_logs'
    )
    message_content = models.TextField(
        validators=[MinLengthValidator(5, "Message must be at least 5 characters long.")]
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    related_case = models.ForeignKey(
        Case,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='communications'
    )
    
    # Additional fields for better communication management
    message_type = models.CharField(
        max_length=20, 
        choices=MESSAGE_TYPE_CHOICES, 
        default='general'
    )
    priority = models.CharField(
        max_length=10, 
        choices=MESSAGE_PRIORITY_CHOICES, 
        default='medium'
    )
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    subject = models.CharField(max_length=200, blank=True)
    attachments = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['sender', 'timestamp']),
            models.Index(fields=['receiver', 'timestamp']),
            models.Index(fields=['related_case']),
            models.Index(fields=['is_read']),
            models.Index(fields=['priority']),
        ]

    def __str__(self):
        return f"{self.sender} -> {self.receiver} @ {self.timestamp}"
    
    @property
    def sender_name(self):
        return f"{self.sender.first_name} {self.sender.last_name}" if self.sender.first_name else self.sender.username
    
    @property
    def receiver_name(self):
        return f"{self.receiver.first_name} {self.receiver.last_name}" if self.receiver.first_name else self.receiver.username
    
    def mark_as_read(self):
        """Mark message as read and set read timestamp"""
        from django.utils import timezone
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=['is_read', 'read_at'])