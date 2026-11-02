"""
Embedding engine for semantic similarity calculations.

Uses Sentence-Transformers ('all-MiniLM-L6-v2') to compute dense vector
embeddings of text (resume text and job description) and calculates
their cosine similarity.
"""

from django.conf import settings
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Cache model instance to avoid reloading per request
_model_instance = None


def get_model():
    """
    Lazy-load the SentenceTransformer model.
    """
    global _model_instance
    if _model_instance is None:
        try:
            from sentence_transformers import SentenceTransformer
            model_name = getattr(settings, 'SENTENCE_TRANSFORMER_MODEL_NAME', 'all-MiniLM-L6-v2')
            _model_instance = SentenceTransformer(model_name)
        except Exception:
            # Fallback if sentence_transformers isn't loaded/downloaded
            _model_instance = False
    return _model_instance


def get_text_similarity(text1: str, text2: str) -> float:
    """
    Calculate semantic similarity between two text strings (0.0 to 1.0).
    """
    if not text1 or not text2:
        return 0.0

    model = get_model()
    if model:
        try:
            embeddings = model.encode([text1, text2])
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            return float(max(0.0, min(1.0, similarity)))
        except Exception:
            pass

    # Simple fallback matching if transformer is unavailable
    from sklearn.feature_extraction.text import TfidfVectorizer
    try:
        vectorizer = TfidfVectorizer().fit_transform([text1, text2])
        vectors = vectorizer.toarray()
        similarity = cosine_similarity([vectors[0]], [vectors[1]])[0][0]
        return float(max(0.0, min(1.0, similarity)))
    except Exception:
        return 0.0
