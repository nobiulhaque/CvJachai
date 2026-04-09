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
            "version": "3.2.0",
            "status": "Operational (Production Secure)",
            "authentication": "JWT Bearer Token Required",
            "architecture": "Modular Hybrid AI (Groq Cloud + Local OCR)",
            "active_models": {
                "ranker": groq_base.ranker_model,
                "optimizer": groq_base.optimizer_model
            },
            "endpoints": {
                "POST /api/auth/signup": "Create account (Email, Password 8+ chars)",
                "POST /api/auth/signin": "Login & get Profile + Tokens",
                "GET/PATCH /api/auth/profile": "View/Update professional details",
                "POST /api/token/refresh/": "Refresh expired access token",
                "POST /api/classify": "Rank massive resume batches (400+)",
                "POST /api/optimize": "ATS Resume Rewrite powered by Llama 70B",
                "GET /api/": "View this documentation"
            },
            "security": {
                "secret_key": "Environment-secured (via .env)",
                "debug_mode": "Environment-controlled",
                "password_policy": "Min 8 chars, no common passwords, Django validators",
                "duplicate_email": "Blocked at registration",
                "rate_limit_anonymous": "20 requests/hour",
                "rate_limit_authenticated": "100 requests/hour"
            },
            "supported_formats": ["PDF", "DOCX", "TXT", "ZIP", "PNG", "JPG", "JPEG"],
            "features": [
                "Deterministic AI Ranking (Temp 0.0)",
                "Bulk 1000+ Resume Batch Support",
                "Multi-threaded OCR Extraction",
                "Auto-Model Discovery (Always latest Llama)",
                "Professional ATS Resume Optimizer",
                "Email-based JWT Authentication",
                "User Profile Management",
                "DRF Rate Limiting & Throttling"
            ]
        }
        
        return Response(response_data, status=HTTP_200_OK)
