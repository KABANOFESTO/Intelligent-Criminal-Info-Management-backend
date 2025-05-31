from django.urls import path
from .views import RegisterView, MyTokenObtainView, AdminOnlyView, PoliceOnlyView, InvestigatorOnlyView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', MyTokenObtainView.as_view(), name='login'),
    path('admin-data/', AdminOnlyView.as_view(), name='admin-data'),
    path('police-data/', PoliceOnlyView.as_view(), name='police-data'),
    path('investigator-data/', InvestigatorOnlyView.as_view(), name='investigator-data'),
]
