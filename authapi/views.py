from django.shortcuts import render
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.conf import settings
from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from .serializers import RegisterSerializer, UserSerializer, ProfileUpdateSerializer, AdminUserCreateSerializer
from .permissions import IsAdmin, IsAdminOrInvestigator, IsAdminOrInvestigatorOrPolice, IsPolice, IsInvestigator
from AuditLog.audit_log_utils import log_action 
import logging

logger = logging.getLogger(__name__)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        log_action(
            self.request,
            'USER_CREATE',
            target_user=user,
            additional_data={'registration_method': 'self_registration'}
        )
        logger.info(f"New user self-registered: {user.email}")


class AdminUserCreateView(generics.CreateAPIView):
    serializer_class = AdminUserCreateSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Log user creation by admin
        log_action(
            request,
            'USER_CREATE',
            target_user=user,
            additional_data={
                'registration_method': 'admin_created',
                'created_by': request.user.email,
                'role': user.role,
                'temporary_password_sent': True
            }
        )
        
        try:
            frontend_login_url = getattr(settings, 'FRONTEND_LOGIN_URL', 'http://localhost:3000/login')
            
            send_mail(
                subject="Your Account Has Been Created",
                message=f"Hello {user.username},\n\n"
                       f"An administrator has created an account for you with the following details:\n\n"
                       f"Username: {user.username}\n"
                       f"Email: {user.email}\n"
                       f"Temporary Password: {user.temporary_password}\n"
                       f"Role: {user.get_role_display()}\n\n"
                       f"Please log in at {frontend_login_url} and change your password immediately.\n\n"
                       f"If you didn't expect this email, please contact your system administrator.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            logger.info(f"User creation email sent to {user.email}")
            
        except Exception as e:
            logger.error(f"Failed to send user creation email to {user.email}: {str(e)}")
            
            # Log email failure
            log_action(
                request,
                'EMAIL_SEND_FAILURE',
                target_user=user,
                additional_data={
                    'email_type': 'user_creation',
                    'error': str(e)
                }
            )
           
            headers = self.get_success_headers(serializer.data)
            return Response(
                {
                    "message": "User created successfully but failed to send email.",
                    "user_id": user.id,
                    "email": user.email
                },
                status=status.HTTP_201_CREATED,
                headers=headers
            )
            
        headers = self.get_success_headers(serializer.data)
        return Response(
            {"message": "User created successfully. Email with credentials sent."},
            status=status.HTTP_201_CREATED,
            headers=headers
        )


class MyTokenObtainView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not email or not password:
            return Response(
                {'error': 'Email and password are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = authenticate(username=email, password=password)
        
        if user:
            if user.is_active:
                refresh = RefreshToken.for_user(user)
                
                # Log successful login
                log_action(
                    request,
                    'LOGIN',
                    target_user=user,
                    additional_data={'login_method': 'email_password'}
                )
                
                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'user': UserSerializer(user).data
                }, status=status.HTTP_200_OK)
            else:
                # Log failed login due to inactive account
                log_action(
                    request,
                    'LOGIN',
                    target_user=user,
                    additional_data={'status': 'failed', 'reason': 'account_deactivated'}
                )
                return Response(
                    {'error': 'Account is deactivated'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
        
        # Log failed login with invalid credentials
        log_action(
            request,
            'LOGIN',
            additional_data={
                'status': 'failed', 
                'reason': 'invalid_credentials',
                'attempted_email': email
            }
        )
        return Response(
            {'error': 'Invalid credentials'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )


class AdminOnlyView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request):
        return Response({'message': 'Hello Admin'})


class PoliceOnlyView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsPolice]

    def get(self, request):
        return Response({'message': 'Hello Police'})


class InvestigatorOnlyView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsInvestigator]

    def get(self, request):
        return Response({'message': 'Hello Investigator'})


class ProfileUpdateView(generics.UpdateAPIView):
    serializer_class = ProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]  

    def get_object(self):
        return self.request.user

    def _get_changed_fields(self, old_data, new_data):
        """Helper to identify changed fields"""
        changed = {}
        for key in old_data:
            if old_data[key] != new_data.get(key):
                changed[key] = {
                    'old': old_data[key],
                    'new': new_data.get(key)
                }
        return changed

    def put(self, request, *args, **kwargs):
        """Handle PUT requests for profile updates including profile picture"""
        old_data = ProfileUpdateSerializer(self.get_object()).data
        response = super().put(request, *args, **kwargs)
        
        log_action(
            request,
            'PROFILE_UPDATE',
            target_user=request.user,
            additional_data={
                'action_type': 'full_update',
                'changes': self._get_changed_fields(old_data, response.data)
            }
        )
        
        return response

    def patch(self, request, *args, **kwargs):
        """Handle PATCH requests for partial profile updates including profile picture"""
        old_data = ProfileUpdateSerializer(self.get_object()).data
        response = super().patch(request, *args, **kwargs)
        
        log_action(
            request,
            'PROFILE_UPDATE',
            target_user=request.user,
            additional_data={
                'action_type': 'partial_update',
                'changes': self._get_changed_fields(old_data, response.data)
            }
        )
        
        return response


