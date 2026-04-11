"""
URL configuration for Resume Classifier API.
"""

from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from api import views as api_views

from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/signup', api_views.RegisterView.as_view(), name='auth_signup'),
    path('api/auth/signin', api_views.LoginView.as_view(), name='auth_signin'),
    path('api/auth/profile', api_views.ProfileDetailAPIView.as_view(), name='auth_profile'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/classify', api_views.ResumeClassifyAPIView.as_view(), name='resume_classify'),
    path('api/optimize', api_views.ResumeOptimizeAPIView.as_view(), name='resume_optimize'),
    path('dashboard/', TemplateView.as_view(template_name='index.html'), name='dashboard'),
    path('api/', api_views.APIInfoAPIView.as_view(), name='api_info'),
    path('', api_views.APIInfoAPIView.as_view(), name='root'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
