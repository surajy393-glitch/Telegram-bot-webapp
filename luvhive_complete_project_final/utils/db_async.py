# utils/db_async.py
"""
Async database utilities to prevent event loop blocking.

This utility wraps synchronous database operations in thread executors
to prevent blocking the asyncio event loop during DB I/O operations.
"""
import asyncio
from typing import Any, Callable
from registration import _conn

# Optional semaphore to prevent thread pool exhaustion
# Set to slightly less than DB pool size (maxconn=15)
DB_SEMAPHORE = asyncio.Semaphore(12)

async def run_db(fn: Callable, *args: Any, **kwargs: Any) -> Any:
    """
    Execute a synchronous database function in a thread executor.
    
    Args:
        fn: Function that performs database operations
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
    
    Returns:
        The result of the database function
    
    Usage:
        async def some_handler(...):
            def db_transaction(user_id):
                with _conn() as con, con.cursor() as cur:
                    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                    result = cur.fetchone()
                    con.commit()
                    return result
            
            result = await run_db(db_transaction, user_id)
    """
    async with DB_SEMAPHORE:
        return await asyncio.to_thread(fn, *args, **kwargs)

async def run_db_uncapped(fn: Callable, *args: Any, **kwargs: Any) -> Any:
    """
    Execute a synchronous database function without semaphore protection.
    Use this for non-critical operations that can tolerate higher concurrency.
    """
    return await asyncio.to_thread(fn, *args, **kwargs)