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
    """Decorator for retrying API calls with exponential backoff."""
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
    """Circuit breaker pattern - opens after threshold failures, closes after timeout."""
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
            if state.is_open:
                time_since_failure = time.time() - state.last_failure_time
                if time_since_failure < recovery_timeout:
                    raise APIError(
                        f"Circuit breaker open - retry in {recovery_timeout - time_since_failure:.0f}s"
                    )
                state.is_open = False
                state.failures = 0
                logger.info("circuit_breaker_half_open", function=func.__name__)

            try:
                result = func(*args, **kwargs)
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
    """Execute API call safely, returning default on failure."""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.warning("safe_api_call_failed",
                      error=str(e),
                      message=error_message)
        return default
