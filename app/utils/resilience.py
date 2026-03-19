import asyncio
import logging
from functools import wraps

logger = logging.getLogger(__name__)

def retry_on_failure(retries=3, delay=2, backoff=2):
    """
    Retry decorator for transient network errors (e.g. yfinance, external APIs).
    """
    def decorator(f):
        @wraps(f)
        async def wrapper(*args, **kwargs):
            m_retries, m_delay = retries, delay
            while m_retries > 1:
                try:
                    return await f(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"Retrying {f.__name__} due to error: {e}. {m_retries-1} attempts left.")
                    await asyncio.sleep(m_delay)
                    m_retries -= 1
                    m_delay *= backoff
            return await f(*args, **kwargs) # Last attempt
        return wrapper
    return decorator
