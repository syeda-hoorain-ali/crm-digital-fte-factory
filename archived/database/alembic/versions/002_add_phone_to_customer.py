"""add phone column to customer table

Revision ID: 002
Revises: 001
Create Date: 2026-02-19 14:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add phone column to customer table (nullable to support existing records)
    op.add_column('customer', sa.Column('phone', sa.String(length=50), nullable=True))

    # Create index for phone lookups (improves query performance)
    op.create_index('idx_customer_phone', 'customer', ['phone'], unique=False)

    # Create index for email lookups (improves query performance)
    op.create_index('idx_customer_email', 'customer', ['email'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_customer_email', table_name='customer')
    op.drop_index('idx_customer_phone', table_name='customer')

    # Drop phone column
    op.drop_column('customer', 'phone')