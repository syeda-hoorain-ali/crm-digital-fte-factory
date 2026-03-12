"""Integration tests for database CRUD operations with real database."""

import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.queries import (
    # Customer operations
    create_customer,
    get_customer,
    update_customer,
    delete_customer,
    list_customers,
    # CustomerIdentifier operations
    create_customer_identifier,
    get_customer_by_identifier,
    list_customer_identifiers,
    # Conversation operations
    create_conversation,
    get_conversation,
    update_conversation_status,
    list_customer_conversations,
    # Message operations
    create_message,
    get_conversation_history,
    get_latest_message,
    delete_message,
    # Ticket operations
    create_ticket,
    get_ticket,
    update_ticket,
    list_conversation_tickets,
    # KnowledgeBase operations
    create_knowledge_base_entry,
    search_knowledge_base,
    get_knowledge_base_entry,
    update_knowledge_base_entry,
    delete_knowledge_base_entry,
)
from src.database.models import (
    IdentifierType,
    Channel,
    ConversationStatus,
    MessageRole,
    MessageDirection,
    Priority,
    TicketStatus,
)

a = 'a'

from src.database.models import (
    Channel,
    Customer,
    CustomerIdentifier,
    Conversation,
    ConversationStatus,
    IdentifierType,
    KnowledgeBase,
    Message,
    MessageRole,
    MessageDirection,
    Ticket,
)


# ============================================================================
# Integration Tests for Customer CRUD (T085)
# ============================================================================

