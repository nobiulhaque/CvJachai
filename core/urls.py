"""
URL configuration for Resume Classifier API.
"""

from django.urls import path
from api.views import (
    ResumeClassifyAPIView,
    APIInfoAPIView
)

urlpatterns = [
    path('api/classify', ResumeClassifyAPIView.as_view(), name='classify-resumes'),
    path('api/', APIInfoAPIView.as_view(), name='api-info'),
    path('', APIInfoAPIView.as_view(), name='root'),
]
