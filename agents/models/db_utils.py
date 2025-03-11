import asyncio
import functools
import logging
import time
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

async def set_session_variables(session, variables):
    """Set session variables, such as timeout settings"""
    for name, value in variables.items():
        await session.execute(f"SET SESSION {name} = {value}")

@asynccontextmanager
async def transaction_timeout(session, timeout_seconds=30):
    """Set timeout for transaction and rollback on timeout"""
    # Set session variables
    await set_session_variables(session, {
        "innodb_lock_wait_timeout": timeout_seconds,
        "max_execution_time": timeout_seconds * 1000  # milliseconds
    })
    
    # Create timeout task
    start_time = time.time()
    transaction_task = asyncio.current_task()
    
    # Create timeout handler
    def timeout_handler():
        elapsed = time.time() - start_time
        if elapsed >= timeout_seconds:
            logger.warning(f"Transaction timeout after {elapsed:.2f}s")
            transaction_task.cancel()
    
    # Set timeout timer
    timer = asyncio.create_task(asyncio.sleep(timeout_seconds))
    timer.add_done_callback(lambda _: timeout_handler())
    
    try:
        # Start transaction
        async with session.begin():
            yield session
    except asyncio.CancelledError:
        logger.error("Transaction was cancelled due to timeout")
        raise TimeoutError(f"Database transaction timed out after {timeout_seconds} seconds")
    finally:
        # Cancel timer
        if not timer.done():
            timer.cancel()

def with_transaction_timeout(timeout_seconds=30):
    """Decorator: Add transaction timeout to database operation functions"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Find session parameter
            session = None
            for arg in args:
                if isinstance(arg, AsyncSession):
                    session = arg
                    break
            
            if session is None:
                for _, value in kwargs.items():
                    if isinstance(value, AsyncSession):
                        session = value
                        break
            
            if session is None:
                logger.warning("No session found in function arguments, cannot apply timeout")
                return await func(*args, **kwargs)
            
            # Apply timeout
            async with transaction_timeout(session, timeout_seconds):
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator

async def execute_with_timeout(session, query, params=None, timeout_seconds=30):
    """Execute query with timeout"""
    # Set session variables
    await set_session_variables(session, {
        "max_execution_time": timeout_seconds * 1000  # milliseconds
    })
    
    start_time = time.time()
    try:
        # Execute query
        result = await session.execute(query, params)
        
        # Log execution time
        elapsed = time.time() - start_time
        if elapsed > 5:  # Log queries taking more than 5 seconds
            logger.warning(f"Slow query took {elapsed:.2f}s: {query}")
        
        return result
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Query failed after {elapsed:.2f}s: {str(e)}")
        raise

async def check_transaction_duration(session, start_time, warning_threshold=10):
    """Check transaction duration and log warnings"""
    elapsed = time.time() - start_time
    if elapsed > warning_threshold:
        # Get current transaction info
        result = await session.execute("SELECT trx_id, trx_started, trx_state FROM information_schema.innodb_trx WHERE trx_mysql_thread_id = CONNECTION_ID()")
        trx_info = result.fetchone()
        
        if trx_info:
            trx_id, trx_started, trx_state = trx_info
            logger.warning(
                f"Long transaction detected: ID={trx_id}, State={trx_state}, "
                f"Started={trx_started}, Duration={elapsed:.2f}s"
            )
        else:
            logger.warning(f"Long database operation detected: {elapsed:.2f}s")
        
        return True
    return False 