@pytest.mark.integration
@pytest.mark.database
class TestCustomerCRUD:
    """Integration tests for Customer CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_customer(self, db_session: AsyncSession):
        """Test creating a new customer."""
        customer = await create_customer(
            db_session,
            name="John Doe",
            email="john@example.com",
            phone="+1234567890",
            meta_data={"tier": "premium"},
        )

        assert customer.id is not None
        assert customer.name == "John Doe"
        assert customer.email == "john@example.com"
        assert customer.phone == "+1234567890"
        assert customer.metadata_["tier"] == "premium"

    @pytest.mark.asyncio
    async def test_get_customer(self, db_session: AsyncSession, test_customer: Customer):
        """Test retrieving customer by ID."""
        customer = await get_customer(db_session, test_customer.id)

        assert customer is not None
        assert customer.id == test_customer.id
        assert customer.email == test_customer.email

    @pytest.mark.asyncio
    async def test_get_customer_not_found(self, db_session: AsyncSession):
        """Test retrieving non-existent customer returns None."""
        customer = await get_customer(db_session, uuid4())

        assert customer is None

    @pytest.mark.asyncio
    async def test_update_customer(self, db_session: AsyncSession, test_customer: Customer):
        """Test updating customer information."""
        updated = await update_customer(
            db_session,
            test_customer.id,
            name="Updated Name",
        )

        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.email == test_customer.email  # Unchanged

    @pytest.mark.asyncio
    async def test_delete_customer(self, db_session: AsyncSession, test_customer: Customer):
        """Test deleting a customer."""
        deleted = await delete_customer(db_session, test_customer.id)

        assert deleted is True

        # Verify customer is gone
        customer = await get_customer(db_session, test_customer.id)
        assert customer is None

    @pytest.mark.asyncio
    async def test_list_customers(
        self, db_session: AsyncSession, test_customer: Customer, test_customer_premium: Customer
    ):
        """Test listing customers with pagination."""
        customers = await list_customers(db_session, limit=10, offset=0)

        assert len(customers) >= 2
        customer_ids = [c.id for c in customers]
        assert test_customer.id in customer_ids
        assert test_customer_premium.id in customer_ids


# ============================================================================
# Integration Tests for CustomerIdentifier CRUD (T086)
# ============================================================================

@pytest.mark.integration
@pytest.mark.database
class TestCustomerIdentifierCRUD:
    """Integration tests for CustomerIdentifier CRUD with cross-channel lookup."""

    @pytest.mark.asyncio
    async def test_create_customer_identifier(self, db_session: AsyncSession, test_customer: Customer):
        """Test creating a customer identifier."""
        identifier = await create_customer_identifier(
            db_session,
            test_customer.id,
            IdentifierType.EMAIL,
            "test@example.com",
        )

        assert identifier.id is not None
        assert identifier.customer_id == test_customer.id
        assert identifier.identifier_type == IdentifierType.EMAIL
        assert identifier.identifier_value == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_customer_by_identifier_email(
        self, db_session: AsyncSession, test_customer: Customer, test_customer_identifier_email: CustomerIdentifier
    ):
        """Test cross-channel lookup by email."""
        customer = await get_customer_by_identifier(
            db_session,
            IdentifierType.EMAIL,
            test_customer.email,
        )

        assert customer is not None
        assert customer.id == test_customer.id

    @pytest.mark.asyncio
    async def test_get_customer_by_identifier_phone(
        self, db_session: AsyncSession, test_customer: Customer, test_customer_identifier_phone: CustomerIdentifier
    ):
        """Test cross-channel lookup by phone."""
        customer = await get_customer_by_identifier(
            db_session,
            IdentifierType.PHONE,
            test_customer.phone,
        )

        assert customer is not None
        assert customer.id == test_customer.id

    @pytest.mark.asyncio
    async def test_get_customer_by_identifier_not_found(self, db_session: AsyncSession):
        """Test lookup with non-existent identifier returns None."""
        customer = await get_customer_by_identifier(
            db_session,
            IdentifierType.EMAIL,
            "nonexistent@example.com",
        )

        assert customer is None

    @pytest.mark.asyncio
    async def test_list_customer_identifiers(
        self,
        db_session: AsyncSession,
        test_customer: Customer,
        test_customer_identifier_email: CustomerIdentifier,
        test_customer_identifier_phone: CustomerIdentifier,
    ):
        """Test listing all identifiers for a customer."""
        identifiers = await list_customer_identifiers(db_session, test_customer.id)

        assert len(identifiers) >= 2
        types = [i.identifier_type for i in identifiers]
        assert IdentifierType.EMAIL in types
        assert IdentifierType.PHONE in types


# ============================================================================
# Integration Tests for Conversation CRUD (T087)
# ============================================================================

@pytest.mark.integration
@pytest.mark.database
class TestConversationCRUD:
    """Integration tests for Conversation CRUD with lifecycle tracking."""

    @pytest.mark.asyncio
    async def test_create_conversation(self, db_session: AsyncSession, test_customer: Customer):
        """Test creating a new conversation."""
        conversation = await create_conversation(
            db_session,
            test_customer.id,
            Channel.EMAIL,
            ConversationStatus.ACTIVE,
        )

        assert conversation.id is not None
        assert conversation.customer_id == test_customer.id
        assert conversation.initial_channel == Channel.EMAIL
        assert conversation.status == ConversationStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_get_conversation(self, db_session: AsyncSession, test_conversation: Conversation):
        """Test retrieving conversation by ID."""
        conversation = await get_conversation(db_session, test_conversation.id)

        assert conversation is not None
        assert conversation.id == test_conversation.id

    @pytest.mark.asyncio
    async def test_update_conversation_status(self, db_session: AsyncSession, test_conversation: Conversation):
        """Test updating conversation status with lifecycle management."""
        updated = await update_conversation_status(
            db_session,
            test_conversation.id,
            ConversationStatus.RESOLVED,
        )

        assert updated is not None
        assert updated.status == ConversationStatus.RESOLVED

    @pytest.mark.asyncio
    async def test_update_conversation_status_sets_ended_at(
        self, db_session: AsyncSession, test_conversation: Conversation
    ):
        """Test updating to CLOSED status sets ended_at timestamp."""
        updated = await update_conversation_status(
            db_session,
            test_conversation.id,
            ConversationStatus.CLOSED,
        )

        assert updated.ended_at is not None

    @pytest.mark.asyncio
    async def test_list_customer_conversations(
        self, db_session: AsyncSession, test_customer: Customer, test_conversation: Conversation
    ):
        """Test listing conversations for a customer."""
        conversations = await list_customer_conversations(
            db_session,
            test_customer.id,
            status=None,
            limit=10,
            offset=0,
        )

        assert len(conversations) >= 1
        conv_ids = [c.id for c in conversations]
        assert test_conversation.id in conv_ids

    @pytest.mark.asyncio
    async def test_list_customer_conversations_filtered(
        self, db_session: AsyncSession, test_customer: Customer, test_conversation: Conversation
    ):
        """Test listing conversations filtered by status."""
        conversations = await list_customer_conversations(
            db_session,
            test_customer.id,
            status=ConversationStatus.ACTIVE,
            limit=10,
            offset=0,
        )

        # All returned conversations should be ACTIVE
        for conv in conversations:
            assert conv.status == ConversationStatus.ACTIVE


# ============================================================================
# Integration Tests for Message CRUD (T088)
# ============================================================================

@pytest.mark.integration
@pytest.mark.database
class TestMessageCRUD:
    """Integration tests for Message CRUD with conversation history."""

    @pytest.mark.asyncio
    async def test_create_message(self, db_session: AsyncSession, test_conversation: Conversation):
        """Test creating a new message."""
        message = await create_message(
            db_session,
            test_conversation.id,
            MessageRole.CUSTOMER,
            "Hello, I need help",
            MessageDirection.INBOUND,
            Channel.API,
            tokens_used=50,
            latency_ms=100,
        )

        assert message.id is not None
        assert message.conversation_id == test_conversation.id
        assert message.role == MessageRole.CUSTOMER
        assert message.content == "Hello, I need help"
        assert message.tokens_used == 50

    @pytest.mark.asyncio
    async def test_get_conversation_history(
        self, 
        db_session: AsyncSession, 
        test_conversation: Conversation, 
        test_message_customer: Message, 
        test_message_agent: Message
    ):
        """Test retrieving conversation history in chronological order."""
        messages = await get_conversation_history(
            db_session,
            test_conversation.id,
            limit=100,
            offset=0,
        )

        assert len(messages) >= 2
        # Messages should be in chronological order (oldest first)
        assert messages[0].created_at <= messages[-1].created_at

    @pytest.mark.asyncio
    async def test_get_latest_message(
        self, db_session: AsyncSession, test_conversation: Conversation, test_message_agent: Message
    ):
        """Test retrieving the most recent message."""
        latest = await get_latest_message(db_session, test_conversation.id)

        assert latest is not None
        # Should be the agent message (created after customer message)
        assert latest.role == MessageRole.AGENT

    @pytest.mark.asyncio
    async def test_delete_message(self, db_session: AsyncSession, test_message_customer: Message):
        """Test deleting a message."""
        deleted = await delete_message(db_session, test_message_customer.id)

        assert deleted is True


# ============================================================================
# Integration Tests for Ticket CRUD (T089)
# ============================================================================

@pytest.mark.integration
@pytest.mark.database
class TestTicketCRUD:
    """Integration tests for Ticket CRUD with conversation linking."""

    @pytest.mark.asyncio
    async def test_create_ticket(
        self, db_session: AsyncSession, test_conversation: Conversation, test_customer: Customer
    ):
        """Test creating a new ticket."""
        ticket = await create_ticket(
            db_session,
            test_conversation.id,
            test_customer.id,
            Channel.API,
            category="technical",
            priority=Priority.HIGH,
            status=TicketStatus.OPEN,
        )

        assert ticket.id is not None
        assert ticket.conversation_id == test_conversation.id
        assert ticket.customer_id == test_customer.id
        assert ticket.category == "technical"
        assert ticket.priority == Priority.HIGH

    @pytest.mark.asyncio
    async def test_get_ticket(self, db_session: AsyncSession, test_ticket: Ticket):
        """Test retrieving ticket by ID."""
        ticket = await get_ticket(db_session, test_ticket.id)

        assert ticket is not None
        assert ticket.id == test_ticket.id

    @pytest.mark.asyncio
    async def test_update_ticket(self, db_session: AsyncSession, test_ticket: Ticket):
        """Test updating ticket with resolution tracking."""
        updated = await update_ticket(
            db_session,
            test_ticket.id,
            status=TicketStatus.RESOLVED,
            resolution="Issue resolved successfully",
        )

        assert updated is not None
        assert updated.status == TicketStatus.RESOLVED
        assert updated.resolution_notes == "Issue resolved successfully"
        assert updated.resolved_at is not None

    @pytest.mark.asyncio
    async def test_list_conversation_tickets(
        self, db_session: AsyncSession, test_conversation: Conversation, test_ticket: Ticket
    ):
        """Test listing all tickets for a conversation."""
        tickets = await list_conversation_tickets(db_session, test_conversation.id)

        assert len(tickets) >= 1
        ticket_ids = [t.id for t in tickets]
        assert test_ticket.id in ticket_ids


# ============================================================================
# Integration Tests for KnowledgeBase CRUD (T090)
# ============================================================================

@pytest.mark.integration
@pytest.mark.database
class TestKnowledgeBaseCRUD:
    """Integration tests for KnowledgeBase CRUD with vector search."""

    @pytest.mark.asyncio
    async def test_create_knowledge_base_entry(self, db_session: AsyncSession):
        """Test creating a knowledge base entry."""
        embedding = [0.1] * 384  # 384-dimensional embedding

        entry = await create_knowledge_base_entry(
            db_session,
            "Test Article",
            "This is test content",
            embedding,
            metadata={"category": "test"},
        )

        assert entry.id is not None
        assert entry.title == "Test Article"
        assert entry.content == "This is test content"
        assert len(entry.embedding) == 384

    @pytest.mark.asyncio
    async def test_search_knowledge_base(self, db_session: AsyncSession, test_knowledge_article: KnowledgeBase):
        """Test semantic search with vector similarity."""
        # Use same embedding as test article for high similarity
        query_embedding = [0.1] * 384

        results = await search_knowledge_base(
            db_session,
            query_embedding,
            limit=5,
            min_similarity=0.5,
        )

        assert len(results) >= 1
        # Results should be tuples of (article, similarity_score)
        article, similarity = results[0]
        assert article.id == test_knowledge_article.id
        assert 0.0 <= similarity <= 1.0

    @pytest.mark.asyncio
    async def test_get_knowledge_base_entry(self, db_session: AsyncSession, test_knowledge_article: KnowledgeBase):
        """Test retrieving knowledge base entry by ID."""
        entry = await get_knowledge_base_entry(db_session, test_knowledge_article.id)

        assert entry is not None
        assert entry.id == test_knowledge_article.id

    @pytest.mark.asyncio
    async def test_update_knowledge_base_entry(self, db_session: AsyncSession, test_knowledge_article: KnowledgeBase):
        """Test updating knowledge base entry."""
        new_embedding = [0.2] * 384

        updated = await update_knowledge_base_entry(
            db_session,
            test_knowledge_article.id,
            title="Updated Title",
            embedding=new_embedding,
        )

        assert updated is not None
        assert updated.title == "Updated Title"
        assert updated.embedding[0] == 0.2

    @pytest.mark.asyncio
    async def test_delete_knowledge_base_entry(self, db_session: AsyncSession, test_knowledge_article: KnowledgeBase):
        """Test deleting knowledge base entry."""
        deleted = await delete_knowledge_base_entry(
            db_session, test_knowledge_article.id
        )

        assert deleted is True

        # Verify entry is gone
        entry = await get_knowledge_base_entry(db_session, test_knowledge_article.id)
        assert entry is None
