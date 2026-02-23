"""Utility functions for generating embeddings using fastembed."""

from typing import List
from fastembed import TextEmbedding
import logging

logger = logging.getLogger(__name__)

# Global variables to hold the embedding model
_embedding_model = None


def _load_embedding_model():
    """Load the fastembed model - called lazily when needed."""
    global _embedding_model

    if _embedding_model is not None:
        return _embedding_model

    try:
        # Use a suitable embedding model
        _embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        logger.info("Successfully loaded embedding model")
        return _embedding_model
    except ImportError:
        logger.error("fastembed not installed. Install with: pip install fastembed")
        raise
    except Exception as e:
        logger.error(f"Failed to load embedding model: {e}")
        raise


def generate_embedding(text: str) -> List[float]:
    """Generate a vector embedding for the given text."""
    try:
        model = _load_embedding_model()

        # Generate embedding - this returns an iterator, so we get the first item
        embeddings = list(model.embed([text]))

        if embeddings and len(embeddings) > 0:
            # Convert numpy array to list of floats
            embedding_array = embeddings[0]
            return embedding_array.tolist() if hasattr(embedding_array, 'tolist') else list(embedding_array)
        else:
            raise ValueError("Could not generate embedding for the given text")

    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        raise


def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for a batch of texts."""
    try:
        model = _load_embedding_model()

        # Generate embeddings for all texts
        embeddings = list(model.embed(texts))

        # Convert each embedding to a list of floats
        result = []
        for emb in embeddings:
            result.append(emb.tolist() if hasattr(emb, 'tolist') else list(emb))

        return result

    except Exception as e:
        logger.error(f"Error generating batch embeddings: {e}")
        raise