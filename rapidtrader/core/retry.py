"""Retry utilities for external API calls."""
from functools import wraps
from typing import Callable, TypeVar
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    RetryError
)
import logging
import requests
from .logging_config import get_logger
from .exceptions import RateLimitError, APIError, DataFetchError

logger = get_logger(__name__)

T = TypeVar('T')


def retry_api_call(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 30.0,
    exceptions: tuple = (requests.RequestException, ConnectionError, TimeoutError)
):
    """Decorator for retrying API calls with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)
        exceptions: Tuple of exception types to retry on

    Usage:
        @retry_api_call(max_attempts=3)
        def fetch_data():
            return requests.get(url)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(exceptions),
            before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
            reraise=True
        )
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return func(*args, **kwargs)
        return wrapper
    return decorator


def with_circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0
):
    """Simple circuit breaker pattern for API calls.

    After `failure_threshold` consecutive failures, the circuit opens
    and immediately raises an exception for `recovery_timeout` seconds.

    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before allowing retries
    """
    import time

    class CircuitState:
        def __init__(self):
            self.failures = 0
            self.last_failure_time = 0
            self.is_open = False

    state = CircuitState()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Check if circuit is open
            if state.is_open:
                time_since_failure = time.time() - state.last_failure_time
                if time_since_failure < recovery_timeout:
                    raise APIError(
                        f"Circuit breaker open - retry in {recovery_timeout - time_since_failure:.0f}s"
                    )
                # Try to close circuit
                state.is_open = False
                state.failures = 0
                logger.info("circuit_breaker_half_open", function=func.__name__)

            try:
                result = func(*args, **kwargs)
                # Success - reset failure count
                state.failures = 0
                return result
            except Exception as e:
                state.failures += 1
                state.last_failure_time = time.time()

                if state.failures >= failure_threshold:
                    state.is_open = True
                    logger.warning("circuit_breaker_opened",
                                  function=func.__name__,
                                  failures=state.failures)

                raise

        return wrapper
    return decorator


def handle_rate_limit(response: requests.Response, api_name: str = "API") -> None:
    """Check for rate limit response and raise appropriate exception.

    Args:
        response: HTTP response to check
        api_name: Name of the API for error messages

    Raises:
        RateLimitError: If rate limit is detected
    """
    if response.status_code == 429:
        retry_after = response.headers.get('Retry-After')
        retry_seconds = int(retry_after) if retry_after else None
        raise RateLimitError(api_name, retry_after=retry_seconds)


def safe_api_call(
    func: Callable[..., T],
    *args,
    default: T | None = None,
    error_message: str = "API call failed",
    **kwargs
) -> T | None:
    """Execute an API call safely, returning default on failure.

    Args:
        func: Function to call
        *args: Arguments to pass to function
        default: Default value to return on failure
        error_message: Message to log on failure
        **kwargs: Keyword arguments to pass to function

    Returns:
        Result of function or default value
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.warning("safe_api_call_failed",
                      error=str(e),
                      message=error_message)
        return default
