"""Async SQLAlchemy engine with connection pooling."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from contextlib import asynccontextmanager
from .config import settings
import structlog

logger = structlog.get_logger()
Base = declarative_base()


def _normalize_db_url(url: str) -> str:
    """Render отдаёт postgres:// или postgresql://, asyncpg-драйверу нужен postgresql+asyncpg://"""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    return url


DATABASE_URL = _normalize_db_url(str(settings.DATABASE_URL))

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_timeout=30,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

@asynccontextmanager
async def get_db_session():
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error("Database transaction failed", error=str(e))
        raise
    finally:
        await session.close()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")

async def close_db():
    await engine.dispose()
    logger.info("Database connections closed")
