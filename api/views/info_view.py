from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from rest_framework.permissions import AllowAny
from engine.groq import groq_base

class APIInfoAPIView(APIView):
    """API information endpoint."""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Return API information."""
        
        response_data = {
            "name": "CvJachai Resume Intelligence Engine",
            "version": "5.0.0 (Cloud-Native AI Release)",
            "status": "Operational",
            "authentication": "JWT Bearer Token Required",
            "architecture": "Cloud-Native AI Pipeline (Groq GPT-OSS 120B + Llama 4 Scout Vision)",
            "active_models": {
                "text_classifier": groq_base.ranker_model + " (Groq)",
                "optimizer": groq_base.optimizer_model + " (Groq)",
                "vision_ocr": groq_base.vision_model + " (Groq Vision)",
            },
            "endpoints": {
                "POST /api/auth/signup": "Create account",
                "POST /api/auth/signin": "Login & obtain JWT tokens",
                "GET/PATCH /api/auth/profile": "Professional profile management",
                "POST /api/token/refresh/": "Fetch new access tokens",
                "POST /api/classify": "Massive resume ranking (Groq AI)",
                "POST /api/optimize": "AI-powered ATS Resume Rewrite",
                "GET /dashboard/": "Premium Admin Intelligence Dashboard"
            },
            "security": {
                "protocol": "JWT + DRF Throttling",
                "environment": "Fully secured via environment variables",
                "password_policy": "Strict (8+ chars, complex validation)",
                "rate_limit": "20/hr (Anon), 100/hr (User)"
            },
            "supported_formats": ["PDF", "DOCX", "TXT", "ZIP", "PNG", "JPG", "JPEG"],
            "features": [
                "Massive Scale: Processes 1000+ resumes per batch",
                "Cloud-Native: Powered entirely by Groq's ultra-fast AI inference",
                "Vision AI: Llama 4 Scout reads resume images directly (no local OCR)",
                "Auto Model Discovery: Always uses the best available Groq model",
                "Premium Dashboard: Glassmorphism UI at /dashboard/",
                "Zero Heavy Dependencies: Lightweight deployment on free-tier cloud",
            ]
        }
        
        return Response(response_data, status=HTTP_200_OK)
