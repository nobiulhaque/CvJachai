import logging
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from api.models import Job, Application
from api.serializers import JobSerializer, ApplicationSerializer
from engine.utils import extract_all_resume_texts, calculate_job_relevance, calculate_skill_bonus, extract_contact_info
from engine.groq import groq_ranker, groq_base

logger = logging.getLogger(__name__)

class JobCreateListView(generics.ListCreateAPIView):
    """
    List all jobs (Public) or Create a new job (Authenticated HR).
    """
    queryset = Job.objects.filter(is_active=True).order_by('-created_at')
    serializer_class = JobSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class ApplyJobView(generics.CreateAPIView):
    """
    Apply for a job without login (Public).
    """
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    permission_classes = [permissions.AllowAny]

class JobApplicationsListView(generics.ListAPIView):
    """
    View list of applicants for a specific job (Authenticated HR - owner only).
    """
    serializer_class = ApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        job_id = self.kwargs.get('job_id')
        job = get_object_or_404(Job, id=job_id, created_by=self.request.user)
        return Application.objects.filter(job=job).order_by('-applied_at')

class AnalyzeJobApplicantsView(APIView):
    """
    Screen and analyze all applicants for a specific job (Authenticated HR).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, job_id):
        job = get_object_or_404(Job, id=job_id, created_by=self.request.user)
        applications = Application.objects.filter(job=job)
        
        if not applications.exists():
            return Response({"error": "No applicants to analyze."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Prepare data for analysis
        # Map resume files to local paths
        resume_texts = {}
        apps_map = {}
        for app in applications:
            if app.resume_file:
                # In standard Django, .path gives the absolute path
                try:
                    from engine.utils import extract_text_from_file
                    text = extract_text_from_file(app.resume_file.path)
                    resume_texts[app.id] = text
                    apps_map[app.id] = app
                except Exception as e:
                    logger.warning(f"Failed to extract text for app {app.id}: {e}")

        if not resume_texts:
            return Response({"error": "Could not extract text from any applicant resumes."}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Run Local Analysis
        skills_list = [s.strip() for s in job.skills_required.split(',') if s.strip()]
        
        results = []
        for app_id, text in resume_texts.items():
            relevance = calculate_job_relevance(text, job.description)
            bonus = calculate_skill_bonus(text, skills_list, job.min_experience)
            initial_score = (relevance * 0.6) + (bonus * 0.4)
            
            results.append({
                "app_id": app_id,
                "text": text,
                "initial_score": initial_score,
                "relevance": relevance,
                "bonus": bonus
            })

        # 3. Sort for LLM (Top 10 for batch)
        results.sort(key=lambda x: x['initial_score'], reverse=True)
        top_for_groq = results[:10]
        
        # Format for Groq (needs list of dicts with 'filename' and 'text')
        groq_input = [{"filename": str(r['app_id']), "text": r['text']} for r in top_for_groq]
        
        final_scores = {}
        if groq_base.available:
            final_scores = groq_ranker.rank_batch(job.description, groq_input)

        # 4. Save results back to applications
        for res in results:
            app = apps_map[res['app_id']]
            app_id_str = str(res['app_id'])
            
            semantic_score = res['initial_score']
            verdict = ""
            strengths = []
            
            if app_id_str in final_scores:
                g_data = final_scores[app_id_str]
                if isinstance(g_data, dict):
                    semantic_score = float(g_data.get('score', 0.5))
                    verdict = g_data.get('verdict', '')
                    strengths = g_data.get('strengths', [])
                else:
                    semantic_score = float(g_data)

            final_score = (semantic_score * 0.5) + (res['relevance'] * 0.3) + (res['bonus'] * 0.2)
            
            # Application of "University Boost"
            boosted = 0.88 + (final_score ** 0.5) * 0.10 if final_score > 0 else 0
            
            app.match_score = boosted
            app.analysis_data = {
                "verdict": verdict,
                "strengths": strengths,
                "raw_relevance": res['relevance'],
                "skill_bonus": res['bonus']
            }
            app.save()

        return Response({"message": f"Successfully analyzed {len(results)} applicants."}, status=status.HTTP_200_OK)
