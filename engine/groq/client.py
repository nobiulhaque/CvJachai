import os
import logging
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class GroqClient:
    """Base client for Groq API with auto-model discovery."""
    
    def __init__(self):
        self.api_key = os.getenv("API_KEY")
        self.client = None
        self.ranker_model = "llama-3.1-8b-instant"
        self.optimizer_model = "llama-3.3-70b-versatile"
        self._available = False

        if self.api_key:
            try:
                self.client = Groq(api_key=self.api_key)
                self._available = True
                self._discover_models()
            except Exception as e:
                logger.error(f"Groq Client Init Error: {e}")

    def _discover_models(self):
        """Find best available models on Groq."""
        try:
            models = [m.id for m in self.client.models.list().data]
            eight_b = sorted([m for m in models if "8b" in m.lower()], reverse=True)
            if eight_b: self.ranker_model = eight_b[0]
            
            seventy_b = sorted([m for m in models if "70b" in m.lower()], reverse=True)
            if seventy_b: self.optimizer_model = seventy_b[0]
        except Exception as e:
            logger.warning(f"Groq Auto-Discovery failed, using defaults: {e}")

    @property
    def available(self):
        return self._available and self.client is not None

    def call(self, system_prompt, user_prompt, model, temperature=0.0, json_mode=False):
        """Centralized API call handler."""
        if not self.available: return None
        try:
            kwargs = {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "model": model,
                "temperature": temperature,
                "seed": 42
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            
            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq API Error: {e}")
            return None

# Singleton base client
groq_base = GroqClient()