class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        email = request.data.get("email")
        
        if not email:
            return Response(
                {"error": "Email is required."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email=email)
            
            # Log password reset request
            log_action(
                request,
                'PASSWORD_RESET_REQUEST',
                target_user=user
            )
            
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            

            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
            reset_link = f"{frontend_url}/reset-password/{uid}/{token}"
            
            try:
                send_mail(
                    subject="Password Reset Request",
                    message=f"Hello {user.first_name or user.username},\n\n"
                           f"You requested a password reset. Click the link below to reset your password:\n"
                           f"{reset_link}\n\n"
                           f"This link will expire in 24 hours.\n\n"
                           f"If you didn't request this, please ignore this email.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                logger.info(f"Password reset email sent to {email}")
                
            except Exception as e:
                logger.error(f"Failed to send password reset email to {email}: {str(e)}")
                
                # Log email failure
                log_action(
                    request,
                    'EMAIL_SEND_FAILURE',
                    target_user=user,
                    additional_data={
                        'email_type': 'password_reset',
                        'error': str(e)
                    }
                )
                
                return Response(
                    {"error": "Failed to send email. Please try again later."}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            return Response(
                {"message": "If an account with this email exists, a password reset link has been sent."}, 
                status=status.HTTP_200_OK
            )
            
        except User.DoesNotExist:
            # Log failed password reset attempt
            logger.warning(f"Password reset attempted for non-existent email: {email}")
            log_action(
                request,
                'PASSWORD_RESET_REQUEST',
                additional_data={
                    'status': 'failed',
                    'reason': 'user_not_found',
                    'attempted_email': email
                }
            )
            return Response(
                {"message": "If an account with this email exists, a password reset link has been sent."}, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Unexpected error in password reset for {email}: {str(e)}")
            return Response(
                {"error": "An unexpected error occurred. Please try again later."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        uid = request.data.get("uid")
        token = request.data.get("token")
        new_password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password")
        
        if not all([uid, token, new_password]):
            return Response(
                {"error": "UID, token, and new password are required."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if confirm_password and new_password != confirm_password:
            return Response(
                {"error": "Passwords do not match."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(new_password) < 8:
            return Response(
                {"error": "Password must be at least 8 characters long."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Decode the user ID
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
            
            # Verify the token
            if default_token_generator.check_token(user, token):
                # Set new password
                user.set_password(new_password)
                user.save()
                
                # Log successful password reset
                log_action(
                    request,
                    'PASSWORD_RESET_COMPLETE',
                    target_user=user
                )
                
                logger.info(f"Password successfully reset for user {user.email}")
                return Response(
                    {"message": "Password has been reset successfully."}, 
                    status=status.HTTP_200_OK
                )
            else:
                # Log failed password reset due to invalid token
                log_action(
                    request,
                    'PASSWORD_RESET_COMPLETE',
                    target_user=user,
                    additional_data={'status': 'failed', 'reason': 'invalid_token'}
                )
                return Response(
                    {"error": "Invalid or expired reset link."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            # Log failed password reset due to invalid link
            log_action(
                request,
                'PASSWORD_RESET_COMPLETE',
                additional_data={'status': 'failed', 'reason': 'invalid_reset_link'}
            )
            return Response(
                {"error": "Invalid reset link."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unexpected error in password reset: {str(e)}")
            return Response(
                {"error": "An unexpected error occurred."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserListView(generics.ListAPIView):
    """Admin view to list all users"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminOrInvestigatorOrPolice]

    def get(self, request, *args, **kwargs):
        # Log user list access
        log_action(
            request,
            'USER_LIST_ACCESS',
            additional_data={'accessed_by_role': request.user.role}
        )
        return super().get(request, *args, **kwargs)


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin view to get, update, or delete a specific user"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminOrInvestigator]

    def _get_changed_fields(self, old_data, new_data):
        """Helper to identify changed fields"""
        changed = {}
        for key in old_data:
            if old_data[key] != new_data.get(key):
                changed[key] = {
                    'old': old_data[key],
                    'new': new_data.get(key)
                }
        return changed

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Log user detail access
        log_action(
            request,
            'USER_DETAIL_ACCESS',
            target_user=instance,
            additional_data={'accessed_by': request.user.email}
        )
        
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """Handle user updates with proper logging"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Log the update attempt
        logger.info(f"Admin {request.user.email} attempting to update user {instance.email}")
        
        # Prevent admin from updating their own account through this endpoint
        if instance == request.user:
            return Response(
                {"error": "Cannot update your own account through this endpoint. Use profile update instead."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        # Store original data for logging
        original_data = UserSerializer(instance).data
        
        self.perform_update(serializer)
        
        # Log what was changed
        updated_user = serializer.instance
        changes = self._get_changed_fields(original_data, serializer.data)
        
        log_action(
            request,
            'USER_UPDATE',
            target_user=updated_user,
            additional_data={
                'old_data': original_data,
                'new_data': serializer.data,
                'changed_fields': changes,
                'update_type': 'partial' if partial else 'full'
            }
        )
        
        if changes:
            change_summary = ', '.join([f"{k}: {v['old']} -> {v['new']}" for k, v in changes.items()])
            logger.info(f"User {updated_user.email} updated by admin {request.user.email}. Changes: {change_summary}")
        
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """Handle user deletion with proper logging and safeguards"""
        instance = self.get_object()
        
        # Prevent admin from deleting their own account
        if instance == request.user:
            return Response(
                {"error": "Cannot delete your own account."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Log the deletion attempt
        logger.warning(f"Admin {request.user.email} is deleting user {instance.email} (ID: {instance.id})")
        
        # Store user info before deletion for logging
        user_data = UserSerializer(instance).data
        
        # Log the deletion
        log_action(
            request,
            'USER_DELETE',
            target_user=instance,
            additional_data={'user_data': user_data}
        )
        
        self.perform_destroy(instance)
        
        logger.warning(f"User {user_data['email']} (ID: {user_data['id']}) successfully deleted by admin {request.user.email}")
        
        return Response(
            {"message": f"User {user_data['email']} has been successfully deleted."}, 
            status=status.HTTP_204_NO_CONTENT
        )


class AdminUserUpdateView(generics.UpdateAPIView):
    """Dedicated view for admin user updates"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    
    def _get_changed_fields(self, old_data, new_data):
        """Helper to identify changed fields"""
        changed = {}
        for key in old_data:
            if old_data[key] != new_data.get(key):
                changed[key] = {
                    'old': old_data[key],
                    'new': new_data.get(key)
                }
        return changed
    
    def update(self, request, *args, **kwargs):
        """Handle user updates with validation and logging"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
       
        if instance == request.user:
            return Response(
                {"error": "Cannot update your own account through admin endpoints. Use profile update instead."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logger.info(f"Admin {request.user.email} updating user {instance.email}")
        
        # Capture old data for logging
        old_data = UserSerializer(instance).data
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        self.perform_update(serializer)
        
        # Log the update
        changes = self._get_changed_fields(old_data, serializer.data)
        log_action(
            request,
            'USER_UPDATE',
            target_user=instance,
            additional_data={
                'old_data': old_data,
                'new_data': serializer.data,
                'changed_fields': changes,
                'update_type': 'partial' if partial else 'full'
            }
        )
        
        logger.info(f"User {instance.email} successfully updated by admin {request.user.email}")
        
        return Response({
            "message": "User updated successfully.",
            "user": serializer.data
        })


class AdminUserDeleteView(generics.DestroyAPIView):
    """Dedicated view for admin user deletion"""
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    
    def destroy(self, request, *args, **kwargs):
        """Handle user deletion with proper safeguards"""
        instance = self.get_object()
        
        if instance == request.user:
            return Response(
                {"error": "Cannot delete your own account."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if instance.role == 'admin':
            admin_count = User.objects.filter(role='admin', is_active=True).count()
            if admin_count <= 1:
                return Response(
                    {"error": "Cannot delete the last active admin account."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        logger.warning(f"Admin {request.user.email} is deleting user {instance.email} (ID: {instance.id})")
        
        # Store user data for logging
        user_data = UserSerializer(instance).data
        
        # Log the deletion
        log_action(
            request,
            'USER_DELETE',
            target_user=instance,
            additional_data={'user_data': user_data}
        )
        
        deleted_user_email = instance.email
        self.perform_destroy(instance)
        
        logger.warning(f"User {deleted_user_email} successfully deleted by admin {request.user.email}")
        
        return Response(
            {"message": f"User {deleted_user_email} has been successfully deleted."}, 
            status=status.HTTP_200_OK
        )


class UserActivateDeactivateView(APIView):
    """Admin view to activate/deactivate users"""
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    
    def patch(self, request, pk):
        """Toggle user active status"""
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        logger.info(f"Before toggle - User {user.email} status: {user.status}, is_active: {user.is_active}")
        
        if user == request.user:
            return Response(
                {"error": "Cannot deactivate your own account."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if user.role == 'Admin' and user.status == 'Active':
            active_admin_count = User.objects.filter(role='Admin', status='Active').count()
            if active_admin_count <= 1:
                return Response(
                    {"error": "Cannot deactivate the last active admin account."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Store original status for logging
        original_status = user.status
        original_is_active = user.is_active
        
        if user.status == 'Active':
            user.deactivate()
            action = "deactivated"
            audit_action = 'USER_DEACTIVATE'
        else:
            user.activate()
            action = "activated"
            audit_action = 'USER_ACTIVATE'
        
        user.refresh_from_db()
        
        # Log the activation/deactivation
        log_action(
            request,
            audit_action,
            target_user=user,
            additional_data={
                'previous_status': original_status,
                'new_status': user.status,
                'previous_is_active': original_is_active,
                'new_is_active': user.is_active
            }
        )
        
        logger.info(f"User {user.email} {action} by admin {request.user.email}")
        logger.info(f"After toggle - User {user.email} status: {user.status}, is_active: {user.is_active}")
        
        return Response({
            "message": f"User {user.email} has been {action}.",
            "user": UserSerializer(user).data,
            "previous_status": original_status,
            "new_status": user.status
        })


class CurrentUserView(APIView):
    """Get current authenticated user details"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)