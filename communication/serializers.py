from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from communication.models import CommunicationLog 
from case.models import Case   

User = get_user_model()


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user serializer for communication logs"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'full_name', 'email']
        read_only_fields = ['id', 'username', 'email']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


class CaseBasicSerializer(serializers.ModelSerializer):
    """Basic case serializer for communication logs"""
    class Meta:
        model = Case
        fields = ['id', 'case_id', 'title', 'status']


class CommunicationLogSerializer(serializers.ModelSerializer):
    sender_details = UserBasicSerializer(source='sender', read_only=True)
    receiver_details = UserBasicSerializer(source='receiver', read_only=True)
    case_details = CaseBasicSerializer(source='related_case', read_only=True)
    sender_name = serializers.ReadOnlyField()
    receiver_name = serializers.ReadOnlyField()
    time_since = serializers.SerializerMethodField()
    
    class Meta:
        model = CommunicationLog
        fields = [
            'id', 'sender', 'receiver', 'sender_details', 'receiver_details',
            'sender_name', 'receiver_name', 'message_content', 'subject',
            'message_type', 'priority', 'timestamp', 'time_since',
            'related_case', 'case_details', 'is_read', 'read_at',
            'attachments'
        ]
        read_only_fields = ['timestamp', 'read_at', 'time_since']
    
    def get_time_since(self, obj):
        """Get human-readable time since message was sent"""
        now = timezone.now()
        diff = now - obj.timestamp
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"
    
    def validate(self, data):
        """Validate communication log data"""
        # Prevent self-messaging
        if data.get('sender') == data.get('receiver'):
            raise serializers.ValidationError("Sender and receiver cannot be the same person.")
        
        # Validate message content length
        message_content = data.get('message_content', '')
        if len(message_content.strip()) < 5:
            raise serializers.ValidationError("Message content must be at least 5 characters long.")
        
        return data
    
    def create(self, validated_data):
        # Set sender to current user if not provided
        if 'sender' not in validated_data:
            validated_data['sender'] = self.context['request'].user
        
        return super().create(validated_data)


class CommunicationLogCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for creating communication logs"""
    
    class Meta:
        model = CommunicationLog
        fields = [
            'receiver', 'message_content', 'subject', 'message_type',
            'priority', 'related_case', 'attachments'
        ]
    
    def validate(self, data):
        """Validate communication log data"""
        # Get sender from request context
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError("Authentication required.")
        
        # Prevent self-messaging
        if request.user == data.get('receiver'):
            raise serializers.ValidationError("You cannot send a message to yourself.")
        
        return data
    
    def create(self, validated_data):
        # Set sender to current user
        validated_data['sender'] = self.context['request'].user
        return super().create(validated_data)


class MessageReadSerializer(serializers.Serializer):
    """Serializer for marking messages as read"""
    message_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        help_text="List of message IDs to mark as read"
    )


class ConversationSerializer(serializers.Serializer):
    """Serializer for conversation threads"""
    participant = UserBasicSerializer()
    last_message = CommunicationLogSerializer()
    unread_count = serializers.IntegerField()
    last_activity = serializers.DateTimeField()