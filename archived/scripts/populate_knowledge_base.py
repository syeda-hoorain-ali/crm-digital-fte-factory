#!/usr/bin/env python3
"""
Script to populate the knowledge base with documentation from context files.
"""

import os
import sys
import re
from pathlib import Path

sys.path.insert(0, '../mcp-server')

import yaml
from sqlmodel import Session
from src.database.session import engine
from src.database.models import KnowledgeBaseEntry
from src.utils.embeddings import generate_embedding


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """
    Parse YAML frontmatter from markdown content.

    Returns:
        tuple: (frontmatter_dict, content_without_frontmatter)
    """
    # Match YAML frontmatter pattern: ---\n...\n---
    frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
    match = re.match(frontmatter_pattern, content, re.DOTALL)

    if not match:
        return {}, content

    try:
        frontmatter = yaml.safe_load(match.group(1))
        content_body = match.group(2)
        return frontmatter or {}, content_body
    except yaml.YAMLError as e:
        print(f"Warning: Failed to parse YAML frontmatter: {e}")
        return {}, content


def load_documents_from_context():
    """Load all markdown documents from the context folder."""
    context_dir = Path(__file__).parent.parent / 'context'

    if not context_dir.exists():
        raise FileNotFoundError(f"Context directory not found: {context_dir}")

    documents = []

    # Read all markdown files from context folder
    for file_path in context_dir.glob('*.md'):
        filename = file_path.name

        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse frontmatter
        frontmatter, content_body = parse_frontmatter(content)

        # Validate required fields
        if 'category' not in frontmatter:
            print(f"Skipping {filename} - missing 'category' in frontmatter")
            continue

        # Extract title from frontmatter or first markdown header
        if 'title' in frontmatter:
            title = frontmatter['title']
        elif content_body.strip().startswith('#'):
            title = content_body.split('\n')[0].strip('#').strip()
        else:
            title = filename.replace('.md', '').replace('-', ' ').title()

        documents.append({
            'title': title,
            'content': content_body.strip(),
            'category': frontmatter['category'],
            'source_file': filename,
            'metadata': frontmatter
        })

    return documents

def populate_knowledge_base():
    """Populate the knowledge base with documents from context folder."""
    print("Loading documents from context folder...")

    try:
        documentation_content = load_documents_from_context()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    if not documentation_content:
        print("No documents found to populate.")
        return

    print(f"Found {len(documentation_content)} documents to add.")
    print("Populating knowledge base with documentation...")

    with Session(engine) as session:
        # Add documentation content to the knowledge base
        for doc in documentation_content:
            print(f"Adding: {doc['title']} (from {doc['source_file']})")

            # Generate embedding for the content
            content_embedding = generate_embedding(doc['content'])

            # Create the knowledge base entry
            knowledge_entry = KnowledgeBaseEntry(
                title=doc['title'],
                content=doc['content'],
                category=doc['category'],
                embedding=content_embedding
            )

            session.add(knowledge_entry)

        session.commit()
        print(f"Successfully added {len(documentation_content)} knowledge base entries.")

if __name__ == "__main__":
    populate_knowledge_base()
