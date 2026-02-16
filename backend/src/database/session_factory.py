"""
Database Session Factory for the Backend
Creates appropriate session types based on environment settings
"""
from typing import Union
from agents.memory import SQLiteSession
from agents.extensions.memory import SQLAlchemySession
from src.settings import get_settings


def create_session(customer_identifier: str) -> Union[SQLiteSession, SQLAlchemySession]:
    """
    Create an appropriate session based on the environment and database configuration

    Args:
        customer_identifier: Unique identifier for the customer/conversation

    Returns:
        Appropriate session type based on environment and configuration
    """
    settings = get_settings()

    if settings.environment == "testing":
        # In testing mode, use mock data and SQLiteSession for conversation history
        return SQLiteSession(f"customer_{customer_identifier}")
    elif settings.environment == "production":
        # In production, always use SQLAlchemySession with the configured database
        if not settings.database_url:
            raise ValueError("database_url is required in production environment")

        # Create SQLAlchemy session with the configured database URL
        return SQLAlchemySession.from_url(
            session_id=f"customer_{customer_identifier}",
            url=settings.database_url,
            create_tables=True  # Auto-create tables in production (consider using migrations in real deployment)
        )
    elif settings.environment == "development":
        # In development mode:
        # - If database_url is set, use SQLAlchemySession
        # - If database_url is not set, use SQLiteSession
        if settings.database_url and not settings.database_url.startswith("sqlite://"):
            # Use SQLAlchemy session with the provided database URL
            return SQLAlchemySession.from_url(
                session_id=f"customer_{customer_identifier}",
                url=settings.database_url,
                create_tables=True
            )
        else:
            # Use SQLite session for development convenience
            return SQLiteSession(f"customer_{customer_identifier}")
    else:
        # Default to SQLite for unknown environments
        return SQLiteSession(f"customer_{customer_identifier}")