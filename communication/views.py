from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count, Max, Case as DjangoCase, When, Value, IntegerField
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import CommunicationLog, Case
from .serializers import (
    CommunicationLogSerializer, 
    CommunicationLogCreateSerializer,
    MessageReadSerializer,
    ConversationSerializer,
    UserBasicSerializer
)
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class CommunicationLogViewSet(viewsets.ModelViewSet):
    queryset = CommunicationLog.objects.select_related('sender', 'receiver', 'related_case').all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CommunicationLogCreateSerializer
        return CommunicationLogSerializer
    
    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        
        # Filter messages where user is sender or receiver
        queryset = queryset.filter(
            Q(sender=user) | Q(receiver=user)
        )
        
        # Filter by conversation partner
        with_user = self.request.query_params.get('with_user')
        if with_user:
            try:
                partner = User.objects.get(id=with_user)
                queryset = queryset.filter(
                    (Q(sender=user) & Q(receiver=partner)) |
                    (Q(sender=partner) & Q(receiver=user))
                )
            except User.DoesNotExist:
                queryset = queryset.none()
        
        # Filter by case
        case_id = self.request.query_params.get('case')
        if case_id:
            queryset = queryset.filter(related_case_id=case_id)
        
        # Filter by message type
        message_type = self.request.query_params.get('message_type')
        if message_type:
            queryset = queryset.filter(message_type=message_type)
        
        # Filter by priority
        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        # Filter by read status
        is_read = self.request.query_params.get('is_read')
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == 'true')
        
        # Only show unread messages received by user
        unread_only = self.request.query_params.get('unread_only')
        if unread_only and unread_only.lower() == 'true':
            queryset = queryset.filter(receiver=user, is_read=False)
        
        return queryset
    
    def perform_create(self, serializer):
        communication_log = serializer.save()
        logger.info(f"Communication log created: {communication_log}")
    
    @action(detail=False, methods=['get'])
    def sent(self, request):
        """Get messages sent by current user"""
        sent_messages = self.get_queryset().filter(sender=request.user)
        page = self.paginate_queryset(sent_messages)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(sent_messages, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def received(self, request):
        """Get messages received by current user"""
        received_messages = self.get_queryset().filter(receiver=request.user)
        page = self.paginate_queryset(received_messages)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(received_messages, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Get unread messages for current user"""
        unread_messages = self.get_queryset().filter(
            receiver=request.user, 
            is_read=False
        )
        serializer = self.get_serializer(unread_messages, many=True)
        return Response({
            'count': unread_messages.count(),
            'messages': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a specific message as read"""
        message = self.get_object()
        
        # Only receiver can mark message as read
        if message.receiver != request.user:
            return Response(
                {'error': 'You can only mark messages you received as read.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not message.is_read:
            message.mark_as_read()
            return Response({'message': 'Message marked as read.'})
        
        return Response({'message': 'Message was already read.'})
    
    @action(detail=False, methods=['post'])
    def mark_multiple_read(self, request):
        """Mark multiple messages as read"""
        serializer = MessageReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        message_ids = serializer.validated_data['message_ids']
        messages = self.get_queryset().filter(
            id__in=message_ids,
            receiver=request.user,
            is_read=False
        )
        
        updated_count = 0
        for message in messages:
            message.mark_as_read()
            updated_count += 1
        
        return Response({
            'message': f'{updated_count} message(s) marked as read.',
            'updated_count': updated_count
        })
    
    @action(detail=False, methods=['get'])
    def conversations(self, request):
        """Get conversation threads with other users"""
        user = request.user
        
        # Get all users who have communicated with current user
        conversations = []
        
        # Find all unique conversation partners
        partners_sent = User.objects.filter(
            received_logs__sender=user
        ).distinct()
        
        partners_received = User.objects.filter(
            sent_logs__receiver=user
        ).distinct()
        
        all_partners = (partners_sent | partners_received).distinct()
        
        for partner in all_partners:
            # Get last message in conversation
            last_message = CommunicationLog.objects.filter(
                (Q(sender=user) & Q(receiver=partner)) |
                (Q(sender=partner) & Q(receiver=user))
            ).first()
            
            # Count unread messages from this partner
            unread_count = CommunicationLog.objects.filter(
                sender=partner,
                receiver=user,
                is_read=False
            ).count()
            
            if last_message:
                conversations.append({
                    'participant': partner,
                    'last_message': last_message,
                    'unread_count': unread_count,
                    'last_activity': last_message.timestamp
                })
        
        # Sort by last activity
        conversations.sort(key=lambda x: x['last_activity'], reverse=True)
        
        serializer = ConversationSerializer(conversations, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get communication statistics for current user"""
        user = request.user
        
        total_sent = CommunicationLog.objects.filter(sender=user).count()
        total_received = CommunicationLog.objects.filter(receiver=user).count()
        unread_count = CommunicationLog.objects.filter(
            receiver=user, 
            is_read=False
        ).count()
        
        # Priority breakdown for received messages
        priority_stats = CommunicationLog.objects.filter(
            receiver=user
        ).values('priority').annotate(count=Count('id'))
        
        # Message type breakdown
        type_stats = CommunicationLog.objects.filter(
            Q(sender=user) | Q(receiver=user)
        ).values('message_type').annotate(count=Count('id'))
        
        return Response({
            'total_sent': total_sent,
            'total_received': total_received,
            'unread_count': unread_count,
            'priority_breakdown': list(priority_stats),
            'type_breakdown': list(type_stats)
        })
    
    @action(detail=False, methods=['get'])
    def users(self, request):
        """Get list of users for messaging"""
        users = User.objects.exclude(id=request.user.id).filter(is_active=True)
        
        # Search functionality
        search = request.query_params.get('search')
        if search:
            users = users.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )
        
        serializer = UserBasicSerializer(users, many=True)
        return Response(serializer.data)