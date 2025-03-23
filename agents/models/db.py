import asyncio
import logging
from contextlib import asynccontextmanager
from urllib.parse import quote
import time

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
    pool_size=20,  # Increased pool size from 10 to 20
    max_overflow=30,  # Increased max overflow connections from 20 to 30
    pool_timeout=30,  # Timeout for getting connections (unchanged)
    pool_recycle=300,  # Reduced connection recycling time from 600s to 300s (5 minutes)
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

def get_async_engine() -> AsyncEngine:
    """
    Get the async database engine instance
    
    Returns:
        AsyncEngine: The async SQLAlchemy engine
    """
    return engine

@asynccontextmanager
async def get_session():
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    start_time = asyncio.get_event_loop().time()
    transaction_timeout = 45  # Reduced transaction timeout from 60s to 45s
    
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

async def get_pool_status():
    """
    Get database connection pool status information
    
    Returns a dictionary containing pool size, current connections in use, etc.
    
    Returns:
        dict: Connection pool status information
    """
    # Get connection pool status
    pool = engine.pool
    
    try:
        # Create a basic info dictionary with the pool type
        pool_info = {
            "pool_type": f"{pool.__class__.__name__}"
        }
        
        # Try to directly get pool configuration parameters
        # Handle case where attributes might be methods
        for attr in ["size", "max_overflow", "timeout", "recycle", "pre_ping"]:
            if hasattr(pool, attr):
                attr_value = getattr(pool, attr)
                # Check if attribute is a callable and not a class
                if callable(attr_value) and not isinstance(attr_value, type):
                    try:
                        # Try to call the method to get the actual value
                        pool_info[attr] = attr_value()
                    except Exception as method_err:
                        logger.debug(f"Could not call {attr} method: {str(method_err)}")
                else:
                    pool_info[attr] = attr_value
        
        # Try to access raw pool statistics - using a more defensive approach
        try:
            # Get current usage statistics using SQLAlchemy internal methods
            if hasattr(pool, "_pool"):
                # For AsyncAdaptedQueuePool, get statistics via QueuePool methods
                raw_pool = pool._pool
                
                # Try different methods to get checked out connections
                if hasattr(raw_pool, "checkedout"):
                    checked_out_attr = getattr(raw_pool, "checkedout")
                    if callable(checked_out_attr):
                        pool_info["checked_out_connections"] = checked_out_attr()
                    else:
                        pool_info["checked_out_connections"] = checked_out_attr
                elif hasattr(raw_pool, "_checkedout"):
                    checkedout_attr = getattr(raw_pool, "_checkedout")
                    if isinstance(checkedout_attr, (list, set, dict)):
                        pool_info["checked_out_connections"] = len(checkedout_attr)
                    else:
                        pool_info["checked_out_connections"] = checkedout_attr
                
                # Try to get other statistics with similar method/attribute handling
                if hasattr(raw_pool, "checkedin"):
                    checkedin_attr = getattr(raw_pool, "checkedin")
                    if callable(checkedin_attr):
                        pool_info["checkedin_connections"] = checkedin_attr()
                    else:
                        pool_info["checkedin_connections"] = checkedin_attr
                
                if hasattr(raw_pool, "overflow"):
                    overflow_attr = getattr(raw_pool, "overflow")
                    if callable(overflow_attr):
                        pool_info["overflow"] = overflow_attr()
                    else:
                        pool_info["overflow"] = overflow_attr
                elif hasattr(raw_pool, "_overflow"):
                    pool_info["overflow"] = getattr(raw_pool, "_overflow")
                
                # Get size - either method or attribute
                if hasattr(raw_pool, "size"):
                    size_attr = getattr(raw_pool, "size")
                    if callable(size_attr):
                        pool_info["pool_size"] = size_attr()
                    else:
                        pool_info["pool_size"] = size_attr
            
            # Direct attributes for simple pool implementations
            elif hasattr(pool, "_checkedout"):
                checkedout_attr = getattr(pool, "_checkedout")
                if isinstance(checkedout_attr, (list, set, dict)):
                    pool_info["checked_out_connections"] = len(checkedout_attr)
                else:
                    pool_info["checked_out_connections"] = checkedout_attr
                
            # Add calculated statistics if we have the required data
            if "checked_out_connections" in pool_info and "pool_size" in pool_info:
                try:
                    pool_info["available_connections"] = int(pool_info["pool_size"]) - int(pool_info["checked_out_connections"])
                except (ValueError, TypeError):
                    # If conversion fails, skip calculated field
                    pass
                
        except Exception as inner_e:
            logger.warning(f"Could not get complete pool statistics: {str(inner_e)}")
            pool_info["statistics_error"] = str(inner_e)
        
        # Get internal engine status
        if hasattr(engine, "pool"):
            pool_info["engine_connected"] = True
        
        # Extract direct pool stats from the SQLAlchemy object 
        # (fallback in case our main approach didn't work)
        if "pool_size" not in pool_info and hasattr(pool, "size"):
            size_attr = getattr(pool, "size")
            if callable(size_attr):
                try:
                    pool_info["pool_size"] = size_attr()
                except Exception:
                    pass
                    
        # Skip raw attributes debug info to reduce clutter
            
        return pool_info
    except Exception as e:
        logger.error(f"Error getting pool status: {str(e)}", exc_info=True)
        return {
            "error": str(e), 
            "pool_type": str(getattr(pool, "__class__", {"__name__": "unknown"}))
        }

