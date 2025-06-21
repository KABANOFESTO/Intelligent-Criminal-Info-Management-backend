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
import logging
import traceback

from .serializers import (
    CaseSerializer, CaseListSerializer, 
    CommunicationLogSerializer, UserSerializer
)

User = get_user_model()
logger = logging.getLogger(__name__)

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

# Case Views
class CaseListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'case_id', 'description']
    ordering_fields = ['start_date', 'case_id', 'priority', 'status']
    ordering = ['-start_date']

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return CaseListSerializer
        return CaseSerializer

    def create(self, request, *args, **kwargs):
        """Override create method with proper error handling and debugging"""
        logger.debug(f"Creating case with data: {request.data}")
        
        try:
            # Get serializer with request data
            serializer = self.get_serializer(data=request.data)
            
            # Validate the data
            if not serializer.is_valid():
                logger.error(f"Serializer validation failed: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            logger.debug(f"Serializer validated data: {serializer.validated_data}")
            
            # Save the case
            case = serializer.save()
            logger.info(f"Case created successfully: {case.case_id}")
            
            # Return success response
            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data, 
                status=status.HTTP_201_CREATED, 
                headers=headers
            )
            
        except Exception as e:
            logger.error(f"Error creating case: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            # Return error response
            return Response(
                {
                    "error": "Failed to create case",
                    "detail": str(e)
                }, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get_queryset(self):
        """Get filtered queryset for cases"""
        queryset = Case.objects.select_related().prefetch_related(
            'assigned_officers', 
            'related_incidents'
        )
        
        # Apply filters
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        priority_filter = self.request.query_params.get('priority')
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)
        
        officer_id = self.request.query_params.get('officer_id')
        if officer_id:
            try:
                queryset = queryset.filter(assigned_officers__id=int(officer_id))
            except ValueError:
                pass  # Invalid officer_id, ignore filter
        
        # Date range filters
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            try:
                queryset = queryset.filter(start_date__gte=date_from)
            except ValueError:
                pass  # Invalid date format, ignore filter
        if date_to:
            try:
                queryset = queryset.filter(start_date__lte=date_to)
            except ValueError:
                pass  # Invalid date format, ignore filter
        
        # My cases filter
        my_cases = self.request.query_params.get('my_cases')
        if my_cases and my_cases.lower() == 'true':
            queryset = queryset.filter(assigned_officers=self.request.user)
            
        return queryset.distinct()  # Ensure no duplicates from joins

class CaseDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CaseSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'case_id'  # Use string-based case_id for lookups
    
    def get_queryset(self):
        return Case.objects.select_related().prefetch_related(
            'assigned_officers', 
            'related_incidents'
        )
    
    def update(self, request, *args, **kwargs):
        """Override update with proper error handling"""
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            
            if not serializer.is_valid():
                logger.error(f"Update validation failed: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            case = serializer.save()
            logger.info(f"Case updated successfully: {case.case_id}")
            
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error updating case: {str(e)}")
            return Response(
                {"error": "Failed to update case", "detail": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, *args, **kwargs):
        """Override destroy with proper error handling"""
        try:
            instance = self.get_object()
            case_id = instance.case_id
            self.perform_destroy(instance)
            logger.info(f"Case deleted successfully: {case_id}")
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            logger.error(f"Error deleting case: {str(e)}")
            return Response(
                {"error": "Failed to delete case", "detail": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CaseOfficersView(generics.ListAPIView):
    """Get all officers assigned to a specific case"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        case_id = self.kwargs.get('case_id')
        if not case_id:
            return User.objects.none()
        
        try:
            case = get_object_or_404(Case, case_id=case_id)
            return case.assigned_officers.all()
        except (ValueError, TypeError):
            return User.objects.none()

class OfficerCasesView(generics.ListAPIView):
    """Get all cases assigned to a specific officer"""
    serializer_class = CaseListSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        officer_id = self.kwargs.get('officer_id')
        if not officer_id:
            return Case.objects.none()
        
        try:
            return Case.objects.filter(
                assigned_officers__id=int(officer_id)
            ).prefetch_related('assigned_officers', 'related_incidents')
        except (ValueError, TypeError):
            return Case.objects.none()

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def assign_officer_to_case(request, case_id):
    """Assign an officer to a case"""
    try:
        case = get_object_or_404(Case, case_id=case_id)
    except (ValueError, TypeError):
        return Response(
            {'error': 'Invalid case ID'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    officer_id = request.data.get('officer_id')
    
    if not officer_id:
        return Response(
            {'error': 'officer_id is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        officer = get_object_or_404(User, id=int(officer_id))
        
        # Check if officer is already assigned
        if case.assigned_officers.filter(id=officer.id).exists():
            return Response(
                {'message': f'Officer {officer.username} is already assigned to case {case.case_id}'}, 
                status=status.HTTP_200_OK
            )
        
        case.assigned_officers.add(officer)
        logger.info(f"Officer {officer.username} assigned to case {case.case_id}")
        
        return Response(
            {'message': f'Officer {officer.username} assigned to case {case.case_id}'}, 
            status=status.HTTP_200_OK
        )
        
    except (ValueError, TypeError):
        return Response(
            {'error': 'Invalid officer ID'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error assigning officer to case: {str(e)}")
        return Response(
            {'error': 'Failed to assign officer'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def remove_officer_from_case(request, case_id, officer_id):
    """Remove an officer from a case"""
    try:
        case = get_object_or_404(Case, case_id=case_id)
        officer = get_object_or_404(User, id=int(officer_id))
        
        # Check if officer is actually assigned
        if not case.assigned_officers.filter(id=officer.id).exists():
            return Response(
                {'message': f'Officer {officer.username} is not assigned to case {case.case_id}'}, 
                status=status.HTTP_200_OK
            )
        
        case.assigned_officers.remove(officer)
        logger.info(f"Officer {officer.username} removed from case {case.case_id}")
        
        return Response(
            {'message': f'Officer {officer.username} removed from case {case.case_id}'}, 
            status=status.HTTP_200_OK
        )
        
    except (ValueError, TypeError):
        return Response(
            {'error': 'Invalid case ID or officer ID'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error removing officer from case: {str(e)}")
        return Response(
            {'error': 'Failed to remove officer'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['PATCH'])
@permission_classes([permissions.IsAuthenticated])
def update_case_status(request, case_id):
    """Update case status"""
    try:
        case = get_object_or_404(Case, case_id=case_id)
    except (ValueError, TypeError):
        return Response(
            {'error': 'Invalid case ID'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    new_status = request.data.get('status')
    
    # Validate status
    valid_statuses = ['open', 'investigating', 'closed']
    if not new_status or new_status not in valid_statuses:
        return Response(
            {
                'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
            }, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Update status
        old_status = case.status
        case.status = new_status
        
        # Auto-set end_date when closing a case
        if new_status == 'closed' and not case.end_date:
            case.end_date = timezone.now().date()
        # Clear end_date when reopening a case
        elif new_status != 'closed' and case.end_date:
            case.end_date = None
        
        case.save()
        logger.info(f"Case {case.case_id} status updated from {old_status} to {new_status}")
        
        serializer = CaseSerializer(case)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error updating case status: {str(e)}")
        return Response(
            {'error': 'Failed to update case status'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def case_statistics(request):
    """Get case statistics"""
    try:
        # Basic counts
        total_cases = Case.objects.count()
        open_cases = Case.objects.filter(status='open').count()
        investigating_cases = Case.objects.filter(status='investigating').count()
        closed_cases = Case.objects.filter(status='closed').count()
        
        # User-specific counts
        my_cases = Case.objects.filter(assigned_officers=request.user).count()
        my_open_cases = Case.objects.filter(
            assigned_officers=request.user, 
            status='open'
        ).count()
        my_investigating_cases = Case.objects.filter(
            assigned_officers=request.user, 
            status='investigating'
        ).count()
        
        # Priority counts
        high_priority = Case.objects.filter(priority='high').count()
        medium_priority = Case.objects.filter(priority='medium').count()
        low_priority = Case.objects.filter(priority='low').count()
        
        return Response({
            'total_cases': total_cases,
            'open_cases': open_cases,
            'investigating_cases': investigating_cases,
            'closed_cases': closed_cases,
            'my_assigned_cases': my_cases,
            'my_open_cases': my_open_cases,
            'my_investigating_cases': my_investigating_cases,
            'case_distribution': {
                'open': open_cases,
                'investigating': investigating_cases,
                'closed': closed_cases
            },
            'priority_distribution': {
                'high': high_priority,
                'medium': medium_priority,
                'low': low_priority
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting case statistics: {str(e)}")
        return Response(
            {'error': 'Failed to get statistics'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def case_by_case_id(request, case_id_str):
    """Get case by case_id string (e.g., CASE-2025-0001)"""
    try:
        case = get_object_or_404(Case, case_id=case_id_str)
        serializer = CaseSerializer(case)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting case by case_id {case_id_str}: {str(e)}")
        return Response(
            {'error': 'Case not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def bulk_update_cases(request):
    """Bulk update multiple cases"""
    case_ids = request.data.get('case_ids', [])
    update_data = request.data.get('update_data', {})
    
    if not case_ids or not update_data:
        return Response(
            {'error': 'case_ids and update_data are required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        updated_count = 0
        errors = []
        
        for case_id in case_ids:
            try:
                case = Case.objects.get(case_id=case_id)
                serializer = CaseSerializer(case, data=update_data, partial=True)
                
                if serializer.is_valid():
                    serializer.save()
                    updated_count += 1
                else:
                    errors.append({
                        'case_id': case_id,
                        'errors': serializer.errors
                    })
                    
            except (Case.DoesNotExist, ValueError, TypeError):
                errors.append({
                    'case_id': case_id,
                    'errors': 'Case not found or invalid ID'
                })
        
        return Response({
            'updated_count': updated_count,
            'errors': errors
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in bulk update: {str(e)}")
        return Response(
            {'error': 'Bulk update failed'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )