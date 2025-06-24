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
from .serializers import RegisterSerializer, UserSerializer, ProfileUpdateSerializer,AdminUserCreateSerializer
from .permissions import IsAdmin, IsPolice, IsInvestigator
import logging

logger = logging.getLogger(__name__)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

class AdminUserCreateView(generics.CreateAPIView):
    serializer_class = AdminUserCreateSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Send email with credentials
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
            # Return response but indicate email wasn't sent
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
        
        # Authenticate using email as username since USERNAME_FIELD is now email
        user = authenticate(username=email, password=password)
        
        if user:
            if user.is_active:
                refresh = RefreshToken.for_user(user)
                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'user': UserSerializer(user).data
                }, status=status.HTTP_200_OK)
            else:
                return Response(
                    {'error': 'Account is deactivated'}, 
                    status=status.HTTP_401_UNAUTHORIZED
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

    def put(self, request, *args, **kwargs):
        """Handle PUT requests for profile updates including profile picture"""
        return super().put(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        """Handle PATCH requests for partial profile updates including profile picture"""
        return super().patch(request, *args, **kwargs)


class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        email = request.data.get("email")
        
        # Validate email presence
        if not email:
            return Response(
                {"error": "Email is required."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email=email)
            
            # Generate UID and token
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            
            # Use settings for frontend URL
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
            reset_link = f"{frontend_url}/reset-password/{uid}/{token}"
            
            # Send email with proper error handling
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
                return Response(
                    {"error": "Failed to send email. Please try again later."}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            return Response(
                {"message": "If an account with this email exists, a password reset link has been sent."}, 
                status=status.HTTP_200_OK
            )
            
        except User.DoesNotExist:
            # Don't reveal if user exists or not for security
            logger.warning(f"Password reset attempted for non-existent email: {email}")
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
                
                logger.info(f"Password successfully reset for user {user.email}")
                return Response(
                    {"message": "Password has been reset successfully."}, 
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"error": "Invalid or expired reset link."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
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
    permission_classes = [permissions.IsAuthenticated, IsAdmin]


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin view to get, update, or delete a specific user"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

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
        original_data = {
            'email': instance.email,
            'role': instance.role,
            'is_active': instance.is_active
        }
        
        self.perform_update(serializer)
        
        # Log what was changed
        updated_user = serializer.instance
        changes = []
        if original_data['email'] != updated_user.email:
            changes.append(f"email: {original_data['email']} -> {updated_user.email}")
        if original_data['role'] != updated_user.role:
            changes.append(f"role: {original_data['role']} -> {updated_user.role}")
        if original_data['is_active'] != updated_user.is_active:
            changes.append(f"is_active: {original_data['is_active']} -> {updated_user.is_active}")
        
        if changes:
            logger.info(f"User {updated_user.email} updated by admin {request.user.email}. Changes: {', '.join(changes)}")
        
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
        deleted_user_email = instance.email
        deleted_user_id = instance.id
        
        self.perform_destroy(instance)
        
        logger.warning(f"User {deleted_user_email} (ID: {deleted_user_id}) successfully deleted by admin {request.user.email}")
        
        return Response(
            {"message": f"User {deleted_user_email} has been successfully deleted."}, 
            status=status.HTTP_204_NO_CONTENT
        )


class AdminUserUpdateView(generics.UpdateAPIView):
    """Dedicated view for admin user updates"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    
    def update(self, request, *args, **kwargs):
        """Handle user updates with validation and logging"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Prevent admin from updating their own account through admin endpoints
        if instance == request.user:
            return Response(
                {"error": "Cannot update your own account through admin endpoints. Use profile update instead."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Log the update attempt
        logger.info(f"Admin {request.user.email} updating user {instance.email}")
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        self.perform_update(serializer)
        
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
        
        # Prevent admin from deleting their own account
        if instance == request.user:
            return Response(
                {"error": "Cannot delete your own account."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if this is the last admin (optional safeguard)
        if instance.role == 'admin':
            admin_count = User.objects.filter(role='admin', is_active=True).count()
            if admin_count <= 1:
                return Response(
                    {"error": "Cannot delete the last active admin account."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Log the deletion
        logger.warning(f"Admin {request.user.email} is deleting user {instance.email} (ID: {instance.id})")
        
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
        
        # Log initial state
        logger.info(f"Before toggle - User {user.email} status: {user.status}, is_active: {user.is_active}")
        
        # Prevent admin from deactivating their own account
        if user == request.user:
            return Response(
                {"error": "Cannot deactivate your own account."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if this is the last admin being deactivated
        if user.role == 'Admin' and user.status == 'Active':
            active_admin_count = User.objects.filter(role='Admin', status='Active').count()
            if active_admin_count <= 1:
                return Response(
                    {"error": "Cannot deactivate the last active admin account."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Store original status for logging
        original_status = user.status
        
        # Use the model methods to toggle status (this keeps both fields in sync)
        if user.status == 'Active':
            user.deactivate()
            action = "deactivated"
        else:
            user.activate()
            action = "activated"
        
        # Refresh from database to get updated values
        user.refresh_from_db()
        
        # Log the change
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