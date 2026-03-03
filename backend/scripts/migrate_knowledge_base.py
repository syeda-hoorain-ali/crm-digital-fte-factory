"""Knowledge base migration script with FastEmbed integration.

This script reads markdown files from a specified directory, generates embeddings
using FastEmbed (all-MiniLM-L6-v2 model), and inserts them into the knowledge_base table.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

# Set dummy OpenAI API key if not set (migration doesn't need it)
if not os.getenv("OPENAI_API_KEY") or not os.getenv("OPENAI_API_KEY").startswith("sk-"):
    os.environ["OPENAI_API_KEY"] = "sk-proj-dummy-key-for-migration-script-only"

from fastembed import TextEmbedding

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection import get_session
from src.database.models import KnowledgeBase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def extract_title(content: str) -> str:
    """
    Extract title from the first # heading in markdown content.

    Args:
        content: Markdown file content

    Returns:
        Extracted title or "Untitled" if no heading found
    """
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith('# '):
            return line[2:].strip()
    return "Untitled"


def extract_category(md_file: Path) -> str:
    """
    Extract category from markdown frontmatter or parent directory name.

    Args:
        md_file: Path to markdown file

    Returns:
        Category name
    """
    content = md_file.read_text(encoding='utf-8')

    # Try to extract from frontmatter
    if content.startswith('---'):
        lines = content.split('\n')
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == '---':
                break
            if line.startswith('category:'):
                category = line.split(':', 1)[1].strip()
                return category.strip('"\'')

    # Fallback to parent directory name
    return md_file.parent.name


async def migrate_knowledge_base(directory: str, batch_size: int = 10) -> None:
    """
    Migrate markdown files to knowledge base with embeddings.

    Args:
        directory: Path to directory containing markdown files
        batch_size: Number of files to process in each batch
    """
    directory_path = Path(directory)

    if not directory_path.exists():
        logger.error(f"Directory not found: {directory}")
        return

    # Find all markdown files
    md_files = list(directory_path.glob("**/*.md"))

    if not md_files:
        logger.warning(f"No markdown files found in {directory}")
        return

    logger.info(f"Found {len(md_files)} markdown files to process")

    # Initialize FastEmbed model
    logger.info("Initializing FastEmbed model (all-MiniLM-L6-v2)...")
    model = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
    logger.info("Model initialized successfully")

    # Process files in batches
    total_inserted = 0
    total_failed = 0

    for i in range(0, len(md_files), batch_size):
        batch = md_files[i:i + batch_size]
        logger.info(f"Processing batch {i // batch_size + 1} ({len(batch)} files)...")

        async with get_session() as session:
            for md_file in batch:
                try:
                    # Read file content
                    content = md_file.read_text(encoding='utf-8')

                    # Extract title and category
                    title = extract_title(content)
                    category = extract_category(md_file)

                    # Generate embedding
                    logger.info(f"Generating embedding for: {md_file.name}")
                    embeddings = list(model.embed([content]))
                    embedding = embeddings[0].tolist()

                    # Verify embedding dimension
                    if len(embedding) != 384:
                        logger.error(
                            f"Invalid embedding dimension for {md_file.name}: "
                            f"expected 384, got {len(embedding)}"
                        )
                        total_failed += 1
                        continue

                    # Create knowledge base entry
                    kb = KnowledgeBase(
                        title=title,
                        content=content,
                        category=category,
                        embedding=embedding
                    )

                    session.add(kb)
                    logger.info(
                        f"✓ Added: {title[:50]}... (category: {category}, "
                        f"content length: {len(content)} chars)"
                    )
                    total_inserted += 1

                except Exception as e:
                    logger.error(f"Failed to process {md_file.name}: {e}")
                    total_failed += 1

            # Commit batch
            try:
                await session.commit()
                logger.info(f"Batch committed successfully")
            except Exception as e:
                logger.error(f"Failed to commit batch: {e}")
                await session.rollback()

    # Summary
    logger.info("=" * 60)
    logger.info("Migration Summary:")
    logger.info(f"  Total files found: {len(md_files)}")
    logger.info(f"  Successfully inserted: {total_inserted}")
    logger.info(f"  Failed: {total_failed}")
    logger.info("=" * 60)


async def test_vector_search(query: str, limit: int = 3) -> None:
    """
    Test vector similarity search on knowledge base.

    Args:
        query: Search query text
        limit: Maximum number of results to return
    """
    logger.info(f"Testing vector search with query: '{query}'")

    # Initialize model
    model = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # Generate query embedding
    query_embeddings = list(model.embed([query]))
    query_embedding = query_embeddings[0].tolist()

    # Search database
    async with get_session() as session:
        from sqlalchemy import text, select, func
        from sqlalchemy.sql import cast

        # Use SQLAlchemy ORM for vector search
        # The <=> operator calculates cosine distance
        stmt = (
            select(
                KnowledgeBase.id,
                KnowledgeBase.title,
                KnowledgeBase.category,
                KnowledgeBase.embedding.cosine_distance(query_embedding).label('distance')
            )
            .order_by(KnowledgeBase.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )

        result = await session.execute(stmt)

        rows = result.fetchall()

        if not rows:
            logger.warning("No results found")
            return

        logger.info(f"Found {len(rows)} results:")
        for idx, row in enumerate(rows, 1):
            logger.info(
                f"  {idx}. {row.title} (category: {row.category}, "
                f"distance: {row.distance:.4f})"
            )


async def main():
    """Main entry point for the migration script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate markdown files to knowledge base with embeddings"
    )
    parser.add_argument(
        "directory",
        help="Directory containing markdown files"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of files to process in each batch (default: 10)"
    )
    parser.add_argument(
        "--test-query",
        help="Test vector search with a query after migration"
    )

    args = parser.parse_args()

    # Run migration
    await migrate_knowledge_base(args.directory, args.batch_size)

    # Run test query if provided
    if args.test_query:
        logger.info("\n" + "=" * 60)
        await test_vector_search(args.test_query)


if __name__ == "__main__":
    asyncio.run(main())
