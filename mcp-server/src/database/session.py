from sqlmodel import create_engine, Session
from typing import Generator
from src.config import settings


# In production, use a connection string from environment variables
connect_args = {"check_same_thread": False}  # Needed for SQLite
engine = create_engine(settings.database_url, connect_args=connect_args)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
