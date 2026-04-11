import logging
import os
import uuid
from urllib.parse import quote
from django.conf import settings

from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR
)
from rest_framework.views import APIView

from engine.model import create_classifier
from engine.pretrained_classifier import semantic_reranker
from engine.groq import groq_ranker, groq_base
from api.serializers import ResumeUploadSerializer
from engine.utils import (
    process_resume_files,
    extract_all_resume_texts,
    calculate_skill_bonus,
    calculate_job_relevance,
    extract_contact_info,
)

logger = logging.getLogger(__name__)

# Initialize the LightGBM classifier
classifier = create_classifier(model_dir="models")

# How many top candidates to send through the slower pretrained model (if Groq fails)
_SEMANTIC_RERANK_K = 20


class ResumeClassifyAPIView(APIView):
    """API endpoint for classifying resumes."""
    
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request):
        """
        Classify and rank uploaded resumes against a job circular.
        """
        serializer = ResumeUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Validation error", "details": serializer.errors},
                status=HTTP_400_BAD_REQUEST
            )

        # Create a unique batch directory in MEDIA_ROOT
        batch_id = str(uuid.uuid4())
        media_save_path = os.path.join(settings.MEDIA_ROOT, 'resumes', batch_id)
        os.makedirs(media_save_path, exist_ok=True)

        try:
            # Parse validated parameters
            files = request.FILES.getlist('resume_files')
            logger.info(">>> API CALLED: Received %d files for processing...", len(files))
            job_circular = request.data.get('job_circular', '').strip()
            top_k = int(request.data.get('top_k', 5))
            skills_raw = request.data.get('skills', '')
            skills_list = [s.strip() for s in skills_raw.split(',') if s.strip()]
            min_experience = int(request.data.get('min_experience', 0))
            
            try:
                min_score = float(request.data.get('min_score', 0.0))
            except (TypeError, ValueError):
                min_score = 0.0

            # ---- Stage 1: File processing ----
            # Process files and save to MEDIA_ROOT
            resumes = process_resume_files(files, media_save_path)

            if not resumes:
                return Response(
                    {"error": "No valid resume files found after processing."},
                    status=HTTP_400_BAD_REQUEST,
                )

            # ---- Stage 2: Text extraction ----
            resume_texts = extract_all_resume_texts(resumes)
            if not resume_texts:
                return Response(
                    {"error": "Could not extract readable text from any files."},
                    status=HTTP_400_BAD_REQUEST,
                )

            # ---- Stage 5: Local Analysis ----
            local_results = []
            for filename, resume_text in resume_texts.items():
                try:
                    relevance = calculate_job_relevance(resume_text, job_circular)
                    bonus = calculate_skill_bonus(resume_text, skills_list, min_experience)
                    initial_score = (relevance * 0.6) + (bonus * 0.4)
                    
                    # Extract Contact Info
                    contact_info = extract_contact_info(resume_text)

                    local_results.append({
                        "filename": filename,
                        "text": resume_text,
                        "file_path": resumes[filename],
                        "keyword_relevance": relevance,
                        "skill_bonus": bonus,
                        "initial_score": initial_score,
                        "contact_info": contact_info
                    })
                except Exception as e:
                    logger.warning("Local analysis failed for '%s': %s", filename, e)

            # Sort and subset for Groq
            local_results.sort(key=lambda x: x['initial_score'], reverse=True)
            top_for_groq = local_results[:50]

            # ---- Stage 6: Groq Judgement ----
            final_scores = {}
            if groq_base.available and top_for_groq:
                final_scores = groq_ranker.rank_batch(job_circular, top_for_groq)

            # Final assembly
            results = []
            host = request.get_host()
            protocol = 'https' if request.is_secure() else 'http'

            for index, cd in enumerate(local_results):
                filename = cd['filename']
                
                if filename in final_scores:
                    semantic_score = final_scores[filename]
                    engine = "Groq Llama 3"
                elif index < _SEMANTIC_RERANK_K:
                    semantic_score = semantic_reranker.match_job(cd['text'], job_circular)
                    engine = "Local NLI"
                else:
                    semantic_score = cd['initial_score']
                    engine = "Keyword Analysis"

                final_score = (semantic_score * 0.50) + (cd['keyword_relevance'] * 0.30) + (cd['skill_bonus'] * 0.20)
                
                # Construct Download Link (URL-encode to handle spaces in folder names)
                relative_path = os.path.relpath(cd['file_path'], settings.MEDIA_ROOT).replace('\\', '/')
                encoded_path = quote(relative_path)
                resume_url = f"{protocol}://{host}{settings.MEDIA_URL}{encoded_path}"

                results.append({
                    "candidate_name": cd['contact_info']['name'],
                    "email": cd['contact_info']['email'],
                    "phone": cd['contact_info']['phone'],
                    "resume_url": resume_url,
                    "final_score": round(final_score, 4),
                    "analysis_engine": engine,
                })

            # Threshold and Top-K
            matched = [r for r in results if r['final_score'] >= min_score]
            matched.sort(key=lambda x: x['final_score'], reverse=True)
            results = matched[:top_k]

            return Response({
                "total_resumes": len(resumes),
                "top_candidates": results,
            }, status=HTTP_200_OK)

        except Exception as e:
            logger.exception("Unexpected error in classify endpoint")
            return Response(
                {"error": f"An unexpected error occurred: {e}"},
                status=HTTP_500_INTERNAL_SERVER_ERROR,
            )
