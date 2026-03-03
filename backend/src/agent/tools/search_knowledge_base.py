"""Knowledge base search tool using semantic vector similarity."""

import logging
import time
from agents import function_tool, RunContextWrapper
from fastembed import TextEmbedding

from src.database.queries import search_knowledge_base as db_search_knowledge_base

logger = logging.getLogger(__name__)

# Initialize FastEmbed model as singleton to avoid reloading on every call
# Using all-MiniLM-L6-v2 which produces 384-dimensional embeddings
_embedding_model: TextEmbedding | None = None


def get_embedding_model() -> TextEmbedding:
    """Get or create the FastEmbed model singleton."""
    global _embedding_model
    if _embedding_model is None:
        logger.info("Initializing FastEmbed model: sentence-transformers/all-MiniLM-L6-v2")
        _embedding_model = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return _embedding_model


@function_tool
async def search_knowledge_base(
    context: RunContextWrapper,
    query: str,
) -> str:
    """Search knowledge base using semantic vector similarity for relevant documentation.

    This tool performs semantic search using pgvector cosine similarity to find the most
    relevant knowledge base articles based on the meaning of the customer's inquiry, not
    just keyword matching. Uses FastEmbed (sentence-transformers/all-MiniLM-L6-v2) to
    generate query embeddings and compares against pre-computed article embeddings.

    Use this tool when customers ask:
    - Product questions and feature explanations
    - How-to guides and tutorials
    - Technical specifications and API documentation
    - Troubleshooting and common issues
    - Best practices and recommendations

    Args:
        query: Natural language search query from customer inquiry. Should be the customer's
            question or a reformulated version that captures their intent. No length limit,
            but queries under 200 characters typically work best.
            Example: "How do I reset my password?" or "API rate limits"

    Returns:
        str: Formatted string containing search results with:
            - Number of articles found
            - For each article: title, relevance score (percentage), and content summary (200 chars)
            - Message if no relevant articles found
            Example: "Found 3 relevant articles:\n\n1. Password Reset Guide (relevance: 92%)\n   To reset your password, navigate to..."

    Raises:
        Exception: If embedding generation fails, database query fails, or context is invalid.
            Error message is returned as a string rather than raising to allow agent to handle gracefully.

    Example:
        >>> # Customer asks about password reset
        >>> result = await search_knowledge_base(
        ...     context=agent_context,
        ...     query="How do I reset my password?",
        ... )
        >>> print(result)
        "Found 2 relevant articles:

        1. Password Reset Guide (relevance: 95%)
           To reset your password, navigate to Settings > Security...

        2. Account Security Best Practices (relevance: 78%)
           We recommend using a strong password with at least..."

        >>> # No relevant articles found
        >>> result = await search_knowledge_base(
        ...     context=agent_context,
        ...     query="How do I build a rocket ship?",
        ... )
        >>> print(result)
        "No relevant articles found in knowledge base. This may require human assistance."

    Notes:
        - Uses cosine similarity with minimum threshold of 0.7 (70% similarity)
        - Returns up to 5 most relevant articles by default
        - Updates context.knowledge_articles_retrieved with article IDs for tracking
        - FastEmbed model is loaded once and cached as singleton for performance
        - Embedding dimension: 384 (must match knowledge base entries)
    """
    start_time = time.time()
    conversation_id = context.context.conversation_id if context and hasattr(context.context, 'conversation_id') else None

    try:
        logger.info(
            "Starting knowledge base search",
            extra={
                "tool": "search_knowledge_base",
                "conversation_id": conversation_id,
                "query_length": len(query),
                "query_preview": query[:100],
            }
        )

        # Generate embedding for query
        embedding_model = get_embedding_model()
        query_embedding = list(embedding_model.embed([query]))[0].tolist()

        # Get database session from context
        if not context or not hasattr(context.context, 'db_session'):
            return "Error: Database session not available in context."

        session = context.context.db_session

        # Query with pgvector similarity search
        # Returns list of (KnowledgeBase, similarity_score) tuples
        results = await db_search_knowledge_base(
            session=session,
            query_embedding=query_embedding,
            limit=5,
            min_similarity=0.7  # Only return articles with >70% similarity
        )

        if not results:
            execution_time = (time.time() - start_time) * 1000
            logger.info(
                "No relevant articles found in knowledge base",
                extra={
                    "tool": "search_knowledge_base",
                    "conversation_id": conversation_id,
                    "results_count": 0,
                    "execution_time_ms": round(execution_time, 2),
                    "success": True,
                }
            )
            return "No relevant articles found in knowledge base. This may require human assistance."

        # Update context with retrieved article IDs
        article_ids = [str(article.id) for article, _ in results]
        context.context.knowledge_articles_retrieved = article_ids

        execution_time = (time.time() - start_time) * 1000
        logger.info(
            "Knowledge base search completed successfully",
            extra={
                "tool": "search_knowledge_base",
                "conversation_id": conversation_id,
                "results_count": len(results),
                "article_ids": article_ids,
                "execution_time_ms": round(execution_time, 2),
                "success": True,
            }
        )

        # Format response with article details
        response = f"Found {len(results)} relevant articles:\n\n"
        for i, (article, similarity) in enumerate(results, 1):
            # Truncate content to first 200 chars for summary
            summary = article.content[:200] + "..." if len(article.content) > 200 else article.content

            # Include similarity score for transparency
            response += f"{i}. {article.title} (relevance: {similarity:.0%})\n"
            response += f"   {summary}\n\n"

        return response

    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        logger.error(
            f"Error searching knowledge base: {e}",
            extra={
                "tool": "search_knowledge_base",
                "conversation_id": conversation_id,
                "execution_time_ms": round(execution_time, 2),
                "success": False,
                "error": str(e),
            },
            exc_info=True
        )
        return f"Error searching knowledge base: {str(e)}"
