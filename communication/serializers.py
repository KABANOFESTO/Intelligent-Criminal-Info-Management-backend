from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone

# Import models directly
from communication.models import CommunicationLog
from case.models import Case
from case.models import Case

User = get_user_model()

class UserBasicSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'full_name', 'email']
        read_only_fields = ['id', 'username', 'email']

    def get_full_name(self, obj):
        if obj.first_name and obj.last_name:
            return f"{obj.first_name} {obj.last_name}".strip()
        return obj.username

class CaseBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Case
        fields = ['id', 'case_id', 'title', 'status']
        read_only_fields = ['id', 'case_id', 'title', 'status']

class CommunicationLogCreateSerializer(serializers.ModelSerializer):
    """Create serializer with proper case handling"""
    related_case = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Use case reference (e.g., 'CASE-2025-0002')"
    )

    class Meta:
        model = CommunicationLog
        fields = [
            'receiver',
            'message_content', 
            'subject',
            'message_type',
            'priority',
            'related_case',
            'attachments',
        ]

    def validate_related_case(self, value):
        """Validate case reference exists but return the case_id string"""
        if not value:
            return None
        
        try:
            case = Case.objects.get(case_id=value)
            return value  # Return the string, not the case object
        except Case.DoesNotExist:
            raise serializers.ValidationError(f"Case with reference '{value}' does not exist.")
        except Exception as e:
            raise serializers.ValidationError(f"Invalid case reference: {str(e)}")

    def validate(self, data):
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError("Authentication required.")
        
        receiver = data.get('receiver')
        if receiver and request.user.id == receiver.id:
            raise serializers.ValidationError({
                'receiver': "You cannot send a message to yourself."
            })
        
        content = data.get('message_content', '')
        if not content or len(content.strip()) < 5:
            raise serializers.ValidationError({
                'message_content': "Message content must be at least 5 characters long."
            })
            
        return data

    def create(self, validated_data):
        validated_data['sender'] = self.context['request'].user
        
        # Handle case reference conversion
        case_reference = validated_data.pop('related_case', None)
        if case_reference:
            try:
                case = Case.objects.get(case_id=case_reference)
                validated_data['related_case'] = case
            except Case.DoesNotExist:
                # This shouldn't happen due to validation, but just in case
                pass
            except Exception as e:
                print(f"Error setting case in create: {e}")
        
        return super().create(validated_data)

class CommunicationLogSerializer(serializers.ModelSerializer):
    sender_details = UserBasicSerializer(source='sender', read_only=True)
    receiver_details = UserBasicSerializer(source='receiver', read_only=True)
    case_details = CaseBasicSerializer(source='related_case', read_only=True)
    sender_name = serializers.ReadOnlyField()
    receiver_name = serializers.ReadOnlyField()
    time_since = serializers.SerializerMethodField()
    related_case = serializers.CharField(source='related_case.case_id', read_only=True)

    class Meta:
        model = CommunicationLog
        fields = [
            'id', 'sender', 'receiver', 'sender_details', 'receiver_details',
            'sender_name', 'receiver_name', 'message_content', 'subject',
            'message_type', 'priority', 'timestamp', 'time_since',
            'related_case', 'case_details', 'is_read', 'read_at', 'attachments'
        ]
        read_only_fields = ['id', 'timestamp', 'read_at', 'time_since', 'sender']

    def get_time_since(self, obj):
        now = timezone.now()
        diff = now - obj.timestamp

        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds >= 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        return "Just now"

class MessageReadSerializer(serializers.Serializer):
    message_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
        help_text="List of message IDs to mark as read",
    )

    def validate_message_ids(self, value):
        if not value:
            raise serializers.ValidationError("At least one message ID is required.")
        
        unique_ids = list(dict.fromkeys(value))
        
        request = self.context.get('request')
        if request and request.user:
            existing_messages = CommunicationLog.objects.filter(
                id__in=unique_ids,
                receiver=request.user
            ).values_list('id', flat=True)
            
            missing_ids = set(unique_ids) - set(existing_messages)
            if missing_ids:
                raise serializers.ValidationError(
                    f"Messages with IDs {list(missing_ids)} do not exist or you don't have permission to access them."
                )
        
        return unique_ids

class ConversationSerializer(serializers.Serializer):
    participant = UserBasicSerializer()
    last_message = CommunicationLogSerializer()
    unread_count = serializers.IntegerField(min_value=0)
    last_activity = serializers.DateTimeField()

    def validate_unread_count(self, value):
        if value < 0:
            raise serializers.ValidationError("Unread count cannot be negative.")
        return value

# Alternative serializer if the above doesn't work
class CommunicationLogCreateSerializerAlternative(serializers.ModelSerializer):
    """Alternative approach using direct model creation"""
    related_case = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Use case reference (e.g., 'CASE-2025-0002')"
    )

    class Meta:
        model = CommunicationLog
        fields = [
            'receiver',
            'message_content', 
            'subject',
            'message_type',
            'priority',
            'related_case',
            'attachments',
        ]

    def validate_related_case(self, value):
        if not value:
            return None
        
        try:
            Case = apps.get_model('case', 'Case')
            case = Case.objects.get(case_id=value)
            return value
        except Case.DoesNotExist:
            raise serializers.ValidationError(f"Case with reference '{value}' does not exist.")

    def validate(self, data):
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError("Authentication required.")
        
        receiver = data.get('receiver')
        if receiver and request.user.id == receiver.id:
            raise serializers.ValidationError({
                'receiver': "You cannot send a message to yourself."
            })
        
        content = data.get('message_content', '')
        if not content or len(content.strip()) < 5:
            raise serializers.ValidationError({
                'message_content': "Message content must be at least 5 characters long."
            })
            
        return data

    def create(self, validated_data):
        validated_data['sender'] = self.context['request'].user
        
        case_reference = validated_data.pop('related_case', None)
        
        # Create the communication log instance
        communication_log = CommunicationLog(**validated_data)
        
        # Handle case assignment separately
        if case_reference:
            try:
                Case = apps.get_model('case', 'Case')
                case = Case.objects.get(case_id=case_reference)
                communication_log.related_case = case
            except Case.DoesNotExist:
                pass  # Already validated
            except Exception as e:
                print(f"Error setting case: {e}")
        
        communication_log.save()
        return communication_log