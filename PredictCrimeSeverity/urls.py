from django.urls import path
from .views import PredictCrimeSeverity, CrimePredictionListView, CrimePredictionDetailView

urlpatterns = [
    # Main prediction endpoint (POST for prediction, GET for list)
    path('predict/', PredictCrimeSeverity.as_view(), name='predict-crime'),
    
    # Alternative URLs for better REST API structure
    path('predictions/', PredictCrimeSeverity.as_view(), name='crime-predictions-list'),
    
    # Individual prediction detail (optional - for retrieving specific prediction)
    path('predictions/<int:pk>/', CrimePredictionDetailView.as_view(), name='crime-prediction-detail'),
    
    # Statistics endpoint (optional)
    path('predictions/stats/', CrimePredictionListView.as_view(), name='crime-predictions-stats'),
]