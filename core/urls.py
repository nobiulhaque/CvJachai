"""
URL configuration for Resume Classifier API.
"""

from django.urls import path
from api import views as api_views

urlpatterns = [
    path('api/classify', api_views.ResumeClassifyAPIView.as_view(), name='resume_classify'),
    path('api/optimize', api_views.ResumeOptimizeAPIView.as_view(), name='resume_optimize'),
    path('api/', api_views.APIInfoAPIView.as_view(), name='api_info'),
    path('', api_views.APIInfoAPIView.as_view(), name='root'),
]
