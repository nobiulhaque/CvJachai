from .classify_view import ResumeClassifyAPIView
from .info_view import APIInfoAPIView
from .optimize_view import ResumeOptimizeAPIView
from .auth_views import RegisterView, LoginView
from .profile_view import ProfileDetailAPIView

__all__ = ['ResumeClassifyAPIView', 'APIInfoAPIView', 'ResumeOptimizeAPIView', 'RegisterView', 'LoginView', 'ProfileDetailAPIView']
