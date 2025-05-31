from django.urls import path
from .views import RegisterView, MyTokenObtainView, AdminOnlyView, PoliceOnlyView, InvestigatorOnlyView, ProfileUpdateView, ForgotPasswordView, ResetPasswordView, UserListView, UserDetailView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', MyTokenObtainView.as_view(), name='login'),
    path('admin-data/', AdminOnlyView.as_view(), name='admin-data'),
    path('police-data/', PoliceOnlyView.as_view(), name='police-data'),
    path('investigator-data/', InvestigatorOnlyView.as_view(), name='investigator-data'),
    path('update-profile/', ProfileUpdateView.as_view(), name='update-profile'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
]
