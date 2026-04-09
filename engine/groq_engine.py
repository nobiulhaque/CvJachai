import os
import logging
import json
import time
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
                # We use llama-3.1-8b-instant for blazing fast JSON generation 
                self.model_name = "llama-3.1-8b-instant" 
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
        Processes candidates in small chunks to stay under Free Tier token limits.
        """
        if not self.available or not candidate_data:
            return {}

        all_final_scores = {}
        # We process in small chunks of 5 resumes to ensure we stay under the 6000 TPM limit
        chunk_size = 5
        
        for index in range(0, len(candidate_data), chunk_size):
            chunk = candidate_data[index : index + chunk_size]
            logger.info("... processing Groq chunk %d-%d ...", index + 1, index + len(chunk))
            
            prompt = (
                "You are a hiring expert. I have already performed a local analysis on a set of resumes.\n"
                "Provide a FINAL MATCH SCORE (0.0 to 1.0) for each candidate.\n\n"
                f"JOB DESCRIPTION:\n{job_description[:600]}\n\n"
                "CANDIDATES TO JUDGE:\n"
            )
            
            for cd in chunk:
                prompt += f"\n--- {cd['filename']} ---\n"
                prompt += f"Local Results: Keyword={cd['keyword_relevance']:.2f}, Skills={cd['skill_bonus']:.2f}\n"
                prompt += f"Resume Snippet: {cd['text'][:700]}\n"
            
            prompt += (
                "\nReturn ONLY a valid JSON object where keys are filenames and values are match scores.\n"
                'Example: {"res1.pdf": 0.92, "res2.docx": 0.75}'
            )

            try:
                response = self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are a recruiting AI. Return strictly formatted JSON matching the example exactly."},
                        {"role": "user", "content": prompt}
                    ],
                    model=self.model_name,
                    response_format={"type": "json_object"},
                    temperature=0.0,
                    seed=42
                )
                raw_text = response.choices[0].message.content
                if "{" in raw_text:
                    raw_text = raw_text[raw_text.find("{"):raw_text.rfind("}")+1]
                
                chunk_scores = json.loads(raw_text)
                all_final_scores.update(chunk_scores)
            except Exception as e:
                logger.error(f"Groq chunk failure: {e}")
            
            # Rate limit protection: 2-second gap between chunks to avoid TPM burst errors
            if index + chunk_size < len(candidate_data):
                time.sleep(2)
        
        return all_final_scores

# Singleton instance
groq_matcher = GroqMatcher()
