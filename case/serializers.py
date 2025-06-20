from rest_framework import serializers
from django.contrib.auth import get_user_model
from communication.models import CommunicationLog
from incidents.models import Incident
  
from case.models import Case

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class IncidentReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Incident
        fields = ['id', 'title', 'incident_number']  # Adjust based on your IncidentReport model

class CaseSerializer(serializers.ModelSerializer):
    assigned_officers = UserSerializer(many=True, read_only=True)
    related_incidents = IncidentReportSerializer(many=True, read_only=True)
    
    # For write operations
    assigned_officers_ids = serializers.ListField(
        child=serializers.IntegerField(), 
        write_only=True, 
        required=False,
        allow_empty=True
    )
    related_incidents_ids = serializers.ListField(
        child=serializers.IntegerField(), 
        write_only=True, 
        required=False,
        allow_empty=True
    )
    
    # Computed fields
    communication_logs_count = serializers.SerializerMethodField()
    days_open = serializers.SerializerMethodField()

    class Meta:
        model = Case
        fields = [
            'id', 'title', 'description', 'case_number', 'assigned_officers',
            'related_incidents', 'start_date', 'end_date', 'status', 'priority',
            'notes', 'assigned_officers_ids', 'related_incidents_ids',
            'communication_logs_count', 'days_open'
        ]

    def get_communication_logs_count(self, obj):
        return obj.communicationlog_set.count()

    def get_days_open(self, obj):
        from django.utils import timezone
        if obj.end_date:
            return (obj.end_date - obj.start_date).days
        return (timezone.now().date() - obj.start_date).days

    def create(self, validated_data):
        assigned_officers_ids = validated_data.pop('assigned_officers_ids', [])
        related_incidents_ids = validated_data.pop('related_incidents_ids', [])
        
        case = Case.objects.create(**validated_data)
        
        if assigned_officers_ids:
            case.assigned_officers.set(assigned_officers_ids)
        if related_incidents_ids:
            case.related_incidents.set(related_incidents_ids)
            
        return case

    def update(self, instance, validated_data):
        assigned_officers_ids = validated_data.pop('assigned_officers_ids', None)
        related_incidents_ids = validated_data.pop('related_incidents_ids', None)
        
        # Update regular fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update many-to-many relationships
        if assigned_officers_ids is not None:
            instance.assigned_officers.set(assigned_officers_ids)
        if related_incidents_ids is not None:
            instance.related_incidents.set(related_incidents_ids)
            
        return instance

class CaseListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views"""
    assigned_officers_count = serializers.SerializerMethodField()
    days_open = serializers.SerializerMethodField()

    class Meta:
        model = Case
        fields = [
            'id', 'title', 'case_number', 'status', 'priority',
            'start_date', 'end_date', 'assigned_officers_count', 'days_open'
        ]

    def get_assigned_officers_count(self, obj):
        return obj.assigned_officers.count()
    
    def get_days_open(self, obj):
        from django.utils import timezone
        if obj.end_date:
            return (obj.end_date - obj.start_date).days
        return (timezone.now().date() - obj.start_date).days

# Updated CommunicationLog serializer to work with Case
class CommunicationLogSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    receiver = UserSerializer(read_only=True)
    related_case = CaseSerializer(read_only=True)
    
    # For write operations
    sender_id = serializers.IntegerField(write_only=True)
    receiver_id = serializers.IntegerField(write_only=True)
    related_case_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = CommunicationLog
        fields = [
            'id', 'sender', 'receiver', 'message_content', 
            'timestamp', 'related_case', 'sender_id', 
            'receiver_id', 'related_case_id'
        ]
        read_only_fields = ['timestamp']

    def create(self, validated_data):
        return CommunicationLog.objects.create(**validated_data)