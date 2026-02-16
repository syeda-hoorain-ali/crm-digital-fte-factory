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
    database_url = settings.database_url

    if settings.environment == "testing":
        # In testing mode, use mock data and SQLiteSession for conversation history
        return SQLiteSession(f"customer_{customer_identifier}")
    elif settings.environment == "production":
        # In production, always use SQLAlchemySession with the configured database
        if not database_url:
            raise ValueError("database_url is required in production environment")

        # Create SQLAlchemy session with the configured database URL
        return SQLAlchemySession.from_url(
            session_id=f"customer_{customer_identifier}",
            url=database_url,
            create_tables=False  # Disable auto-create tables; use Alembic migrations instead
        )
    elif settings.environment == "development":
        # In development mode:
        # - If database_url is set, use SQLAlchemySession
        # - If database_url is not set, use SQLiteSession
        if database_url and not database_url.startswith("sqlite://"):
            # Use SQLAlchemy session with the provided database URL
            return SQLAlchemySession.from_url(
                session_id=f"customer_{customer_identifier}",
                url=database_url,
                create_tables=False  # Disable auto-create tables; use Alembic migrations instead
            )
        else:
            # Use SQLite session for development convenience
            return SQLiteSession(f"customer_{customer_identifier}", database_url.removeprefix("sqlite://"))
    else:
        # Default to SQLite for unknown environments
        return SQLiteSession(f"customer_{customer_identifier}")
