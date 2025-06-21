from django.contrib.auth.models import AbstractUser
from django.db import models

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