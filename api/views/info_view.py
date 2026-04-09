from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

class APIInfoAPIView(APIView):
    """API information endpoint."""
    
    def get(self, request):
        """Return API information."""
        
        response_data = {
            "name": "Dynamic Resume Ranking API",
            "version": "1.5.0",
            "description": "Rank resumes dynamically against a job circular using semantic matching and skill analysis.",
            "engine": "NLP-Powered Matcher",
            "endpoints": {
                "POST /api/classify": "Analyse and rank resumes against a job description",
                "GET /api/": "API info"
            },
            "supported_formats": ["PDF", "DOCX", "TXT", "ZIP"],
            "note": "This API does not use pre-selected categories; it matches resumes directly to your job circular text."
        }
        
        return Response(response_data, status=HTTP_200_OK)
