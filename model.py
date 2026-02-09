"""
Model loading and embedding computation module.
Can be easily swapped to use different models.
"""

from sentence_transformers import SentenceTransformer, util
import torch
from typing import Dict, Tuple


class EmbeddingModel:
    """Wrapper class for embedding models."""
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize the embedding model.
        
        Args:
            model_name: Name of the sentence transformer model to use.
                        Examples: 'all-MiniLM-L6-v2', 'all-mpnet-base-v2', 'paraphrase-MiniLM-L6-v2'
        """
        print(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
        print(f"Model '{model_name}' loaded successfully!")
    
    def encode_text(self, text: str):
        """
        Encode text to embeddings.
        
        Args:
            text: Text to encode
            
        Returns:
            Tensor embedding
        """
        return self.model.encode(text, convert_to_tensor=True)
    
    def compute_similarity(self, embedding1, embedding2) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding tensor
            embedding2: Second embedding tensor
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        return util.pytorch_cos_sim(embedding1, embedding2).item()
    
    def rank_by_similarity(self, query_embedding, resume_embeddings: Dict[str, object]) -> Dict[str, float]:
        """
        Rank resume embeddings by similarity to query.
        
        Args:
            query_embedding: Embedding of job circular
            resume_embeddings: Dict of {filename: embedding}
            
        Returns:
            Dict of {filename: similarity_score}
        """
        scores = {}
        for filename, embedding in resume_embeddings.items():
            scores[filename] = self.compute_similarity(query_embedding, embedding)
        return scores
    
    def get_model_info(self) -> Dict:
        """Return information about the loaded model."""
        return {
            "model_name": self.model_name,
            "model_type": "SentenceTransformer",
            "embedding_dimension": self.model.get_sentence_embedding_dimension()
        }


# Available models (can be easily added)
AVAILABLE_MODELS = {
    'all-MiniLM-L6-v2': 'Fast, lightweight model (384-dim)',
    'all-mpnet-base-v2': 'More accurate, larger model (768-dim)',
    'paraphrase-MiniLM-L6-v2': 'Good for paraphrase detection (384-dim)',
    'sentence-transformers/all-roberta-large-v1': 'High quality (1024-dim)',
}


def get_available_models() -> Dict:
    """Return list of available models."""
    return AVAILABLE_MODELS


def create_model(model_name: str = 'all-MiniLM-L6-v2') -> EmbeddingModel:
    """
    Factory function to create an embedding model.
    
    Args:
        model_name: Name of the model to load
        
    Returns:
        EmbeddingModel instance
    """
    if model_name not in AVAILABLE_MODELS:
        print(f"Warning: '{model_name}' not in pre-configured list.")
        print(f"Available models: {list(AVAILABLE_MODELS.keys())}")
    
    return EmbeddingModel(model_name)
