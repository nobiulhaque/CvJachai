"""
URL configuration for Resume Classifier API.
"""

import os
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.http import FileResponse, Http404
from django.views.generic import TemplateView
from api import views as api_views

from rest_framework_simplejwt.views import TokenRefreshView


def serve_media_file(request, path):
    """Production-safe media file serving view."""
    file_path = os.path.join(settings.MEDIA_ROOT, path)
    if not os.path.exists(file_path):
        raise Http404("File not found")
    return FileResponse(open(file_path, 'rb'), as_attachment=True)

api_patterns = [
    path('auth/signup', api_views.RegisterView.as_view(), name='auth_signup'),
    path('auth/signin', api_views.LoginView.as_view(), name='auth_signin'),
    path('auth/google', api_views.GoogleLoginView.as_view(), name='auth_google'),
    path('auth/otp/request/', api_views.ForgotPasswordView.as_view(), name='otp_request'),
    path('auth/reset-password/', api_views.ResetPasswordView.as_view(), name='reset_password'),
    path('auth/profile', api_views.ProfileDetailAPIView.as_view(), name='auth_profile'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('classify', api_views.ResumeClassifyAPIView.as_view(), name='resume_classify'),
    path('optimize', api_views.ResumeOptimizeAPIView.as_view(), name='resume_optimize'),
    
    # --- Job Portal Endpoints ---
    path('jobs/', api_views.JobCreateListView.as_view(), name='job_list_create'),
    path('jobs/my/', api_views.MyJobsView.as_view(), name='my_jobs'),
    path('jobs/apply/', api_views.ApplyJobView.as_view(), name='job_apply'),
    path('jobs/<str:job_id>/applications/', api_views.JobApplicationsListView.as_view(), name='job_applications'),
    path('jobs/<str:job_id>/analyze/', api_views.AnalyzeJobApplicantsView.as_view(), name='job_analyze'),
    path('jobs/<str:job_id>/delete/', api_views.JobDeleteView.as_view(), name='job_delete'),
    # ----------------------------
    path('media/<path:path>', serve_media_file, name='media_serve'),
    path('', api_views.APIInfoAPIView.as_view(), name='api_info'),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('dashboard/', TemplateView.as_view(template_name='index.html'), name='dashboard'),
    path('media/<path:path>', serve_media_file, name='media_serve_root'),
    
    # Include API patterns both with and without 'api/' prefix to support
    # both local development and cPanel Phusion Passenger (which strips /api)
    path('api/', include(api_patterns)),
    path('', include(api_patterns)),
]
