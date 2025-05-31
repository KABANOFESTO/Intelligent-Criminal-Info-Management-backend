from django.shortcuts import render
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from .serializers import RegisterSerializer, UserSerializer
from .permissions import IsAdmin, IsPolice, IsInvestigator

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

class MyTokenObtainView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        from django.contrib.auth import authenticate
        user = authenticate(username=request.data['username'], password=request.data['password'])
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(user).data
            })
        return Response({'error': 'Invalid Credentials'}, status=401)

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

