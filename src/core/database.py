"""Database configuration and session management."""

from sqlmodel import SQLModel, create_engine, Session
from .models import *

sqlite_file_name = "software_house.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=False)


def init_db():
    """Initialize database with all tables."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Get a new database session (generator for dependency injection)."""
    with Session(engine) as session:
        yield session


def get_session_direct():
    """Get a database session directly (for non-async contexts)."""
    return Session(engine)
