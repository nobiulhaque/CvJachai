"""
Django REST Framework views for Resume Classifier API.
"""

import logging
import shutil
import tempfile

from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR
)
from rest_framework.views import APIView

from model import create_classifier
from serializers import ResumeUploadSerializer
from utils import (
    process_resume_files,
    extract_all_resume_texts,
    calculate_skill_bonus,
    calculate_job_relevance,
)

logger = logging.getLogger(__name__)

# Initialize the classifier
classifier = create_classifier(model_dir="models")


class ResumeClassifyAPIView(APIView):
    """API endpoint for classifying resumes."""
    
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request):
        """
        Classify and rank uploaded resumes against a job circular.

        Parameters:
        - job_circular: Job description text
        - resume_files: Resume files (PDF, DOCX, TXT, or ZIP)
        - top_k: Number of top candidates to return (default 5)
        - skills: Comma-separated required skills (optional)
        - min_experience: Minimum years of experience (optional)
        """
        serializer = ResumeUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Validation error", "details": serializer.errors},
                status=HTTP_400_BAD_REQUEST
            )

        temp_dir = None
        try:
            temp_dir = tempfile.mkdtemp()

            # Parse request parameters
            files = request.FILES.getlist('resume_files')
            job_circular = request.data.get('job_circular', '')
            top_k = int(request.data.get('top_k', 5))
            skills_raw = request.data.get('skills', '')
            skills_list = [s.strip() for s in skills_raw.split(',') if s.strip()]
            min_experience = int(request.data.get('min_experience', 0))

            # Process files
            resumes = process_resume_files(files, temp_dir)

            # Extract text
            resume_texts = extract_all_resume_texts(resumes)
            if not resume_texts:
                return Response(
                    {"error": "Could not extract text from any resume files"},
                    status=HTTP_400_BAD_REQUEST
                )

            # Classify and score each resume
            predictions = classifier.predict_batch(resume_texts)

            results = []
            for filename, prediction in predictions.items():
                resume_text = resume_texts[filename]

                # Relevance to job circular (0-1)
                relevance = calculate_job_relevance(resume_text, job_circular)

                # Skill & experience bonus (0-1)
                bonus = 0.0
                if skills_list or min_experience > 0:
                    bonus = calculate_skill_bonus(resume_text, skills_list, min_experience)

                # Final score: 50% classification confidence + 30% job relevance + 20% skill/exp bonus
                confidence = prediction['confidence']
                final_score = (confidence * 0.5) + (relevance * 0.3) + (bonus * 0.2)

                top_predictions = dict(
                    list(prediction['all_predictions'].items())[:5]
                )

                results.append({
                    "filename": filename,
                    "predicted_category": prediction['predicted_category'],
                    "confidence": round(confidence, 4),
                    "job_relevance": round(relevance, 4),
                    "skill_bonus": round(bonus, 4),
                    "final_score": round(final_score, 4),
                    "top_categories": top_predictions,
                })

            # Sort by final_score descending, return top_k
            results.sort(key=lambda x: x['final_score'], reverse=True)
            results = results[:top_k]

            response_data = {
                "job_circular_preview": job_circular[:200] + "..." if len(job_circular) > 200 else job_circular,
                "skills_searched": skills_list or None,
                "min_experience": min_experience if min_experience > 0 else None,
                "total_resumes": len(resumes),
                "processed_resumes": len(resume_texts),
                "top_k": top_k,
                "ranked_resumes": results,
            }

            return Response(response_data, status=HTTP_200_OK)
        
        except ValueError as e:
            return Response(
                {"error": f"Validation error: {str(e)}"},
                status=HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception("Error classifying resumes")
            return Response(
                {"error": f"Internal server error: {e}"},
                status=HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            # Cleanup temporary directory
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)


class HealthCheckAPIView(APIView):
    """Health check endpoint."""
    
    def get(self, request):
        """Return health status and model info."""
        model_info = classifier.get_model_info()
        
        response_data = {
            "status": "healthy",
            "model_info": model_info,
            "message": "Resume Classifier API is running"
        }
        
        return Response(response_data, status=HTTP_200_OK)


class APIInfoAPIView(APIView):
    """API information endpoint."""
    
    def get(self, request):
        """Return API information."""
        model_info = classifier.get_model_info()
        categories = classifier.get_categories()
        
        response_data = {
            "name": "Resume Classifier API",
            "version": "1.0.0",
            "description": "Classify resumes into job categories using LightGBM",
            "model_info": model_info,
            "total_categories": len(categories),
            "sample_categories": categories[:10],
            "endpoints": {
                "POST /api/classify": "Classify resumes",
                "GET /api/health": "Health check",
                "GET /api/": "API info",
                "GET /api/categories": "List all job categories"
            },
            "supported_formats": ["PDF", "DOCX", "TXT", "ZIP"]
        }
        
        return Response(response_data, status=HTTP_200_OK)


class CategoriesAPIView(APIView):
    """Endpoint to list all job categories."""
    
    def get(self, request):
        """Return all job categories."""
        categories = classifier.get_categories()
        
        response_data = {
            "total_categories": len(categories),
            "categories": categories
        }
        
        return Response(response_data, status=HTTP_200_OK)
