"""
URL configuration for Resume Classifier API.
"""

from django.urls import path
from views import (
    ResumeClassifyAPIView,
    HealthCheckAPIView,
    APIInfoAPIView,
    CategoriesAPIView
)

urlpatterns = [
    path('api/classify', ResumeClassifyAPIView.as_view(), name='classify-resumes'),
    path('api/health', HealthCheckAPIView.as_view(), name='health-check'),
    path('api/categories', CategoriesAPIView.as_view(), name='categories'),
    path('api/', APIInfoAPIView.as_view(), name='api-info'),
    path('', APIInfoAPIView.as_view(), name='root'),
]
