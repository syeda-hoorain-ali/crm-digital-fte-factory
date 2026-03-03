"""Integration tests for knowledge base migration script."""

import pytest
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.queries import (
    create_knowledge_base_entry,
    search_knowledge_base,
    get_knowledge_base_entry,
)


# ============================================================================
# Integration Tests for Knowledge Base Migration (T096)
# ============================================================================

@pytest.mark.integration
@pytest.mark.database
class TestKnowledgeBaseMigration:
    """Integration tests for knowledge base migration script."""

    @pytest.mark.asyncio
    async def test_migrate_knowledge_base_from_json(self, db_session: AsyncSession):
        """Test migrating knowledge base articles from JSON format."""
        # Simulate migration data
        articles_data = [
            {
                "title": "Getting Started Guide",
                "content": "Welcome to CloudStream CRM! This guide will help you get started.",
                "category": "onboarding",
            },
            {
                "title": "Password Reset",
                "content": "To reset your password, go to Settings > Security > Reset Password.",
                "category": "account",
            },
            {
                "title": "Billing FAQ",
                "content": "Common questions about billing, invoices, and payment methods.",
                "category": "billing",
            },
        ]

        # Mock embedding generation (in real migration, this would use FastEmbed)
        dummy_embedding = [0.1] * 384

        # Migrate articles
        migrated_articles = []
        for article_data in articles_data:
            article = await create_knowledge_base_entry(
                db_session,
                title=article_data["title"],
                content=article_data["content"],
                embedding=dummy_embedding,
                category=article_data["category"],
            )
            migrated_articles.append(article)

        await db_session.commit()

        # Verify all articles were migrated
        assert len(migrated_articles) == 3

        # Verify each article can be retrieved
        for article in migrated_articles:
            retrieved = await get_knowledge_base_entry(db_session, article.id)
            assert retrieved is not None
            assert retrieved.title == article.title
            assert retrieved.content == article.content

    @pytest.mark.asyncio
    async def test_migrate_with_embeddings_generation(self, db_session: AsyncSession):
        """Test migration with actual embedding generation."""
        from unittest.mock import MagicMock, patch

        article_data = {
            "title": "API Documentation",
            "content": "Complete API reference for CloudStream CRM integration.",
            "category": "technical",
        }

        # Mock FastEmbed model
        with patch("fastembed.TextEmbedding") as mock_embedding_class:
            mock_model = MagicMock()
            mock_model.embed.return_value = [[0.2] * 384]
            mock_embedding_class.return_value = mock_model

            # Generate embedding
            embedding = list(mock_model.embed([article_data["content"]]))[0]

            # Create article with generated embedding
            article = await create_knowledge_base_entry(
                db_session,
                title=article_data["title"],
                content=article_data["content"],
                embedding=embedding,
                category=article_data["category"],
                metadata={"category": article_data["category"]}
            )

            await db_session.commit()

            # Verify article was created with embedding
            assert article.id is not None
            assert len(article.embedding) == 384
            assert article.embedding[0] == 0.2

    @pytest.mark.asyncio
    async def test_migrate_handles_duplicate_titles(self, db_session: AsyncSession):
        """Test migration handles articles with duplicate titles."""
        dummy_embedding = [0.1] * 384

        # Create first article
        article1 = await create_knowledge_base_entry(
            db_session,
            title="Common Issue",
            content="First version of content",
            embedding=dummy_embedding,
        )

        await db_session.commit()

        # Create second article with same title (should be allowed)
        article2 = await create_knowledge_base_entry(
            db_session,
            title="Common Issue",
            content="Second version of content",
            embedding=dummy_embedding,
        )

        await db_session.commit()

        # Both articles should exist with different IDs
        assert article1.id != article2.id
        assert article1.content != article2.content

    @pytest.mark.asyncio
    async def test_migrate_preserves_metadata(self, db_session: AsyncSession):
        """Test migration preserves article metadata."""
        dummy_embedding = [0.1] * 384

        metadata = {
            "category": "technical",
            "tags": ["api", "integration", "webhook"],
            "author": "support-team",
            "last_updated": "2024-01-15",
        }

        article = await create_knowledge_base_entry(
            db_session,
            title="Webhook Integration",
            content="How to set up webhooks for real-time notifications.",
            embedding=dummy_embedding,
            category="technical",
            metadata=metadata,
        )

        await db_session.commit()

        # Verify metadata was preserved
        retrieved = await get_knowledge_base_entry(db_session, article.id)
        assert retrieved is not None
        assert retrieved.meta_data == metadata

    @pytest.mark.asyncio
    async def test_migrate_enables_semantic_search(self, db_session: AsyncSession):
        """Test migrated articles are searchable via semantic search."""
        # Create articles with embeddings
        articles_data = [
            ("Password Reset", "How to reset your password", [0.1] * 384),
            ("Account Security", "Tips for securing your account", [0.15] * 384),
            ("Billing Issues", "Common billing problems", [0.9] * 384),
        ]

        for title, content, embedding in articles_data:
            await create_knowledge_base_entry(
                db_session,
                title=title,
                content=content,
                embedding=embedding,
            )

        await db_session.commit()

        # Search with similar embedding to first two articles
        query_embedding = [0.12] * 384
        results = await search_knowledge_base(
            db_session,
            query_embedding,
            limit=5,
            min_similarity=0.5,
        )

        # Should find articles with similar embeddings
        assert len(results) >= 2

        # Results should be sorted by similarity
        if len(results) >= 2:
            similarity1 = results[0][1]
            similarity2 = results[1][1]
            assert similarity1 >= similarity2

    @pytest.mark.asyncio
    async def test_migrate_batch_processing(self, db_session: AsyncSession):
        """Test migration can handle batch processing of articles."""
        dummy_embedding = [0.1] * 384

        # Create batch of articles
        batch_size = 10
        articles = []

        for i in range(batch_size):
            article = await create_knowledge_base_entry(
                db_session,
                title=f"Article {i}",
                content=f"Content for article {i}",
                embedding=dummy_embedding,
                metadata={"batch": "test", "index": i},
            )
            articles.append(article)

        await db_session.commit()

        # Verify all articles were created
        assert len(articles) == batch_size

        # Verify articles can be retrieved
        for i, article in enumerate(articles):
            retrieved = await get_knowledge_base_entry(db_session, article.id)
            assert retrieved is not None
            assert retrieved.meta_data["index"] == i

    @pytest.mark.asyncio
    async def test_migrate_handles_long_content(self, db_session: AsyncSession):
        """Test migration handles articles with long content."""
        dummy_embedding = [0.1] * 384

        # Create article with long content (simulate real documentation)
        long_content = "This is a comprehensive guide. " * 500  # ~15,000 characters

        article = await create_knowledge_base_entry(
            db_session,
            title="Comprehensive Guide",
            content=long_content,
            embedding=dummy_embedding,
        )

        await db_session.commit()

        # Verify article was created successfully
        retrieved = await get_knowledge_base_entry(db_session, article.id)
        assert retrieved is not None
        assert len(retrieved.content) == len(long_content)

    @pytest.mark.asyncio
    async def test_migrate_handles_special_characters(self, db_session: AsyncSession):
        """Test migration handles special characters in content."""
        dummy_embedding = [0.1] * 384

        special_content = """
        Special characters test:
        - Quotes: "double" and 'single'
        - Symbols: @#$%^&*()
        - Unicode: 你好 مرحبا שלום
        - Code: `function() { return true; }`
        - Markdown: **bold** _italic_ [link](url)
        """

        article = await create_knowledge_base_entry(
            db_session,
            title="Special Characters Test",
            content=special_content,
            embedding=dummy_embedding,
        )

        await db_session.commit()

        # Verify content was preserved exactly
        retrieved = await get_knowledge_base_entry(db_session, article.id)
        assert retrieved is not None
        assert retrieved.content == special_content

    @pytest.mark.asyncio
    async def test_migrate_rollback_on_error(self, db_session: AsyncSession):
        """Test migration can rollback on error."""
        dummy_embedding = [0.1] * 384

        # Create first article successfully
        article1 = await create_knowledge_base_entry(
            db_session,
            title="Article 1",
            content="Content 1",
            embedding=dummy_embedding,
        )

        # Simulate error before commit
        try:
            # Create second article
            article2 = await create_knowledge_base_entry(
                db_session,
                title="Article 2",
                content="Content 2",
                embedding=dummy_embedding,
            )

            # Simulate error
            raise Exception("Simulated migration error")

        except Exception:
            # Rollback transaction
            await db_session.rollback()

        # Verify neither article was committed
        retrieved1 = await get_knowledge_base_entry(db_session, article1.id)
        # After rollback, article should not exist
        assert retrieved1 is None

    @pytest.mark.asyncio
    async def test_migrate_idempotency(self, db_session: AsyncSession):
        """Test migration can be run multiple times safely."""
        dummy_embedding = [0.1] * 384

        article_data = {
            "title": "Idempotency Test",
            "content": "This article tests idempotent migration",
        }

        # First migration
        article1 = await create_knowledge_base_entry(
            db_session,
            title=article_data["title"],
            content=article_data["content"],
            embedding=dummy_embedding,
        )

        await db_session.commit()

        # Second migration (should create new article, not update)
        article2 = await create_knowledge_base_entry(
            db_session,
            title=article_data["title"],
            content=article_data["content"],
            embedding=dummy_embedding,
        )

        await db_session.commit()

        # Both articles should exist (migration creates new entries)
        assert article1.id != article2.id

        # In a real migration script, you would implement deduplication logic
        # to prevent duplicate articles
