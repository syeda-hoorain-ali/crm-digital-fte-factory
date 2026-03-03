"""Database CRUD operations - modular structure.

This module provides a unified interface to all database operations,
organized by entity type for better maintainability.
"""

from .customer import (
    create_customer,
    get_customer,
    update_customer,
    delete_customer,
    list_customers,
    create_customer_identifier,
    get_customer_by_identifier,
    list_customer_identifiers,
    identify_or_create_customer,
)
from .conversation import (
    create_conversation,
    get_conversation,
    update_conversation_status,
    list_customer_conversations,
)
from .message import (
    create_message,
    get_conversation_history,
    get_latest_message,
    delete_message,
)
from .ticket import (
    create_ticket,
    get_ticket,
    update_ticket,
    list_conversation_tickets,
)
from .knowledge_base import (
    create_knowledge_base_entry,
    search_knowledge_base,
    get_knowledge_base_entry,
    update_knowledge_base_entry,
    delete_knowledge_base_entry,
)
from .channel_config import (
    create_channel_config,
    get_channel_config,
    update_channel_config,
    list_active_channels,
)
from .agent_metric import (
    create_agent_metric,
    get_conversation_metrics,
    get_aggregate_metrics,
)

__all__ = [
    # Customer operations
    "create_customer",
    "get_customer",
    "update_customer",
    "delete_customer",
    "list_customers",
    "create_customer_identifier",
    "get_customer_by_identifier",
    "list_customer_identifiers",
    "identify_or_create_customer",
    # Conversation operations
    "create_conversation",
    "get_conversation",
    "update_conversation_status",
    "list_customer_conversations",
    # Message operations
    "create_message",
    "get_conversation_history",
    "get_latest_message",
    "delete_message",
    # Ticket operations
    "create_ticket",
    "get_ticket",
    "update_ticket",
    "list_conversation_tickets",
    # KnowledgeBase operations
    "create_knowledge_base_entry",
    "search_knowledge_base",
    "get_knowledge_base_entry",
    "update_knowledge_base_entry",
    "delete_knowledge_base_entry",
    # ChannelConfig operations
    "create_channel_config",
    "get_channel_config",
    "update_channel_config",
    "list_active_channels",
    # AgentMetric operations
    "create_agent_metric",
    "get_conversation_metrics",
    "get_aggregate_metrics",
]
