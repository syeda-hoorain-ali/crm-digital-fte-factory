import os
import pytest
import json
import tempfile
import shutil
from pathlib import Path
from collections.abc import AsyncGenerator
from mcp.client.session import ClientSession
from mcp.shared.memory import create_connected_server_and_client_session

from src.main import mcp
from src.storage import TicketStorage, KnowledgeBaseStorage, ReplyStorage, CustomerStorage


@pytest.fixture(name="temp_tickets_file")
def temp_tickets_file_fixture():
    """Create a temporary tickets JSON file for testing."""
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)

    # Sample test tickets
    test_tickets = [
        {
            "id": "TKT-001",
            "channel": "gmail",
            "customer_email": "test@example.com",
            "customer_phone": None,
            "subject": "Test ticket",
            "content": "This is a test ticket",
            "status": "open",
            "created_at": "2026-02-22T10:00:00"
        },
        {
            "id": "TKT-002",
            "channel": "whatsapp",
            "customer_email": None,
            "customer_phone": "+14155550192",
            "content": "Another test ticket",
            "status": "open",
            "created_at": "2026-02-22T11:00:00"
        }
    ]

    json.dump(test_tickets, temp_file, indent=4)
    temp_file.close()

    yield temp_file.name

    # Cleanup
    os.unlink(temp_file.name)


@pytest.fixture(name="temp_context_dir")
def temp_context_dir_fixture():
    """Create a temporary context directory with sample markdown files."""
    temp_dir = tempfile.mkdtemp()

    # Create sample markdown file
    sample_md = Path(temp_dir) / "test-docs.md"
    sample_md.write_text("""
# Test Documentation

## Feature A
This is documentation for feature A.

## Feature B
This is documentation for feature B with password reset instructions.
""")

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture(name="temp_replies_dir")
def temp_replies_dir_fixture():
    """Create a temporary replies directory for testing."""
    temp_dir = tempfile.mkdtemp()

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture(name="ticket_storage")
def ticket_storage_fixture(temp_tickets_file):
    """Create a TicketStorage instance with temporary file."""
    return TicketStorage(temp_tickets_file)


@pytest.fixture(name="knowledge_base_storage")
def knowledge_base_storage_fixture(temp_context_dir):
    """Create a KnowledgeBaseStorage instance with temporary directory."""
    return KnowledgeBaseStorage(temp_context_dir)


@pytest.fixture(name="reply_storage")
def reply_storage_fixture(temp_replies_dir):
    """Create a ReplyStorage instance with temporary directory."""
    return ReplyStorage(temp_replies_dir)


@pytest.fixture(name="customer_storage")
def customer_storage_fixture(ticket_storage):
    """Create a CustomerStorage instance."""
    return CustomerStorage(ticket_storage)


@pytest.fixture
async def client_session() -> AsyncGenerator[ClientSession]:
    """Create a connected MCP client session for testing."""
    async with create_connected_server_and_client_session(mcp, raise_exceptions=True) as _session:
        yield _session
