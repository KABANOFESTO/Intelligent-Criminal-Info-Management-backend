from rest_framework import serializers
from .models import Suspect, CrimeIncident, RegionRiskSummary

class SuspectSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    risk_color = serializers.ReadOnlyField(source='get_risk_color')
    
    class Meta:
        model = Suspect
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'alias', 
            'gender', 'age', 'national_id', 'known_addresses', 
            'criminal_record_summary', 'biometric_data', 'behavior_patterns',
            'predicted_risk_level', 'risk_score', 'prediction_confidence',
            'last_prediction_date', 'risk_color', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'predicted_risk_level', 'risk_score', 'prediction_confidence',
            'last_prediction_date', 'created_at', 'updated_at'
        ]

    def validate_criminal_record_summary(self, value):
        if not value or len(value.strip()) < 10:
            raise serializers.ValidationError("Criminal record summary must be at least 10 characters long.")
        return value

    def validate_national_id(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("National ID must contain only digits.")
        return value


class CrimeIncidentSerializer(serializers.ModelSerializer):
    suspects_details = SuspectSerializer(source='suspects', many=True, read_only=True)
    suspects = serializers.PrimaryKeyRelatedField(queryset=Suspect.objects.all(), many=True, required=False)
    
    class Meta:
        model = CrimeIncident
        fields = [
            'id', 'incident_id', 'crime_type', 'location_type',
            'latitude', 'longitude', 'region_code', 'description',
            'is_severe', 'severity_score', 'prediction_confidence',
            'suspects', 'suspects_details', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'is_severe', 'severity_score', 'prediction_confidence',
            'created_at', 'updated_at'
        ]

    def validate_latitude(self, value):
        if not -90 <= value <= 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90 degrees.")
        return value

    def validate_longitude(self, value):
        if not -180 <= value <= 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180 degrees.")
        return value


class RegionRiskSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = RegionRiskSummary
        fields = '__all__'
        read_only_fields = ['last_updated']