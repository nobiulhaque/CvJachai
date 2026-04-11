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
            "version": "4.0.0 (Full Stack Release)",
            "status": "Operational (Secure Deployment Ready)",
            "authentication": "JWT Bearer Token Required",
            "architecture": "Hybrid AI Pipeline (LightGBM + Groq LLM + Local NLI Fallback)",
            "active_models": {
                "mass_classifier": "LightGBM 1.2.8",
                "semantic_judge": groq_base.ranker_model + " (Groq)",
                "fallback_judge": "Local NLI Transformer",
                "optimizer": groq_base.optimizer_model + " (Groq)"
            },
            "endpoints": {
                "POST /api/auth/signup": "Create account",
                "POST /api/auth/signin": "Login & obtain JWT tokens",
                "GET/PATCH /api/auth/profile": "Professional profile management",
                "POST /api/token/refresh/": "Fetch new access tokens",
                "POST /api/classify": "Massive resume ranking (Hybrid LightGBM/LLM)",
                "POST /api/optimize": "AI-powered ATS Resume Rewrite",
                "ADMIN /admin/": "Django Admin Control Center",
                "DASHBOARD /admin/index.html": "Premium Admin Frontend UI"
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
                "Hybrid Scoring: Combines local ML speed with LLM precision",
                "Resilient Architecture: Automatic local NLI fallback if API is down",
                "Advanced OCR: Multi-threaded text extraction from images and docs",
                "Admin Suite: Premium glassmorphism dashboard and enhanced Django admin",
                "SEO Optimized: Semantic HTML structure and performance tuned"
            ]
        }
        
        return Response(response_data, status=HTTP_200_OK)
