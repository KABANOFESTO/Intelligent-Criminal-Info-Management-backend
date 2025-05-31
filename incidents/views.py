from rest_framework import viewsets
from .models import Incident
from .serializers import IncidentSerializer

class IncidentViewSet(viewsets.ModelViewSet):
    queryset = Incident.objects.all().order_by('-created_at')
    serializer_class = IncidentSerializer
