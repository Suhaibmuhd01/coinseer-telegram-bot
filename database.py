"""Legacy database compatibility bridge."""
from app.core.database import Base, engine, async_session_factory, get_db_session, init_db

__all__ = ["Base", "engine", "async_session_factory", "get_db_session", "init_db"]