"""Unit tests for knowledge base database queries."""

import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import KnowledgeBase
from src.database.queries.knowledge_base import (
    create_knowledge_base_entry,
    get_knowledge_base_entry,
    update_knowledge_base_entry,
    delete_knowledge_base_entry,
)


@pytest.mark.unit
@pytest.mark.asyncio
class TestKnowledgeBaseCRUD:
    """Test knowledge base CRUD operations."""

    async def test_create_knowledge_base_entry_minimal(self, session: AsyncSession):
        """Test creating knowledge base entry with minimal fields."""
        embedding = [0.1] * 384  # 384-dimensional embedding

        entry = await create_knowledge_base_entry(
            session,
            title="How to reset password",
            content="To reset your password, click on 'Forgot Password' link...",
            embedding=embedding
        )

        print(entry)

        assert entry.id is not None
        assert entry.title == "How to reset password"
        assert entry.content == "To reset your password, click on 'Forgot Password' link..."
        assert entry.embedding == pytest.approx(embedding)
        assert entry.category is None
        assert entry.metadata_ == {}

    async def test_create_knowledge_base_entry_full(self, session: AsyncSession):
        """Test creating knowledge base entry with all fields."""
        embedding = [0.2] * 384
        metadata = {"source": "documentation", "version": "2.0"}

        entry = await create_knowledge_base_entry(
            session,
            title="API Authentication",
            content="Our API uses OAuth 2.0 for authentication...",
            embedding=embedding,
            category="api",
            metadata=metadata
        )

        assert entry.id is not None
        assert entry.title == "API Authentication"
        assert entry.category == "api"
        assert entry.metadata_ == metadata

    async def test_create_knowledge_base_entry_different_categories(self, session: AsyncSession):
        """Test creating entries with different categories."""
        embedding = [0.1] * 384

        billing_entry = await create_knowledge_base_entry(
            session,
            "Billing FAQ",
            "Common billing questions...",
            embedding,
            category="billing"
        )

        technical_entry = await create_knowledge_base_entry(
            session,
            "Technical Guide",
            "Technical documentation...",
            embedding,
            category="technical"
        )

        account_entry = await create_knowledge_base_entry(
            session,
            "Account Management",
            "How to manage your account...",
            embedding,
            category="account"
        )

        assert billing_entry.category == "billing"
        assert technical_entry.category == "technical"
        assert account_entry.category == "account"

    async def test_get_knowledge_base_entry_exists(self, session: AsyncSession):
        """Test getting existing knowledge base entry."""
        embedding = [0.1] * 384
        created_entry = await create_knowledge_base_entry(
            session,
            "Test Entry",
            "Test content",
            embedding,
            category="test"
        )
        await session.commit()

        entry = await get_knowledge_base_entry(session, created_entry.id)

        assert entry is not None
        assert entry.id == created_entry.id
        assert entry.title == "Test Entry"
        assert entry.category == "test"

    async def test_get_knowledge_base_entry_not_exists(self, session: AsyncSession):
        """Test getting non-existent knowledge base entry."""
        fake_id = uuid4()
        entry = await get_knowledge_base_entry(session, fake_id)

        assert entry is None

    async def test_update_knowledge_base_entry_title(self, session: AsyncSession):
        """Test updating knowledge base entry title."""
        embedding = [0.1] * 384
        entry = await create_knowledge_base_entry(
            session,
            "Original Title",
            "Content",
            embedding
        )
        await session.commit()

        updated = await update_knowledge_base_entry(
            session,
            entry.id,
            title="Updated Title"
        )

        assert updated is not None
        assert updated.title == "Updated Title"
        assert updated.content == "Content"  # Unchanged

    async def test_update_knowledge_base_entry_content(self, session: AsyncSession):
        """Test updating knowledge base entry content."""
        embedding = [0.1] * 384
        entry = await create_knowledge_base_entry(
            session,
            "Title",
            "Original content",
            embedding
        )
        await session.commit()

        updated = await update_knowledge_base_entry(
            session,
            entry.id,
            content="Updated content with more details"
        )

        assert updated is not None
        assert updated.content == "Updated content with more details"
        assert updated.title == "Title"  # Unchanged

    async def test_update_knowledge_base_entry_embedding(self, session: AsyncSession):
        """Test updating knowledge base entry embedding."""
        original_embedding = [0.1] * 384
        new_embedding = [0.5] * 384

        entry = await create_knowledge_base_entry(
            session,
            "Title",
            "Content",
            original_embedding
        )
        await session.commit()

        updated = await update_knowledge_base_entry(
            session,
            entry.id,
            embedding=new_embedding
        )

        assert updated is not None
        assert updated.embedding == pytest.approx(new_embedding)

    async def test_update_knowledge_base_entry_metadata(self, session: AsyncSession):
        """Test updating knowledge base entry metadata."""
        embedding = [0.1] * 384
        original_metadata = {"version": "1.0"}
        new_metadata = {"version": "2.0", "author": "John Doe"}

        entry = await create_knowledge_base_entry(
            session,
            "Title",
            "Content",
            embedding,
            metadata=original_metadata
        )
        await session.commit()

        updated = await update_knowledge_base_entry(
            session,
            entry.id,
            metadata=new_metadata
        )

        assert updated is not None
        assert updated.metadata_ == new_metadata

    async def test_update_knowledge_base_entry_multiple_fields(self, session: AsyncSession):
        """Test updating multiple fields at once."""
        original_embedding = [0.1] * 384
        new_embedding = [0.5] * 384
        new_metadata = {"updated": True}

        entry = await create_knowledge_base_entry(
            session,
            "Original Title",
            "Original content",
            original_embedding
        )
        await session.commit()

        updated = await update_knowledge_base_entry(
            session,
            entry.id,
            title="New Title",
            content="New content",
            embedding=new_embedding,
            metadata=new_metadata
        )

        assert updated is not None
        assert updated.title == "New Title"
        assert updated.content == "New content"
        assert updated.embedding == pytest.approx(new_embedding)
        assert updated.metadata_ == new_metadata

    async def test_update_knowledge_base_entry_not_exists(self, session: AsyncSession):
        """Test updating non-existent knowledge base entry."""
        fake_id = uuid4()
        updated = await update_knowledge_base_entry(
            session,
            fake_id,
            title="Test"
        )

        assert updated is None

    async def test_delete_knowledge_base_entry_exists(self, session: AsyncSession):
        """Test deleting existing knowledge base entry."""
        embedding = [0.1] * 384
        entry = await create_knowledge_base_entry(
            session,
            "Entry to delete",
            "Content",
            embedding
        )
        await session.commit()

        result = await delete_knowledge_base_entry(session, entry.id)

        assert result is True

        # Verify entry is deleted
        deleted_entry = await get_knowledge_base_entry(session, entry.id)
        assert deleted_entry is None

    async def test_delete_knowledge_base_entry_not_exists(self, session: AsyncSession):
        """Test deleting non-existent knowledge base entry."""
        fake_id = uuid4()
        result = await delete_knowledge_base_entry(session, fake_id)

        assert result is False

    async def test_create_multiple_entries_different_embeddings(self, session: AsyncSession):
        """Test creating multiple entries with different embeddings."""
        embedding1 = [0.1] * 384
        embedding2 = [0.5] * 384
        embedding3 = [0.9] * 384

        entry1 = await create_knowledge_base_entry(
            session,
            "Entry 1",
            "Content 1",
            embedding1
        )

        entry2 = await create_knowledge_base_entry(
            session,
            "Entry 2",
            "Content 2",
            embedding2
        )

        entry3 = await create_knowledge_base_entry(
            session,
            "Entry 3",
            "Content 3",
            embedding3
        )

        await session.commit()

        assert entry1.embedding == pytest.approx(embedding1)
        assert entry2.embedding == pytest.approx(embedding2)
        assert entry3.embedding == pytest.approx(embedding3)

    async def test_knowledge_base_entry_timestamps(self, session: AsyncSession):
        """Test that timestamps are set correctly."""
        embedding = [0.1] * 384
        entry = await create_knowledge_base_entry(
            session,
            "Test Entry",
            "Content",
            embedding
        )
        await session.commit()

        assert entry.created_at is not None
        assert entry.updated_at is not None

        # Capture before update mutates the object
        original_updated_at = entry.updated_at

        # Update entry
        updated = await update_knowledge_base_entry(
            session,
            entry.id,
            title="Updated Title"
        )

        assert updated is not None
        assert updated.updated_at > original_updated_at

    async def test_create_entry_with_empty_metadata(self, session: AsyncSession):
        """Test creating entry with empty metadata dict."""
        embedding = [0.1] * 384
        entry = await create_knowledge_base_entry(
            session,
            "Title",
            "Content",
            embedding,
            metadata={}
        )

        assert entry.metadata_ == {}

    async def test_create_entry_with_complex_metadata(self, session: AsyncSession):
        """Test creating entry with complex metadata structure."""
        embedding = [0.1] * 384
        complex_metadata = {
            "source": "documentation",
            "version": "2.0",
            "tags": ["api", "authentication", "oauth"],
            "related_articles": ["article-1", "article-2"],
            "difficulty": "intermediate"
        }

        entry = await create_knowledge_base_entry(
            session,
            "Complex Entry",
            "Content",
            embedding,
            metadata=complex_metadata
        )

        assert entry.metadata_ == complex_metadata
        assert entry.metadata_["tags"] == ["api", "authentication", "oauth"]
        assert entry.metadata_["difficulty"] == "intermediate"
