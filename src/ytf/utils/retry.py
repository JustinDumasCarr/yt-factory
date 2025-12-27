"""
Retry utilities for handling transient failures in batch mode and provider calls.

Provides both a function-based retry wrapper and a decorator for step-level retries.
"""

import random
import time
from functools import wraps
from typing import Callable, TypeVar, Union

T = TypeVar("T")

# Retriable HTTP status codes
RETRIABLE_STATUS_CODES = [429, 500, 502, 503, 504]

# Default retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_INITIAL_DELAY = 1.0  # seconds
DEFAULT_MAX_DELAY = 60.0  # seconds


def is_retriable_error(error: Exception) -> bool:
    """
    Check if an error is retriable.

    Args:
        error: Exception to check

    Returns:
        True if error is retriable, False otherwise
    """
    # Check for httpx HTTPStatusError (response.status_code)
    if hasattr(error, "response") and hasattr(error.response, "status_code"):
        return error.response.status_code in RETRIABLE_STATUS_CODES

    # Check for HTTP status codes directly
    if hasattr(error, "status_code"):
        return error.status_code in RETRIABLE_STATUS_CODES

    # Check for HTTP response status (googleapiclient)
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


def retry_call(
    fn: Callable[[], T],
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
    initial_delay: float = DEFAULT_INITIAL_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    jitter: bool = True,
    retriable_check: Callable[[Exception], bool] = is_retriable_error,
) -> T:
    """
    Execute a function with retry logic on transient errors.

    Args:
        fn: Function to execute (no arguments)
        max_retries: Maximum number of retries (default: 3)
        initial_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay cap in seconds (default: 60.0)
        jitter: Whether to add random jitter to delays (default: True)
        retriable_check: Function to check if error is retriable

    Returns:
        Result of function call

    Raises:
        Exception: The last exception raised if all retries exhausted
    """
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            return fn()
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
            delay = min(delay, max_delay)

            # Add jitter if enabled (up to 20% of delay)
            if jitter:
                jitter_amount = delay * 0.2 * random.random()
                delay = delay + jitter_amount

            # Log retry attempt
            error_preview = str(e)[:100]
            print(
                f"[RETRY] Attempt {attempt + 1}/{max_retries + 1}: {error_preview}... "
                f"Waiting {delay:.1f}s before retry"
            )

            time.sleep(delay)

    # Should never reach here, but just in case
    if last_error:
        raise last_error
    raise RuntimeError("retry_call: unexpected end of retry loop")


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

