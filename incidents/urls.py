from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import IncidentViewSet

router = DefaultRouter()
router.register(r'incidents', IncidentViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
