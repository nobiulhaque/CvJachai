import json
import time
import logging
from .client import groq_base

logger = logging.getLogger(__name__)

CHUNK_SIZE = 5
DELAY = 2.0

class GroqRanker:
    """Specialized engine for ranking large batches of resumes."""

    def rank_batch(self, job_desc, candidates):
        if not groq_base.available or not candidates:
            return {}

        final_scores = {}
        for i in range(0, len(candidates), CHUNK_SIZE):
            chunk = candidates[i : i + CHUNK_SIZE]
            
            prompt = (
                f"JOB DESCRIPTION:\n{job_desc[:600]}\n\n"
                "CANDIDATES:\n"
            )
            for c in chunk:
                prompt += f"- {c['filename']}: LocalRank={c['initial_score']:.2f}. Snip={c['text'][:600]}\n"
            
            prompt += "\nReturn JSON: {\"filename\": 0.0 to 1.0}"

            raw = groq_base.call(
                system_prompt="You are a recruiting AI. Output strictly valid JSON scores.",
                user_prompt=prompt,
                model=groq_base.ranker_model,
                json_mode=True
            )
            
            if raw:
                try:
                    clean = raw[raw.find("{"):raw.rfind("}")+1]
                    final_scores.update(json.loads(clean))
                except Exception as e:
                    logger.error(f"Ranker Parse Error: {e}")

            if i + CHUNK_SIZE < len(candidates):
                time.sleep(DELAY)
        
        return final_scores

groq_ranker = GroqRanker()
