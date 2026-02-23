"""Search knowledge base tool - simplified for file-based MVP."""
from typing import List, Dict, Any
from src.storage import KnowledgeBaseStorage
from src.config import settings


# Initialize knowledge base storage
kb_storage = KnowledgeBaseStorage(str(settings.context_path))


def search_product_docs_impl(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search product documentation using TF-IDF.

    Args:
        query: The search query string
        max_results: Maximum number of results to return (default: 5)

    Returns:
        List of documentation results with relevance scores
    """
    # Basic validation
    if not query or not query.strip():
        raise ValueError("Query must be a non-empty string")

    if len(query) > 1000:
        raise ValueError("Query must be less than 1000 characters")

    if max_results < 1 or max_results > 20:
        raise ValueError("max_results must be between 1 and 20")

    try:
        # Search using TF-IDF
        results = kb_storage.search_documents(query.strip(), top_k=max_results)

        # Format results
        return [
            {
                "id": idx + 1,
                "title": result["title"],
                "content": result["content"],
                "source": result["source"],
                "similarity_score": result["similarity_score"],
                "search_method": "tfidf"
            }
            for idx, result in enumerate(results)
        ]

    except Exception as e:
        # Return graceful error
        return [{
            "error": f"Knowledge base search failed: {str(e)}",
            "search_method": "error_fallback"
        }]
