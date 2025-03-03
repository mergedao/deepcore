from contextlib import asynccontextmanager
from urllib.parse import quote

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker

from agents.common.config import SETTINGS
from agents.models.models import Base

DATABASE_URL = f"mysql+aiomysql://{SETTINGS.MYSQL_USER}:{quote(SETTINGS.MYSQL_PASSWORD)}@{SETTINGS.MYSQL_HOST}:{SETTINGS.MYSQL_PORT}/{SETTINGS.MYSQL_DB}"

# Configure database connection pool
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to False in production environment
    pool_size=10,  # Reduce pool size to avoid too many connections
    max_overflow=20,  # Reduce maximum overflow connections
    pool_timeout=30,  # Timeout for getting connections
    pool_recycle=1800,  # Connection recycle time to avoid using expired connections
    pool_pre_ping=True,  # Test connection validity before use
    # Set connection parameters
    connect_args={
        "charset": "utf8mb4",
        "use_unicode": True,
        "connect_timeout": 10  # Connection timeout in seconds
    }
)

# Create session factory
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Avoid reloading objects after commit
    autocommit=False,
    autoflush=False
)

@asynccontextmanager
async def get_session():
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()

async def get_db():
    """Dependency for providing database session for each request."""
    session = None
    try:
        session = SessionLocal()
        yield session
        await session.commit()
    except Exception:
        if session:
            await session.rollback()
        raise
    finally:
        if session:
            await session.close()

async def init_db(engine: AsyncEngine):
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def dispose_engine():
    """Properly dispose of the engine and its connection pool."""
    try:
        await engine.dispose()
    except Exception as e:
        logger.error(f"Error disposing database engine: {str(e)}", exc_info=True)

# Initialize database on application startup
if __name__ == '__main__':
    import asyncio
    import logging
    
    logger = logging.getLogger(__name__)
    
    async def init():
        try:
            await init_db(engine)
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}", exc_info=True)
        finally:
            await dispose_engine()
    
    asyncio.run(init())
