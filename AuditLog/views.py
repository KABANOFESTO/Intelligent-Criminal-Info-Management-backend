from rest_framework import generics
from rest_framework import permissions
from .models import AuditLog
from .serializers import AuditLogSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from authapi.permissions import IsAdmin

class AuditLogListView(generics.ListAPIView):
    queryset = AuditLog.objects.all().select_related('user', 'target_user')
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['action', 'user', 'target_user']
    ordering_fields = ['timestamp', 'action']
    ordering = ['-timestamp']