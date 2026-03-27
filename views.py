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
from pretrained_classifier import semantic_reranker
from serializers import ResumeUploadSerializer
from utils import (
    process_resume_files,
    extract_all_resume_texts,
    calculate_skill_bonus,
    calculate_job_relevance,
    infer_job_category_from_resumes,
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

            # ---- Stage 4: Classification ----
            try:
                predictions = classifier.predict_batch(resume_texts)
            except Exception as e:
                logger.exception("Error during batch classification")
                return Response(
                    {"error": f"Classification model error: {e}"},
                    status=HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # ---- Stage 4b: Job category inference ----
            # Primary: if the semantic model is available, classify the job circular
            # DIRECTLY — this is the most reliable inference method because NLI
            # understands natural language without needing to look at resumes at all.
            # Fallback: vocabulary-overlap against the resume pool (Stage 4b original logic).
            categories = classifier.get_categories()
            inferred_category = None
            if semantic_reranker.available:
                try:
                    job_cat_scores = semantic_reranker.classify(job_circular, categories)
                    if job_cat_scores:
                        inferred_category = max(job_cat_scores, key=job_cat_scores.get)
                        logger.info(
                            "Job category inferred via semantic model: '%s' (scores: %s)",
                            inferred_category,
                            {k: round(v, 3) for k, v in job_cat_scores.items()},
                        )
                except Exception as e:
                    logger.warning("Semantic job inference failed, falling back: %s", e)

            if not inferred_category:
                try:
                    inferred_category = infer_job_category_from_resumes(
                        job_circular, predictions, resume_texts
                    )
                except Exception as e:
                    logger.warning("Vocabulary job inference failed: %s", e)

            # ---- Stage 5: Scoring (using LightGBM predictions) ----
            results = []
            skipped = []
            for filename, prediction in predictions.items():
                try:
                    resume_text = resume_texts[filename]
                    relevance = calculate_job_relevance(resume_text, job_circular)

                    bonus = 0.0
                    if skills_list or min_experience > 0:
                        bonus = calculate_skill_bonus(resume_text, skills_list, min_experience)

                    predicted_cat = prediction['predicted_category']
                    confidence = prediction['confidence']

                    if inferred_category:
                        category_alignment = 1.0 if predicted_cat == inferred_category else 0.0
                    else:
                        category_alignment = confidence

                    # Base score — 35% confidence + 30% relevance + 20% skill + 15% alignment
                    final_score = (
                        (confidence * 0.35)
                        + (relevance * 0.30)
                        + (bonus * 0.20)
                        + (category_alignment * 0.15)
                    )

                    top_predictions = dict(list(prediction['all_predictions'].items())[:5])
                    results.append({
                        "filename": filename,
                        "predicted_category": predicted_cat,
                        "confidence": round(confidence, 4),
                        "job_relevance": round(relevance, 4),
                        "skill_bonus": round(bonus, 4),
                        "category_alignment": round(category_alignment, 4),
                        "final_score": round(final_score, 4),
                        "top_categories": top_predictions,
                    })
                except Exception as e:
                    logger.warning("Skipping '%s' due to scoring error: %s", filename, e)
                    skipped.append({"filename": filename, "reason": str(e)})

            if not results:
                return Response(
                    {"error": "All resumes failed during scoring. "
                              "Please check file contents and try again.",
                     "skipped": skipped},
                    status=HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Pre-sort by current score before semantic re-ranking
            results.sort(key=lambda x: x['final_score'], reverse=True)

            # ---- Stage 6: Semantic re-ranking ----
            # Run zero-shot NLI on the top-K candidates only (for speed).
            # Key change: the semantic model OVERRIDES LightGBM's predicted_category
            # when it confidently disagrees. This corrects the "everything is peion"
            # bias from undertrained LightGBM models.
            semantic_used = False
            if semantic_reranker.available:
                try:
                    top_candidates = results[:_SEMANTIC_RERANK_K]
                    candidate_texts = {
                        r["filename"]: resume_texts[r["filename"]]
                        for r in top_candidates
                        if r["filename"] in resume_texts
                    }
                    semantic_scores = semantic_reranker.classify_batch(candidate_texts, categories)
                    updated_count = 0

                    for r in top_candidates:
                        sem = semantic_scores.get(r["filename"], {})
                        if not sem:
                            continue

                        # Semantic model's top predicted category and its confidence
                        sem_top_cat = max(sem, key=sem.get)
                        sem_top_conf = sem[sem_top_cat]

                        # Override LightGBM's category if semantic is meaningfully
                        # more confident in a DIFFERENT category (threshold: 30%).
                        # This corrects the "peion" catch-all bias.
                        if sem_top_cat != r["predicted_category"] and sem_top_conf >= 0.30:
                            r["predicted_category"] = sem_top_cat
                            r["confidence"] = round(sem_top_conf, 4)
                            r["semantic_override"] = True
                        else:
                            r["semantic_override"] = False

                        r["semantic_confidence"] = round(sem_top_conf, 4)

                        # Recompute category_alignment with (possibly corrected) category
                        if inferred_category:
                            r["category_alignment"] = (
                                1.0 if r["predicted_category"] == inferred_category else 0.0
                            )

                        # Final score with semantic-corrected values
                        # Weights sum to 1.0: confidence(35) + relevance(30) + skill(20) + align(15)
                        r["final_score"] = round(
                            (r["confidence"] * 0.35)
                            + (r["job_relevance"] * 0.30)
                            + (r["skill_bonus"] * 0.20)
                            + (r["category_alignment"] * 0.15),
                            4,
                        )
                        updated_count += 1

                    semantic_used = updated_count > 0
                    if semantic_used:
                        results.sort(key=lambda x: x['final_score'], reverse=True)
                        logger.info(
                            "Semantic re-ranking applied to %d/%d candidates.",
                            updated_count, len(top_candidates),
                        )
                except Exception as e:
                    logger.warning("Semantic re-ranking failed, using LightGBM only: %s", e)


            # ---- Stage 6: No-match check ----
            # Filter out resumes that don't meet the minimum score threshold.
            matched = [r for r in results if r['final_score'] >= min_score]
            if not matched:
                top_score = results[0]['final_score'] if results else 0.0
                return Response(
                    {
                        "no_candidates_found": True,
                        "reason": (
                            f"None of the {len(results)} scored resumes met the minimum "
                            f"score threshold of {min_score:.2f}. "
                            f"The best score achieved was {top_score:.4f}. "
                            "Try lowering min_score, uploading more relevant resumes, "
                            "or refining the job circular text."
                        ),
                        "min_score_required": min_score,
                        "best_score_found": round(top_score, 4),
                        "inferred_job_category": inferred_category,
                        "total_resumes": len(resumes),
                        "processed_resumes": len(resume_texts),
                    },
                    status=HTTP_200_OK,
                )

            results = matched[:top_k]

            response_data = {
                "job_circular_preview": (
                    job_circular[:200] + "..." if len(job_circular) > 200 else job_circular
                ),
                "inferred_job_category": inferred_category,
                "semantic_reranking_used": semantic_used,
                "skills_searched": skills_list or None,
                "min_experience": min_experience if min_experience > 0 else None,
                "total_resumes": len(resumes),
                "processed_resumes": len(resume_texts),
                "failed_extractions": failed_extractions,
                "skipped_scoring": skipped or None,
                "top_k": top_k,
                "ranked_resumes": results,
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
