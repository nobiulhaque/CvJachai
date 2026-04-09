import os
import logging
import json
import PIL.Image
from google import genai
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class GeminiMatcher:
    """
    Experimental high-performance matcher using Google Gemini.
    Faster and more accurate than local NLI models when an API key is provided.
    Now supports Vision (OCR for image resumes).
    """

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self._available = False
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
                self.model_name = 'gemini-1.5-flash'
                self._available = True
                logger.info("Gemini Engine initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")

    @property
    def available(self):
        return self._available

    def match_batch(self, job_description, candidate_data):
        """
        Final judgement pass using Gemini.
        candidate_data: list of dicts {filename, text, file_path, local_relevance, etc.}
        returns: {filename: final_judgement_score}
        """
        if not self.available or not candidate_data:
            return {}

        prompt_parts = [
            "You are a hiring expert. I have already performed a local keyword and skill analysis on a set of resumes.",
            "Please provide a FINAL MATCH SCORE (0.0 to 1.0) for each candidate by combining my local data with your own semantic analysis of their resume.",
            f"\nJOB DESCRIPTION:\n{job_description[:1000]}",
            "\nCANDIDATES TO JUDGE:"
        ]
        
        for i, cd in enumerate(candidate_data):
            info = f"\n--- Candidate: {cd['filename']} ---\nLocal Keyword Relevance: {cd['keyword_relevance']:.2f}\nLocal Skill Bonus: {cd['skill_bonus']:.2f}\n"
            prompt_parts.append(info)
            
            # If it's an image, pass the image object. If text, pass the text.
            ext = cd.get('filename', '').lower().split('.')[-1]
            if ext in ['png', 'jpg', 'jpeg'] and os.path.exists(cd.get('file_path', '')):
                try:
                    img = PIL.Image.open(cd['file_path'])
                    prompt_parts.append(img)
                except Exception as e:
                    logger.error(f"Error loading image {cd['filename']}: {e}")
                    prompt_parts.append(f"Resume Snippet (Text): {cd['text'][:1500]}")
            else:
                prompt_parts.append(f"Resume Snippet (Text): {cd['text'][:1500]}")
            
        prompt_parts.append("""
        For each candidate, return a JSON object where keys are filenames and values are your FINAL match scores (0.0 to 1.0).
        Consider local scores, but prioritize your own semantic understanding of their experience.
        Return ONLY valid JSON.
        Example: {"res1.pdf": 0.92, "res2.docx": 0.75}
        """)

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt_parts,
            )
            raw_text = response.text
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "{" in raw_text:
                raw_text = raw_text[raw_text.find("{"):raw_text.rfind("}")+1]
            
            return json.loads(raw_text)
        except Exception as e:
            logger.error(f"Gemini final judge pass failed: {e}")
            return {}

# Singleton instance
gemini_matcher = GeminiMatcher()
