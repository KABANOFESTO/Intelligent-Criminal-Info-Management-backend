from rest_framework import serializers
from .models import CrimePrediction

class CrimePredictionInputSerializer(serializers.Serializer):
    crime_type = serializers.CharField(max_length=100)
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    
    def validate_latitude(self, value):
        if not -90 <= value <= 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90")
        return value
    
    def validate_longitude(self, value):
        if not -180 <= value <= 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180")
        return value

class CrimePredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrimePrediction
        fields = [
            'id',
            'crime_type',
            'latitude', 
            'longitude',
            'encoded_crime_type',
            'predicted_severity',
            'prediction_value',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']