"""
Retry utilities for handling transient hardware failures.

Provides decorators and helper functions for retrying operations with exponential backoff.
"""

import time
import logging
from functools import wraps
from typing import Callable, Tuple, Type, Any, Optional


logger = logging.getLogger(__name__)


def retry_operation(
    max_attempts: int = 3,
    delay: float = 0.1,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int, int], None]] = None,
    on_failure: Optional[Callable[[Exception, int], None]] = None
):
    """
    Decorator for retrying operations with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts (default: 3)
        delay: Initial delay between retries in seconds (default: 0.1)
        backoff: Multiplier for delay after each retry (default: 2.0)
        exceptions: Tuple of exception types to catch and retry (default: all Exceptions)
        on_retry: Optional callback function(exception, attempt, max_attempts) called on each retry
        on_failure: Optional callback function(exception, attempts) called when all retries fail

    Returns:
        Decorated function that retries on failure

    Example:
        @retry_operation(max_attempts=3, delay=0.1, exceptions=(OSError, IOError))
        def flaky_i2c_read():
            return device.read()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_attempts:
                        # Log retry attempt
                        if on_retry:
                            on_retry(e, attempt, max_attempts)
                        else:
                            logger.debug(
                                f"Retry {attempt}/{max_attempts} for {func.__name__} "
                                f"after {type(e).__name__}: {e}. "
                                f"Waiting {current_delay:.3f}s"
                            )

                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        # All retries exhausted
                        if on_failure:
                            on_failure(e, max_attempts)
                        else:
                            logger.error(
                                f"Failed {func.__name__} after {max_attempts} attempts. "
                                f"Last error: {type(e).__name__}: {e}"
                            )
                        raise

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


def retry_with_context(
    operation_name: str,
    max_attempts: int = 3,
    delay: float = 0.1,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    logger_instance: Optional[logging.Logger] = None
) -> Callable:
    """
    Create a retry decorator with contextual logging.

    This is a helper that creates a retry decorator with pre-configured logging
    that includes the operation name for better debugging.

    Args:
        operation_name: Name of the operation for logging (e.g., "I2C read", "Arduino write")
        max_attempts: Maximum number of attempts
        delay: Initial delay between retries
        backoff: Delay multiplier
        exceptions: Exceptions to catch
        logger_instance: Logger to use (defaults to module logger)

    Returns:
        Configured retry decorator

    Example:
        retry_i2c = retry_with_context("I2C operation", max_attempts=5, exceptions=(OSError, IOError))

        @retry_i2c
        def read_sensor():
            return i2c.read()
    """
    log = logger_instance or logger

    def on_retry_callback(e: Exception, attempt: int, max_attempts: int):
        log.warning(
            f"{operation_name} failed (attempt {attempt}/{max_attempts}): "
            f"{type(e).__name__}: {e}. Retrying..."
        )

    def on_failure_callback(e: Exception, attempts: int):
        log.error(
            f"{operation_name} failed after {attempts} attempts: "
            f"{type(e).__name__}: {e}"
        )

    return retry_operation(
        max_attempts=max_attempts,
        delay=delay,
        backoff=backoff,
        exceptions=exceptions,
        on_retry=on_retry_callback,
        on_failure=on_failure_callback
    )
