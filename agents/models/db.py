import asyncio
import logging
from contextlib import asynccontextmanager
from urllib.parse import quote

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker

from agents.common.config import SETTINGS
from agents.models.models import Base

logger = logging.getLogger(__name__)

DATABASE_URL = f"mysql+aiomysql://{SETTINGS.MYSQL_USER}:{quote(SETTINGS.MYSQL_PASSWORD)}@{SETTINGS.MYSQL_HOST}:{SETTINGS.MYSQL_PORT}/{SETTINGS.MYSQL_DB}"

# Configure database connection pool
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to False in production environment
    pool_size=10,  # Reduce pool size to avoid too many connections
    max_overflow=20,  # Reduce maximum overflow connections
    pool_timeout=30,  # Timeout for getting connections
    pool_recycle=600,  # Reduced recycle time from 1800s to 600s (10 minutes)
    pool_pre_ping=True,  # Test connection validity before use
    # Set connection parameters
    connect_args={
        "charset": "utf8mb4",
        "use_unicode": True,
        "connect_timeout": 10  # Connection timeout in seconds
        # Removed read_timeout and write_timeout as they're not supported by aiomysql
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
    start_time = asyncio.get_event_loop().time()
    transaction_timeout = 60  # Set transaction timeout to 60 seconds
    
    try:
        yield session
        
        # Check if transaction took too long
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed > transaction_timeout:
            logger.warning(f"Transaction took too long: {elapsed:.2f}s, consider optimizing")
            
        await session.commit()
        
    except Exception as e:
        logger.error(f"Database error in transaction: {str(e)}", exc_info=True)
        await session.rollback()
        raise
    finally:
        await session.close()
        logger.debug(f"Session closed after {asyncio.get_event_loop().time() - start_time:.2f}s")

async def get_db():
    """Dependency for providing database session for each request."""
    session = None
    start_time = asyncio.get_event_loop().time()
    request_timeout = 30  # Set database operation timeout to 30 seconds
    
    try:
        session = SessionLocal()
        yield session
        
        # Check if request took too long
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed > request_timeout:
            logger.warning(f"Database operation took too long: {elapsed:.2f}s")
            
        await session.commit()
        
    except Exception as e:
        logger.error(f"Database error in request: {str(e)}", exc_info=True)
        if session:
            await session.rollback()
        raise
    finally:
        if session:
            await session.close()
            logger.debug(f"Request DB session closed after {asyncio.get_event_loop().time() - start_time:.2f}s")

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
    async def init():
        try:
            await init_db(engine)
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}", exc_info=True)
        finally:
            await dispose_engine()
    
    asyncio.run(init())
