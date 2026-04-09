import logging
from .client import groq_base

logger = logging.getLogger(__name__)

class GroqOptimizer:
    """Specialized engine for ATS resume optimization."""

    def optimize(self, text, job_desc=None):
        if not groq_base.available:
            return None

        prompt = (
            "Rewrite this resume to be 100% ATS-friendly and professional.\n"
            "Use clear sections and impact-driven action verbs.\n\n"
        )
        if job_desc:
            prompt += f"TARGET JOB:\n{job_desc[:800]}\n\n"
        
        prompt += f"RESUME:\n{text[:4000]}"

        return groq_base.call(
            system_prompt="You are an expert Resume Writer. Provide a beautifully formatted Markdown resume.",
            user_prompt=prompt,
            model=groq_base.optimizer_model,
            temperature=0.3
        )

groq_optimizer = GroqOptimizer()
