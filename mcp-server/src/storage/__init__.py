"""File-based storage layer for MCP server."""

from .file_storage import (
    TicketStorage,
    KnowledgeBaseStorage,
    ReplyStorage,
    CustomerStorage,
)

__all__ = [
    "TicketStorage",
    "KnowledgeBaseStorage",
    "ReplyStorage",
    "CustomerStorage",
]
