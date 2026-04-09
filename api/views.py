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

from engine.model import create_classifier
from engine.pretrained_classifier import semantic_reranker
from engine.gemini_engine import gemini_matcher
from api.serializers import ResumeUploadSerializer
from engine.utils import (
    process_resume_files,
    extract_all_resume_texts,
    calculate_skill_bonus,
    calculate_job_relevance,
)

logger = logging.getLogger(__name__)

# Initialize the LightGBM classifier
classifier = create_classifier(model_dir="models")

# How many top candidates to send through the slower pretrained model
_SEMANTIC_RERANK_K = 50


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
        except OSError as e:
            logger.exception("Failed to create temp directory")
            return Response(
                {"error": f"Server error: could not create temporary storage. {e}"},
                status=HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            # Parse validated parameters
            files = request.FILES.getlist('resume_files')
            job_circular = request.data.get('job_circular', '').strip()
            top_k = int(request.data.get('top_k', 5))
            skills_raw = request.data.get('skills', '')
            skills_list = [s.strip() for s in skills_raw.split(',') if s.strip()]
            min_experience = int(request.data.get('min_experience', 0))
            # Minimum final_score a resume must reach to be considered a match
            try:
                min_score = float(request.data.get('min_score', 0.0))
                if not (0.0 <= min_score <= 1.0):
                    raise ValueError
            except (TypeError, ValueError):
                return Response(
                    {"error": "min_score must be a decimal between 0.0 and 1.0."},
                    status=HTTP_400_BAD_REQUEST,
                )

            # ---- Stage 1: File processing ----
            try:
                resumes = process_resume_files(files, temp_dir)
            except ValueError as e:
                return Response(
                    {"error": f"Invalid file: {e}"},
                    status=HTTP_400_BAD_REQUEST,
                )
            except Exception as e:
                logger.exception("Error processing uploaded files")
                return Response(
                    {"error": f"Failed to process uploaded files: {e}"},
                    status=HTTP_500_INTERNAL_SERVER_ERROR,
                )

            if not resumes:
                return Response(
                    {"error": "No valid resume files found after processing. "
                              "Ensure files are PDF, DOCX, TXT, or a ZIP containing them."},
                    status=HTTP_400_BAD_REQUEST,
                )

            # ---- Stage 2: Text extraction ----
            try:
                resume_texts = extract_all_resume_texts(resumes)
            except Exception as e:
                logger.exception("Error extracting text from resumes")
                return Response(
                    {"error": f"Failed to extract text from resume files: {e}"},
                    status=HTTP_500_INTERNAL_SERVER_ERROR,
                )

            failed_extractions = len(resumes) - len(resume_texts)
            if not resume_texts:
                return Response(
                    {"error": "Could not extract readable text from any of the uploaded "
                              "resume files. Ensure files are not scanned images or password-protected."},
                    status=HTTP_400_BAD_REQUEST,
                )

            # ---- Stage 3: Feature Extraction (Done in Utils) ----
            # Text was extracted in Stage 2.

            # ---- Stage 5: Stage 1 - Local Model Analysis (Fast) ----
            # Perform keyword, skill, and text-stat analysis for EVERY resume.
            local_results = []
            for filename, resume_text in resume_texts.items():
                try:
                    relevance = calculate_job_relevance(resume_text, job_circular)
                    bonus = 0.0
                    if skills_list or min_experience > 0:
                        bonus = calculate_skill_bonus(resume_text, skills_list, min_experience)

                    # Quick local initial score (weighted 50/50 for Stage 1 filtering)
                    initial_score = (relevance * 0.6) + (bonus * 0.4)

                    local_results.append({
                        "filename": filename,
                        "text": resume_text,
                        "file_path": resumes[filename],
                        "keyword_relevance": relevance,
                        "skill_bonus": bonus,
                        "initial_score": initial_score
                    })
                except Exception as e:
                    logger.warning("Local analysis failed for '%s': %s", filename, e)

            # Sort by local score to pick top candidates for Gemini
            local_results.sort(key=lambda x: x['initial_score'], reverse=True)
            top_for_gemini = local_results[:20]  # Judge top 20 resumes with Gemini

            # ---- Stage 6: Stage 2 - Gemini Final Judgement (Smart) ----
            final_scores = {}
            if gemini_matcher.available and top_for_gemini:
                logger.info("Stage 2: Sending top %d candidates to Gemini judge...", len(top_for_gemini))
                final_scores = gemini_matcher.match_batch(job_circular, top_for_gemini)

            # Final assembly of results
            results = []
            for cd in local_results:
                filename = cd['filename']
                
                # If Gemini judged it, use Gemini's score as the base (60%)
                # otherwise fallback to local semantic score or initial score
                if filename in final_scores:
                    semantic_score = final_scores[filename]
                    engine = "Gemini 1.5 Flash (Final Judge)"
                else:
                    # Fallback for resumes not in the top 20 or if Gemini failed
                    try:
                        semantic_score = semantic_reranker.match_job(cd['text'], job_circular)
                        engine = "Local NLI Transformer"
                    except Exception as e:
                        logger.warning("Local semantic reranking failed: %s", e)
                        semantic_score = cd['initial_score']
                        engine = "Local Initial Analysis"

                # Weighted Final Score: 50% Semantic (Gemini/Local) + 30% Keyword + 20% Skills
                final_score = (semantic_score * 0.50) + (cd['keyword_relevance'] * 0.30) + (cd['skill_bonus'] * 0.20)

                results.append({
                    "filename": filename,
                    "final_score": round(final_score, 4),
                    "semantic_score": round(semantic_score, 4),
                    "keyword_relevance": round(cd['keyword_relevance'], 4),
                    "skill_bonus": round(cd['skill_bonus'], 4),
                    "analysis_engine": engine,
                    "match_summary": f"Final judgement provided by {engine} based on hybrid analysis."
                })

            # ---- Final Step: Threshold filtering & Top-K selection ----
            # Filter results by the minimum score threshold
            matched = [r for r in results if r['final_score'] >= min_score]
            
            if not matched:
                top_score = results[0]['final_score'] if results else 0.0
                return Response(
                    {
                        "no_candidates_found": True,
                        "reason": f"No resumes met the min_score of {min_score}. Best score: {top_score:.4f}",
                        "min_score_required": min_score,
                        "best_score_found": round(top_score, 4),
                        "total_resumes_provided": len(resumes)
                    },
                    status=HTTP_200_OK
                )

            # Sort by final score and take top K
            matched.sort(key=lambda x: x['final_score'], reverse=True)
            results = matched[:top_k]


            response_data = {
                "job_circular_preview": (
                    job_circular[:200] + "..." if len(job_circular) > 200 else job_circular
                ),
                "analysis_engine": "Gemini Hybrid" if gemini_matcher.available else "Local Hybrid",
                "skills_searched": skills_list or None,
                "min_experience": min_experience if min_experience > 0 else None,
                "total_resumes_provided": len(resumes),
                "successfully_analysed": len(resume_texts),
                "top_k_requested": top_k,
                "best_candidates": results,
            }

            return Response(response_data, status=HTTP_200_OK)

        except Exception as e:
            logger.exception("Unexpected error in classify endpoint")
            return Response(
                {"error": f"An unexpected error occurred: {e}"},
                status=HTTP_500_INTERNAL_SERVER_ERROR,
            )
        finally:
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)






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
