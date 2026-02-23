from sqlmodel import create_engine, Session
from typing import Generator
from src.config import settings
import logging

logger = logging.getLogger(__name__)


def create_db_engine():
    """Create database engine with appropriate settings based on database type."""
    # PostgreSQL-specific connection arguments for engine creation
    engine_kwargs = {
        "pool_size": 20,
        "max_overflow": 30,
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
    logger.info("Using PostgreSQL engine configuration")

    return create_engine(settings.database_url, **engine_kwargs)


# Create the engine with appropriate settings
engine = create_db_engine()


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
