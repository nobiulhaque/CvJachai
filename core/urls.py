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
    path('api/auth/password-reset', api_views.ForgotPasswordView.as_view(), name='password_reset'),
    path('api/auth/reset-password', api_views.ResetPasswordView.as_view(), name='reset_password'),
    path('api/auth/profile', api_views.ProfileDetailAPIView.as_view(), name='auth_profile'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/classify', api_views.ResumeClassifyAPIView.as_view(), name='resume_classify'),
    path('api/optimize', api_views.ResumeOptimizeAPIView.as_view(), name='resume_optimize'),
    path('dashboard/', TemplateView.as_view(template_name='index.html'), name='dashboard'),
    path('api/', api_views.APIInfoAPIView.as_view(), name='api_info'),
    path('', api_views.APIInfoAPIView.as_view(), name='root'),
    path('media/<path:path>', serve_media_file, name='media_serve'),
]
