"""CRM Tools - Central export point for all tool implementations.

This module provides a single import point for all CRM tool implementations.
Each tool is implemented in its own file for better maintainability.
"""

# Import all tool implementations
from src.tools.search_knowledge_base import search_product_docs_impl
from src.tools.create_ticket import create_support_ticket_impl
from src.tools.get_customer_history import lookup_customer_impl
from src.tools.escalate_to_human import escalate_ticket_impl
from src.tools.send_response import save_reply_impl
from src.tools.identify_customer import identify_customer_impl
from src.tools.analyze_sentiment import analyze_sentiment_impl, get_sentiment_analyzer

# Export all tools for easy importing
__all__ = [
    "search_product_docs_impl",
    "create_support_ticket_impl",
    "lookup_customer_impl",
    "escalate_ticket_impl",
    "save_reply_impl",
    "identify_customer_impl",
    "analyze_sentiment_impl",
    "get_sentiment_analyzer",
]
