from django.urls import path
from .views import AdminUserCreateView, AdminUserDeleteView, AdminUserUpdateView, RegisterView, MyTokenObtainView, AdminOnlyView, PoliceOnlyView, InvestigatorOnlyView, ProfileUpdateView, ForgotPasswordView, ResetPasswordView, UserActivateDeactivateView, UserListView, UserDetailView, CurrentUserView

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
    path('admin/users/create/', AdminUserCreateView.as_view(), name='admin-user-create'),
    path('admin/users/<int:pk>/update/', AdminUserUpdateView.as_view(), name='admin-user-update'),
    path('admin/users/<int:pk>/delete/', AdminUserDeleteView.as_view(), name='admin-user-delete'),
    path('admin/users/<int:pk>/toggle-active/', UserActivateDeactivateView.as_view(), name='admin-user-toggle-active'),
    path('me/', CurrentUserView.as_view(), name='current-user'),
]
