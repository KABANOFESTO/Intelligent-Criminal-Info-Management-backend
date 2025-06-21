from rest_framework import serializers
from django.contrib.auth import get_user_model
from communication.models import CommunicationLog
from incidents.models import Incident
from .models import Case
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class IncidentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Incident
        fields = ['id', 'crime_type', 'location', 'description', 'date', 'time', 'urgency']

class CaseSerializer(serializers.ModelSerializer):
    assigned_officers = UserSerializer(many=True, read_only=True)
    related_incidents = IncidentSerializer(many=True, read_only=True)
    
    assigned_officers_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=User.objects.all(),
        source='assigned_officers',
        required=False
    )
    related_incidents_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=Incident.objects.all(),
        source='related_incidents',
        required=False
    )
    
    communication_logs_count = serializers.SerializerMethodField()
    days_open = serializers.SerializerMethodField()

    class Meta:
        model = Case
        fields = [
            'id', 'title', 'description', 'case_id', 'start_date', 'end_date',
            'status', 'priority', 'notes', 'assigned_officers', 'related_incidents',
            'assigned_officers_ids', 'related_incidents_ids', 
            'communication_logs_count', 'days_open'
        ]
        extra_kwargs = {
            'case_id': {'required': True}
        }

    def validate_case_id(self, value):  # Changed from validate_case_number to validate_case_id
        if not value.startswith('CASE-'):
            raise serializers.ValidationError("Case ID must start with 'CASE-'")
        # Check if we're updating (self.instance exists) or creating (self.instance is None)
        if self.instance is None:  # Creating new case
            if Case.objects.filter(case_id=value).exists():
                raise serializers.ValidationError("Case with this ID already exists")
        else:  # Updating existing case
            if Case.objects.filter(case_id=value).exclude(pk=self.instance.pk).exists():
                raise serializers.ValidationError("Case with this ID already exists")
        return value

    def create(self, validated_data):
        logger.debug(f"CaseSerializer.create called with: {validated_data}")

        # Defensive: DRF should map assigned_officers_ids -> assigned_officers, but let's check both
        assigned_officers = validated_data.pop('assigned_officers', None)
        related_incidents = validated_data.pop('related_incidents', None)
        
        # Defensive: ensure these are always lists (not a string or None)
        if assigned_officers is None:
            assigned_officers = []
        elif not isinstance(assigned_officers, (list, tuple)):
            raise serializers.ValidationError({
                'assigned_officers_ids': 'assigned_officers_ids must be a list of officer IDs.'
            })
        if related_incidents is None:
            related_incidents = []
        elif not isinstance(related_incidents, (list, tuple)):
            raise serializers.ValidationError({
                'related_incidents_ids': 'related_incidents_ids must be a list of incident IDs.'
            })

        logger.debug(f"About to create case with data: {validated_data}")
        logger.debug(f"Assigned officers: {assigned_officers}")
        logger.debug(f"Related incidents: {related_incidents}")
        
        try:
            case = Case.objects.create(**validated_data)
            logger.debug(f"Case created successfully: {case}")

            if assigned_officers:
                case.assigned_officers.set(assigned_officers)
                logger.debug(f"Assigned officers set: {list(case.assigned_officers.all())}")
            if related_incidents:
                case.related_incidents.set(related_incidents)
                logger.debug(f"Related incidents set: {list(case.related_incidents.all())}")

            return case
        except Exception as e:
            logger.error(f"Error creating case: {str(e)}")
            logger.error(f"Validated data that caused error: {validated_data}")
            raise
    
    def update(self, instance, validated_data):
        # Extract many-to-many data
        assigned_officers = validated_data.pop('assigned_officers', None)
        related_incidents = validated_data.pop('related_incidents', None)
        
        # Update scalar fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update many-to-many relationships
        if assigned_officers is not None:
            instance.assigned_officers.set(assigned_officers)
        if related_incidents is not None:
            instance.related_incidents.set(related_incidents)
            
        return instance

    def get_communication_logs_count(self, obj):
        import logging
        from case.models import Case
        from communication.models import CommunicationLog
        logger = logging.getLogger(__name__)
        try:
            # Defensive: If obj is a string, try to get the Case instance
            if isinstance(obj, str):
                logger.warning(f"get_communication_logs_count called with str: {obj}")
                try:
                    obj = Case.objects.get(case_id=obj)
                except Case.DoesNotExist:
                    logger.error(f"No Case found for case_id={obj}")
                    return 0
            if not isinstance(obj, Case):
                logger.error(f"get_communication_logs_count called with non-Case: type={type(obj)}, value={obj}")
                return 0
            return CommunicationLog.objects.filter(related_case=obj).count()
        except Exception as e:
            logger.error(f"Exception in get_communication_logs_count: {e}")
            return 0

    def get_days_open(self, obj):
        from django.utils import timezone
        if obj.end_date:
            return (obj.end_date - obj.start_date).days
        return (timezone.now().date() - obj.start_date).days

class CaseListSerializer(serializers.ModelSerializer):
    assigned_officers_count = serializers.SerializerMethodField()
    days_open = serializers.SerializerMethodField()

    class Meta:
        model = Case
        fields = [
            'id', 'title', 'case_id', 'status', 'priority',
            'start_date', 'end_date', 'assigned_officers_count', 'days_open'
        ]

    def get_assigned_officers_count(self, obj):
        return obj.assigned_officers.count()
    
    def get_days_open(self, obj):
        from django.utils import timezone
        if obj.end_date:
            return (obj.end_date - obj.start_date).days
        return (timezone.now().date() - obj.start_date).days

class CommunicationLogSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    receiver = UserSerializer(read_only=True)
    
    # Use PrimaryKeyRelatedField properly
    related_case = serializers.PrimaryKeyRelatedField(
        queryset=Case.objects.all(),
        required=False,
        allow_null=True
    )
    
    # Add this if you want to display case number in responses
    related_case_number = serializers.CharField(source='related_case.case_id', read_only=True)
    
    # Add write-only field for case number input
    related_case_number_input = serializers.CharField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = CommunicationLog
        fields = [
            'id', 'sender', 'receiver', 'message_content', 
            'timestamp', 'related_case', 'related_case_number',
            'related_case_number_input'
        ]
        read_only_fields = ['timestamp']
    
    def validate_related_case_number_input(self, value):
        """Validate case number input"""
        if value:
            if not Case.objects.filter(case_id=value).exists():
                raise serializers.ValidationError(f"Case with number '{value}' does not exist")
        return value
    
    def create(self, validated_data):
        # Handle case number input
        case_number_input = validated_data.pop('related_case_number_input', None)
        if case_number_input:
            try:
                case = Case.objects.get(case_id=case_number_input)
                validated_data['related_case'] = case
            except Case.DoesNotExist:
                raise serializers.ValidationError(f"Case with number '{case_number_input}' does not exist")
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        # Handle case number input
        case_number_input = validated_data.pop('related_case_number_input', None)
        if case_number_input:
            try:
                case = Case.objects.get(case_id=case_number_input)
                validated_data['related_case'] = case
            except Case.DoesNotExist:
                raise serializers.ValidationError(f"Case with number '{case_number_input}' does not exist")
        
        return super().update(instance, validated_data)