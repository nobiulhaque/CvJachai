import os
import logging
import json
import PIL.Image
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class GroqMatcher:
    """
    High-performance matcher using Groq and Llama 3.
    Faster and robust alternative to Gemini.
    """

    def __init__(self):
        # We look for the exact 'API_KEY' the user added to .env
        self.api_key = os.getenv("API_KEY") 
        self._available = False
        if self.api_key:
            try:
                self.client = Groq(api_key=self.api_key)
                # We use llama3-8b for blazing fast JSON generation 
                self.model_name = "llama3-8b-8192" 
                self._available = True
                logger.info("Groq Engine initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Groq: {e}")

    @property
    def available(self):
        return self._available

    def match_batch(self, job_description, candidate_data):
        """
        Final judgement pass using Groq (Llama 3).
        candidate_data: list of dicts {filename, text, file_path, local_relevance, etc.}
        returns: {filename: final_judgement_score}
        """
        if not self.available or not candidate_data:
            return {}

        prompt = (
            "You are a hiring expert. I have already performed a local keyword and skill analysis on a set of resumes.\n"
            "Please provide a FINAL MATCH SCORE (0.0 to 1.0) for each candidate by combining my local data with your own semantic analysis of their resume.\n\n"
            f"JOB DESCRIPTION:\n{job_description[:1000]}\n\n"
            "CANDIDATES TO JUDGE:\n"
        )
        
        for i, cd in enumerate(candidate_data):
            prompt += f"\n--- Candidate: {cd['filename']} ---\n"
            prompt += f"Local Keyword Relevance: {cd['keyword_relevance']:.2f}\n"
            prompt += f"Local Skill Bonus: {cd['skill_bonus']:.2f}\n"
            
            ext = cd.get('filename', '').lower().split('.')[-1]
            if ext in ['png', 'jpg', 'jpeg']:
                prompt += f"Resume Snippet (Text from Image): [IMAGE_RESUME: {cd['filename']}]\n"
            else:
                prompt += f"Resume Snippet (Text): {cd['text'][:1500]}\n"
            
        prompt += (
            "\nFor each candidate, return a JSON object where keys are filenames and values are your FINAL match scores (0.0 to 1.0).\n"
            "Consider local scores, but prioritize your own semantic understanding of their experience.\n"
            "Return ONLY a valid JSON object starting with { and ending with }, nothing else.\n"
            'Example: {"res1.pdf": 0.92, "res2.docx": 0.75}'
        )

        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a recruiting AI. Always return answers in strictly formatted JSON."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model_name,
                response_format={"type": "json_object"}
            )
            raw_text = response.choices[0].message.content
            
            if "{" in raw_text:
                raw_text = raw_text[raw_text.find("{"):raw_text.rfind("}")+1]
            return json.loads(raw_text)
        except Exception as e:
            logger.error(f"Groq final judge pass failed: {e}")
            return {}

# Singleton instance
groq_matcher = GroqMatcher()
