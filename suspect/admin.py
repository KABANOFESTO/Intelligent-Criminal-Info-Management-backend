from django.contrib import admin
from .models import Suspect, CrimeIncident, RegionRiskSummary

@admin.register(Suspect)
class SuspectAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'age', 'gender', 'predicted_risk_level', 'risk_score', 'last_prediction_date']
    list_filter = ['predicted_risk_level', 'gender', 'created_at']
    search_fields = ['first_name', 'last_name', 'national_id', 'alias']
    readonly_fields = ['predicted_risk_level', 'risk_score', 'prediction_confidence', 'last_prediction_date']
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'alias', 'gender', 'age', 'national_id')
        }),
        ('Details', {
            'fields': ('known_addresses', 'criminal_record_summary', 'biometric_data', 'behavior_patterns')
        }),
        ('ML Predictions', {
            'fields': ('predicted_risk_level', 'risk_score', 'prediction_confidence', 'last_prediction_date'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CrimeIncident)
class CrimeIncidentAdmin(admin.ModelAdmin):
    list_display = ['incident_id', 'crime_type', 'region_code', 'is_severe', 'severity_score', 'created_at']
    list_filter = ['crime_type', 'location_type', 'is_severe', 'region_code', 'created_at']
    search_fields = ['incident_id', 'description']
    readonly_fields = ['is_severe', 'severity_score', 'prediction_confidence']
    filter_horizontal = ['suspects']


@admin.register(RegionRiskSummary)
class RegionRiskSummaryAdmin(admin.ModelAdmin):
    list_display = ['region_code', 'total_cases', 'severe_cases', 'risk_score', 'most_common_crime', 'last_updated']
    list_filter = ['last_updated', 'most_common_crime']
    search_fields = ['region_code']
    readonly_fields = ['last_updated']