async def detect_connection_leaks(threshold_percentage=80):
    """
    Detect potential connection leaks in the database pool
    
    Logs detailed connection pool status and stack trace when usage exceeds threshold
    
    Args:
        threshold_percentage: Connection usage percentage threshold to trigger warnings
    
    Returns:
        bool: True if potential leak detected, False otherwise
    """
    try:
        pool_status = await get_pool_status()
        
        # Check if we got an error or statistics error
        if "error" in pool_status:
            logger.error(f"Cannot detect leaks: {pool_status['error']}")
            return False
            
        if "statistics_error" in pool_status:
            logger.warning(f"Incomplete pool statistics: {pool_status['statistics_error']}")
        
        # Extract required metrics using a more defensive approach
        pool_size = pool_status.get("pool_size")
        checked_out = pool_status.get("checked_out_connections", 0)
        max_overflow = pool_status.get("max_overflow", 0)
        overflow = pool_status.get("overflow", 0)
        
        # If we can't determine pool size, we can't detect leaks
        if pool_size is None or not isinstance(pool_size, (int, float)):
            logger.warning(f"Cannot detect leaks: Unable to determine pool size. Pool status: {pool_status}")
            return False
            
        # Calculate total capacity and usage
        total_capacity = pool_size
        if isinstance(max_overflow, (int, float)):
            total_capacity += max_overflow
            
        total_used = checked_out
        if isinstance(overflow, (int, float)):
            total_used += overflow
            
        if total_capacity <= 0:
            logger.warning("Pool capacity appears to be zero, cannot calculate usage percentage")
            return False
            
        usage_percentage = (total_used / total_capacity) * 100
        logger.info(f"detect_connection_leaks usage_percentage={usage_percentage} "
                    f"total_used={total_used} total_capacity={total_capacity}")
        if usage_percentage >= threshold_percentage:
            # Log detailed connection pool status
            logger.warning(
                f"Possible connection leak detected! "
                f"Connection usage: {usage_percentage:.1f}% "
                f"({total_used}/{total_capacity}). "
                f"Pool status: {pool_status}"
            )
            
            # Add more debug information
            import traceback
            current_stack = ''.join(traceback.format_stack())
            logger.info(f"Current stack trace when leak detected:\n{current_stack}")
            
            return True
        return False
    except Exception as e:
        logger.error(f"Error in leak detection: {str(e)}", exc_info=True)
        return False

async def test_connection():
    """
    Test database connection by executing a simple query
    
    This function attempts to get a connection from the pool and execute
    a simple query to verify the database is accessible.
    
    Returns:
        dict: Status information including success flag and response time
    """
    start_time = time.time()
    session = None
    
    try:
        # Get a session from the pool
        session = SessionLocal()
        
        # Execute a simple query
        result = await session.execute("SELECT 1")
        row = result.scalar_one()
        
        # Calculate response time
        response_time = time.time() - start_time
        
        return {
            "success": True,
            "response_time_ms": round(response_time * 1000, 2),
            "result": row
        }
    except Exception as e:
        # Calculate time even for failures
        response_time = time.time() - start_time
        
        logger.error(f"Database connection test failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "response_time_ms": round(response_time * 1000, 2),
            "error": str(e)
        }
    finally:
        if session:
            await session.close()

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
