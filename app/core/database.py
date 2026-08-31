from typing import AsyncGenerator
import asyncio
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncEngine,
)
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings
from app.core.logging import logger


class Base(DeclarativeBase):
    pass


def _create_engine(url: str) -> AsyncEngine:
    if "sqlite" in url:
        return create_async_engine(url, echo=settings.DEBUG)
    return create_async_engine(
        url,
        echo=settings.DEBUG,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_recycle=settings.DB_POOL_RECYCLE_SECS,
        pool_pre_ping=True,
        connect_args={"command_timeout": 3, "timeout": 3},
    )


engine: AsyncEngine = _create_engine(settings.DATABASE_URL)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables with automatic local fallback."""
    global engine, async_session_factory
    try:
        async with engine.begin() as conn:
            import app.models  # noqa: F401
            await conn.run_sync(Base.metadata.create_all)
        logger.info("database_initialized_successfully", url=str(engine.url.render_as_string(hide_password=True)))
    except Exception as e:
        logger.warning("primary_database_unavailable_attempting_sqlite_fallback", error=str(e))
        # Fallback to local SQLite database for instant local development
        fallback_url = "sqlite+aiosqlite:///./coinseer_bot.db"
        engine = _create_engine(fallback_url)
        async_session_factory.configure(bind=engine)
        async with engine.begin() as conn:
            import app.models  # noqa: F401
            await conn.run_sync(Base.metadata.create_all)
        logger.info("sqlite_fallback_initialized_successfully", url=fallback_url)

