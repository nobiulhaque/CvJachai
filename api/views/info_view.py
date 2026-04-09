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
            "version": "3.1.0",
            "status": "Operational (Secure)",
            "authentication": "JWT Bearer Token Required",
            "architecture": "Modular Hybrid AI (Groq Cloud + Local OCR)",
            "primary_engine": f"Groq {groq_base.ranker_model}/{groq_base.optimizer_model}",
            "endpoints": {
                "POST /api/auth/signup": "Create account (Email based)",
                "POST /api/auth/signin": "Login & get Profile + Tokens",
                "GET/PATCH /api/auth/profile": "View/Update professional details",
                "POST /api/classify": "Rank massive resume batches (400+) instantly",
                "POST /api/optimize": "ATS Resume Rewrite (Llama 3.3 70B)",
                "GET /api/": "View this documentation"
            },
            "features": [
                "Deterministic AI Ranking (Temp 0.0)",
                "Bulk 1000+ Resume Batch Support",
                "Multi-threaded OCR Extraction",
                "Auto-Model Discovery (Always latest Llama)",
                "Professional ATS Resume Optimizer"
            ]
        }
        
        return Response(response_data, status=HTTP_200_OK)
