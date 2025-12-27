"""
Retry utilities for handling transient failures in batch mode.

Provides a simple retry decorator with exponential backoff for step-level retries.
"""

import time
from functools import wraps
from typing import Callable, TypeVar, Union

T = TypeVar("T")

# Retriable HTTP status codes
RETRIABLE_STATUS_CODES = [429, 500, 502, 503, 504]

# Default retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_INITIAL_DELAY = 1.0  # seconds


def is_retriable_error(error: Exception) -> bool:
    """
    Check if an error is retriable.

    Args:
        error: Exception to check

    Returns:
        True if error is retriable, False otherwise
    """
    # Check for HTTP status codes
    if hasattr(error, "status_code"):
        return error.status_code in RETRIABLE_STATUS_CODES

    # Check for HTTP response status
    if hasattr(error, "resp") and hasattr(error.resp, "status"):
        return error.resp.status in RETRIABLE_STATUS_CODES

    # Check error message for common retriable patterns
    error_msg = str(error).lower()
    retriable_patterns = [
        "rate limit",
        "quota exceeded",
        "too many requests",
        "service unavailable",
        "internal server error",
        "bad gateway",
        "gateway timeout",
        "timeout",
        "connection",
    ]

    return any(pattern in error_msg for pattern in retriable_patterns)


def retry_step(
    max_retries: int = DEFAULT_MAX_RETRIES,
    initial_delay: float = DEFAULT_INITIAL_DELAY,
    retriable_check: Callable[[Exception], bool] = is_retriable_error,
) -> Callable[[Callable[[str], T]], Callable[[str], T]]:
    """
    Decorator to retry a step function on transient errors.

    Args:
        max_retries: Maximum number of retries (default: 3)
        initial_delay: Initial delay in seconds (default: 1.0)
        retriable_check: Function to check if error is retriable

    Returns:
        Decorated function that retries on retriable errors

    Example:
        @retry_step(max_retries=3)
        def my_step(project_id: str) -> None:
            # step implementation
            pass
    """

    def decorator(func: Callable[[str], T]) -> Callable[[str], T]:
        @wraps(func)
        def wrapper(project_id: str) -> T:
            last_error = None

            for attempt in range(max_retries + 1):
                try:
                    return func(project_id)
                except Exception as e:
                    last_error = e

                    # Check if error is retriable
                    if not retriable_check(e):
                        # Non-retriable error, re-raise immediately
                        raise

                    # If this was the last attempt, re-raise
                    if attempt >= max_retries:
                        raise

                    # Calculate delay with exponential backoff
                    delay = initial_delay * (2 ** attempt)

                    # Log retry attempt (using print since we don't have logger context here)
                    print(
                        f"[RETRY] Attempt {attempt + 1}/{max_retries + 1} for {func.__name__} "
                        f"(project: {project_id}): {str(e)[:100]}"
                    )
                    print(f"[RETRY] Waiting {delay:.1f}s before retry...")

                    time.sleep(delay)

            # Should never reach here, but just in case
            if last_error:
                raise last_error

        return wrapper

    return decorator

