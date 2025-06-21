from django.urls import path, include
from . import views

urlpatterns = [
    # ✅ Case CRUD operations
    path('cases/', views.CaseListCreateView.as_view(), name='case-list-create'),
    path('cases/<str:pk>/', views.CaseDetailView.as_view(), name='case-detail'),

    # ✅ Case-Officer relationships
    path('cases/<str:case_id>/officers/', views.CaseOfficersView.as_view(), name='case-officers'),
    path('officers/<int:officer_id>/cases/', views.OfficerCasesView.as_view(), name='officer-cases'),
    path('cases/<str:case_id>/assign-officer/', views.assign_officer_to_case, name='assign-officer'),
    path('cases/<str:case_id>/officers/<int:officer_id>/remove/', views.remove_officer_from_case, name='remove-officer'),

    # ✅ Case status management
    path('cases/<str:case_id>/status/', views.update_case_status, name='update-case-status'),

    # ✅ Statistics
    path('cases/statistics/', views.case_statistics, name='case-statistics'),

    # ✅ Communication module routes
    path('communication/', include('communication.urls')),
]
