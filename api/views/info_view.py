from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

class APIInfoAPIView(APIView):
    """API information endpoint."""
    
    def get(self, request):
        """Return API information."""
        
        response_data = {
            "name": "CvJachai Resume Ranking Engine",
            "version": "2.0.0",
            "status": "Operational",
            "architecture": "Hybrid AI (Cloud + Local)",
            "primary_engine": "Groq Llama 3.1 (Global Judge)",
            "fallback_engine": "Local NLI Transformer",
            "extraction_engine": "Multi-threaded OCR & Text Parsers",
            "supported_formats": ["PDF", "DOCX", "TXT", "ZIP", "PNG", "JPG", "JPEG"],
            "endpoints": {
                "POST /api/classify": "Analyse and rank resumes. Supports batch uploads and images.",
                "GET /api/": "View this documentation"
            },
            "features": [
                "Dynamic Semantic Ranking",
                "Automated Skill Extraction",
                "Local-First OCR for Images",
                "Blazing Fast CPU Inference"
            ]
        }
        
        return Response(response_data, status=HTTP_200_OK)
