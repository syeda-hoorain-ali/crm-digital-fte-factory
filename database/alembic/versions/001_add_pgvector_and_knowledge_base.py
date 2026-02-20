"""add pgvector extension and all CRM database tables

Revision ID: 001
Revises:
Create Date: 2026-02-17 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create pgvector extension
    op.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    # Create knowledge_base table
    op.create_table('knowledge_base',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('content', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('embedding', Vector(384), nullable=True),  # pgvector type with 384 dimensions
        sa.Column('relevance_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )

    # Note: IVFFLAT index removed - it doesn't work well with small datasets (< 1000 rows)
    # For production with larger datasets, consider adding:
    # op.execute(text("CREATE INDEX IF NOT EXISTS idx_knowledge_base_embedding ON knowledge_base USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);"))
    # Or use HNSW index for better performance:
    # op.execute(text("CREATE INDEX IF NOT EXISTS idx_knowledge_base_embedding ON knowledge_base USING hnsw (embedding vector_cosine_ops);"))

    # Create customer table
    op.create_table('customer',
        sa.Column('customer_id', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('plan_type', sa.String(), nullable=True),
        sa.Column('subscription_status', sa.String(), nullable=True),
        sa.Column('last_interaction', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('customer_id')
    )

    # Create support_ticket table
    op.create_table('support_ticket',
        sa.Column('ticket_id', sa.String(), nullable=False),
        sa.Column('customer_id', sa.String(), nullable=False),
        sa.Column('channel', sa.String(), nullable=True),
        sa.Column('query', sa.String(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('escalated', sa.Boolean(), nullable=True),
        sa.Column('escalation_reason', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['customer_id'], ['customer.customer_id'], ),
        sa.PrimaryKeyConstraint('ticket_id')
    )

    # Create escalation_record table
    op.create_table('escalation_record',
        sa.Column('escalation_id', sa.String(), nullable=False),
        sa.Column('ticket_id', sa.String(), nullable=True),
        sa.Column('reason', sa.String(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['ticket_id'], ['support_ticket.ticket_id'], ),
        sa.PrimaryKeyConstraint('escalation_id')
    )


def downgrade() -> None:
    # Drop escalation_record table
    op.drop_table('escalation_record')

    # Drop support_ticket table
    op.drop_table('support_ticket')

    # Drop customer table
    op.drop_table('customer')

    # Drop the knowledge_base table and index
    op.execute(text("DROP INDEX IF EXISTS idx_knowledge_base_embedding"))
    op.drop_table('knowledge_base')

    # Drop pgvector extension (be careful with this in production)
    # op.execute(text("DROP EXTENSION IF EXISTS vector"))
