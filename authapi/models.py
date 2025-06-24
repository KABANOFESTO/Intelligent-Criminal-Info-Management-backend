from django.contrib.auth.models import AbstractUser
from django.db import models
import secrets
import string

class User(AbstractUser):
    # Override username field to remove unique constraint
    username = models.CharField(max_length=150, unique=False)
    # Explicitly set email as unique for authentication
    email = models.EmailField(unique=True)
    
    ROLE_CHOICES = (
        ('Admin', 'Admin'),
        ('Police', 'Police'),
        ('Investigator', 'Investigator'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    
    STATUS_CHOICES = (
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')
    
    # Use email for authentication instead of username
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    profile_picture = models.ImageField(
        upload_to='profile_pictures/', 
        blank=True, 
        null=True,
        help_text="Upload a profile picture"
    )

    def __str__(self):
        return f"{self.username} ({self.role})"

    def get_profile_picture_url(self):
        """Return the URL of the profile picture or None if not set"""
        if self.profile_picture:
            return self.profile_picture.url
        return None

    @classmethod
    def generate_random_password(cls):
        """Generate a secure random password"""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(12))
    
    def save(self, *args, **kwargs):
        """Override save to keep is_active and status fields synchronized"""
        # Synchronize is_active with status
        if self.status == 'Active':
            self.is_active = True
        else:
            self.is_active = False
        
        super().save(*args, **kwargs)
    
    def activate(self):
        """Activate the user"""
        self.status = 'Active'
        self.is_active = True
        self.save(update_fields=['status', 'is_active'])
    
    def deactivate(self):
        """Deactivate the user"""
        self.status = 'Inactive'
        self.is_active = False
        self.save(update_fields=['status', 'is_active'])
    
    @property
    def is_user_active(self):
        """Check if user is active (using status field as source of truth)"""
        return self.status == 'Active'