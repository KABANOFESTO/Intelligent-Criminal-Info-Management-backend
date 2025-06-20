from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count, Avg
from django.utils import timezone
from .models import Suspect, CrimeIncident, RegionRiskSummary
from .serializers import SuspectSerializer, CrimeIncidentSerializer, RegionRiskSummarySerializer
from .ml_predictor import predictor
import logging

logger = logging.getLogger(__name__)

class SuspectViewSet(viewsets.ModelViewSet):
    queryset = Suspect.objects.all()
    serializer_class = SuspectSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        # Save the suspect first
        suspect = serializer.save()
        
        # Generate ML prediction
        risk_level, risk_score = predictor.predict_suspect_risk(suspect.criminal_record_summary)
        
        if risk_level and risk_score:
            suspect.predicted_risk_level = risk_level
            suspect.risk_score = risk_score
            suspect.prediction_confidence = 0.85  # Default confidence
            suspect.save()
            logger.info(f"Suspect {suspect.id} created with risk level: {risk_level}")
        else:
            logger.warning(f"Could not generate prediction for suspect {suspect.id}")
    
    def perform_update(self, serializer):
        # Save the updated suspect
        suspect = serializer.save()
        
        # Regenerate ML prediction if criminal record changed
        if 'criminal_record_summary' in serializer.validated_data:
            risk_level, risk_score = predictor.predict_suspect_risk(suspect.criminal_record_summary)
            
            if risk_level and risk_score:
                suspect.predicted_risk_level = risk_level
                suspect.risk_score = risk_score
                suspect.prediction_confidence = 0.85
                suspect.save()
                logger.info(f"Suspect {suspect.id} updated with new risk level: {risk_level}")
    
    @action(detail=False, methods=['get'])
    def high_risk(self, request):
        """Get all high-risk suspects"""
        high_risk_suspects = self.queryset.filter(predicted_risk_level='high')
        serializer = self.get_serializer(high_risk_suspects, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def risk_statistics(self, request):
        """Get risk level statistics"""
        stats = self.queryset.values('predicted_risk_level').annotate(
            count=Count('id')
        ).order_by('predicted_risk_level')
        
        total = self.queryset.count()
        result = {
            'total_suspects': total,
            'risk_breakdown': list(stats),
            'average_risk_score': self.queryset.aggregate(
                avg_risk=Avg('risk_score')
            )['avg_risk'] or 0
        }
        
        return Response(result)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by risk level
        risk_level = self.request.query_params.get('risk_level')
        if risk_level:
            queryset = queryset.filter(predicted_risk_level=risk_level)
        
        # Search functionality
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(alias__icontains=search) |
                Q(national_id__icontains=search)
            )
        
        return queryset


class CrimeIncidentViewSet(viewsets.ModelViewSet):
    queryset = CrimeIncident.objects.all()
    serializer_class = CrimeIncidentSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        # Save the incident first
        incident = serializer.save()
        
        # Generate ML prediction
        is_severe, confidence = predictor.predict_crime_severity(
            incident.crime_type,
            incident.latitude,
            incident.longitude,
            incident.location_type
        )
        
        if is_severe is not None and confidence is not None:
            incident.is_severe = is_severe
            incident.severity_score = 0.8 if is_severe else 0.3  # Simplified scoring
            incident.prediction_confidence = confidence
            incident.save()
            logger.info(f"Incident {incident.id} created with severity: {is_severe}")
            
            # Update region risk summary
            self._update_region_risk(incident.region_code)
        else:
            logger.warning(f"Could not generate prediction for incident {incident.id}")
    
    def _update_region_risk(self, region_code):
        """Update or create region risk summary"""
        try:
            incidents = CrimeIncident.objects.filter(region_code=region_code)
            total_cases = incidents.count()
            severe_cases = incidents.filter(is_severe=True).count()
            
            if total_cases > 0:
                risk_score = (severe_cases / total_cases) * 100
                most_common_crime = incidents.values('crime_type').annotate(
                    count=Count('crime_type')
                ).order_by('-count').first()
                
                RegionRiskSummary.objects.update_or_create(
                    region_code=region_code,
                    defaults={
                        'total_cases': total_cases,
                        'severe_cases': severe_cases,
                        'risk_score': risk_score,
                        'most_common_crime': most_common_crime['crime_type'] if most_common_crime else ''
                    }
                )
        except Exception as e:
            logger.error(f"Error updating region risk for {region_code}: {e}")
    
    @action(detail=False, methods=['get'])
    def severe_incidents(self, request):
        """Get all severe incidents"""
        severe_incidents = self.queryset.filter(is_severe=True)
        serializer = self.get_serializer(severe_incidents, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_region(self, request):
        """Get incidents grouped by region"""
        region = request.query_params.get('region_code')
        if region:
            incidents = self.queryset.filter(region_code=region)
            serializer = self.get_serializer(incidents, many=True)
            return Response(serializer.data)
        
        # Return all regions with incident counts
        regions = self.queryset.values('region_code').annotate(
            incident_count=Count('id'),
            severe_count=Count('id', filter=Q(is_severe=True))
        ).order_by('-incident_count')
        
        return Response(list(regions))
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by severity
        is_severe = self.request.query_params.get('is_severe')
        if is_severe is not None:
            queryset = queryset.filter(is_severe=is_severe.lower() == 'true')
        
        # Filter by crime type
        crime_type = self.request.query_params.get('crime_type')
        if crime_type:
            queryset = queryset.filter(crime_type=crime_type)
        
        # Filter by region
        region_code = self.request.query_params.get('region_code')
        if region_code:
            queryset = queryset.filter(region_code=region_code)
        
        return queryset


class RegionRiskSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RegionRiskSummary.objects.all()
    serializer_class = RegionRiskSummarySerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def high_risk_regions(self, request):
        """Get regions with risk score above threshold"""
        threshold = float(request.query_params.get('threshold', 50.0))
        high_risk = self.queryset.filter(risk_score__gte=threshold)
        serializer = self.get_serializer(high_risk, many=True)
        return Response(serializer.data)