from rest_framework import generics, permissions, filters, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Count, Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.auth import get_user_model
from communication.models import CommunicationLog
from .models import Case
from .serializers import (
    CaseSerializer, CaseListSerializer, 
    CommunicationLogSerializer, UserSerializer
)
User = get_user_model()

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

# Case Views
class CaseListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'case_number', 'description']
    ordering_fields = ['start_date', 'case_number', 'priority', 'status']
    ordering = ['-start_date']

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return CaseListSerializer
        return CaseSerializer

    def get_queryset(self):
        queryset = Case.objects.prefetch_related(
            'assigned_officers', 'related_incidents'
        )
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by priority
        priority_filter = self.request.query_params.get('priority', None)
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)
        
        # Filter by assigned officer
        officer_id = self.request.query_params.get('officer_id', None)
        if officer_id:
            queryset = queryset.filter(assigned_officers__id=officer_id)
        
        # Filter by date range
        date_from = self.request.query_params.get('date_from', None)
        date_to = self.request.query_params.get('date_to', None)
        if date_from:
            queryset = queryset.filter(start_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(start_date__lte=date_to)
        
        # Filter by current user's cases
        my_cases = self.request.query_params.get('my_cases', None)
        if my_cases == 'true':
            queryset = queryset.filter(assigned_officers=self.request.user)
            
        return queryset

class CaseDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CaseSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Case.objects.prefetch_related(
            'assigned_officers', 'related_incidents',
            Prefetch('communicationlog_set', 
                    queryset=CommunicationLog.objects.select_related('sender', 'receiver'))
        )

class CaseOfficersView(generics.ListAPIView):
    """Get all officers assigned to a specific case"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        case_id = self.kwargs['case_id']
        case = get_object_or_404(Case, id=case_id)
        return case.assigned_officers.all()

class OfficerCasesView(generics.ListAPIView):
    """Get all cases assigned to a specific officer"""
    serializer_class = CaseListSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        officer_id = self.kwargs['officer_id']
        return Case.objects.filter(
            assigned_officers__id=officer_id
        ).prefetch_related('assigned_officers')

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def assign_officer_to_case(request, case_id):
    """Assign an officer to a case"""
    case = get_object_or_404(Case, id=case_id)
    officer_id = request.data.get('officer_id')
    
    if not officer_id:
        return Response(
            {'error': 'officer_id is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        officer = User.objects.get(id=officer_id)
        case.assigned_officers.add(officer)
        return Response(
            {'message': f'Officer {officer.username} assigned to case {case.case_number}'}, 
            status=status.HTTP_200_OK
        )
    except User.DoesNotExist:
        return Response(
            {'error': 'Officer not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def remove_officer_from_case(request, case_id, officer_id):
    """Remove an officer from a case"""
    case = get_object_or_404(Case, id=case_id)
    
    try:
        officer = User.objects.get(id=officer_id)
        case.assigned_officers.remove(officer)
        return Response(
            {'message': f'Officer {officer.username} removed from case {case.case_number}'}, 
            status=status.HTTP_200_OK
        )
    except User.DoesNotExist:
        return Response(
            {'error': 'Officer not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['PATCH'])
@permission_classes([permissions.IsAuthenticated])
def update_case_status(request, case_id):
    """Update case status"""
    case = get_object_or_404(Case, id=case_id)
    new_status = request.data.get('status')
    
    if new_status not in ['open', 'investigating', 'closed']:
        return Response(
            {'error': 'Invalid status. Must be: open, investigating, or closed'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    case.status = new_status
    
    # Auto-set end_date when closing a case
    if new_status == 'closed' and not case.end_date:
        case.end_date = timezone.now().date()
    
    case.save()
    
    serializer = CaseSerializer(case)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def case_statistics(request):
    """Get case statistics"""
    total_cases = Case.objects.count()
    open_cases = Case.objects.filter(status='open').count()
    investigating_cases = Case.objects.filter(status='investigating').count()
    closed_cases = Case.objects.filter(status='closed').count()
    
    my_cases = Case.objects.filter(assigned_officers=request.user).count()
    
    return Response({
        'total_cases': total_cases,
        'open_cases': open_cases,
        'investigating_cases': investigating_cases,
        'closed_cases': closed_cases,
        'my_assigned_cases': my_cases,
        'case_distribution': {
            'open': open_cases,
            'investigating': investigating_cases,
            'closed': closed_cases
        }
    })