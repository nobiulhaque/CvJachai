"""
URL configuration for Resume Classifier API.
"""

import os
from django.contrib import admin
from django.urls import path
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

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/signup', api_views.RegisterView.as_view(), name='auth_signup'),
    path('api/auth/signin', api_views.LoginView.as_view(), name='auth_signin'),
    path('api/auth/google', api_views.GoogleLoginView.as_view(), name='auth_google'),
    path('api/auth/otp/request/', api_views.ForgotPasswordView.as_view(), name='otp_request'),
    path('api/auth/reset-password/', api_views.ResetPasswordView.as_view(), name='reset_password'),
    path('api/auth/profile', api_views.ProfileDetailAPIView.as_view(), name='auth_profile'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/classify', api_views.ResumeClassifyAPIView.as_view(), name='resume_classify'),
    path('api/optimize', api_views.ResumeOptimizeAPIView.as_view(), name='resume_optimize'),
    
    # --- Job Portal Endpoints ---
    path('api/jobs/', api_views.JobCreateListView.as_view(), name='job_list_create'),
    path('api/jobs/my/', api_views.MyJobsView.as_view(), name='my_jobs'),
    path('api/jobs/apply/', api_views.ApplyJobView.as_view(), name='job_apply'),
    path('api/jobs/<str:job_id>/applications/', api_views.JobApplicationsListView.as_view(), name='job_applications'),
    path('api/jobs/<str:job_id>/analyze/', api_views.AnalyzeJobApplicantsView.as_view(), name='job_analyze'),
    path('api/jobs/<str:job_id>/delete/', api_views.JobDeleteView.as_view(), name='job_delete'),
    # ----------------------------

    path('dashboard/', TemplateView.as_view(template_name='index.html'), name='dashboard'),
    path('api/', api_views.APIInfoAPIView.as_view(), name='api_info'),
    path('', api_views.APIInfoAPIView.as_view(), name='root'),
    path('media/<path:path>', serve_media_file, name='media_serve'),
]
