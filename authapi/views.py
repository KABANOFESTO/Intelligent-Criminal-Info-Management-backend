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
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from .serializers import RegisterSerializer, UserSerializer, ProfileUpdateSerializer
from .permissions import IsAdmin, IsPolice, IsInvestigator
import logging

logger = logging.getLogger(__name__)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


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
        
        # Try to get user by email first
        try:
            user = User.objects.get(email=email)
            # Authenticate using the username but we got user by email
            user = authenticate(username=user.username, password=password)
        except User.DoesNotExist:
            user = None
        
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

    def get_object(self):
        return self.request.user


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


class CurrentUserView(APIView):
    """Get current authenticated user details"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)