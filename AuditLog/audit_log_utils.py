from .models import AuditLog
from django.contrib.auth import get_user_model
import json

def log_action(request, action, target_user=None, additional_data=None):
    """
    Helper function to create audit log entries
    """
    user = request.user if request.user.is_authenticated else None
    
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    ip_address = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
    
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
    
    data = None
    if additional_data:
        try:
            data = json.loads(json.dumps(additional_data))
        except:
            data = {'raw_data': str(additional_data)}
    
    AuditLog.objects.create(
        user=user,
        action=action,
        ip_address=ip_address,
        user_agent=user_agent,
        target_user=target_user,
        additional_data=data
    )