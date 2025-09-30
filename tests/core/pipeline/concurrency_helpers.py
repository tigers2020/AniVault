"""Concurrency test helpers for validating thread safety.

This module provides utilities for testing race conditions and
thread safety in the pipeline.
"""

from __future__ import annotations

import random
import threading
import time
from pathlib import Path
from typing import Any


class SharedCounter:
    """Thread-safe counter for concurrency testing.

    This counter uses a threading.Lock to ensure thread-safe increments.
    It's used to detect race conditions in the pipeline.
    """

    def __init__(self, initial_value: int = 0) -> None:
        """Initialize the shared counter.

        Args:
            initial_value: Starting value for the counter.
        """
        self._value = initial_value
        self._lock = threading.Lock()

    def increment(self) -> None:
        """Increment the counter in a thread-safe manner."""
        with self._lock:
            self._value += 1

    def increment_unsafe(self) -> None:
        """Increment the counter WITHOUT locking (for testing race conditions).

        This method intentionally does NOT use the lock, allowing
        race conditions to occur. Used to verify that tests can
        detect concurrency issues.
        """
        # Intentionally no lock - allow race conditions
        current = self._value
        time.sleep(random.uniform(0.0001, 0.001))  # Encourage race conditions
        self._value = current + 1

    @property
    def value(self) -> int:
        """Get the current counter value.

        Returns:
            Current counter value.
        """
        with self._lock:
            return self._value

    def reset(self) -> None:
        """Reset the counter to zero."""
        with self._lock:
            self._value = 0


def create_race_condition_test_parser(counter: SharedCounter, use_lock: bool = True):
    """Create a test parser function for race condition testing.

    Args:
        counter: SharedCounter instance to increment.
        use_lock: If True, use locked increment. If False, use unsafe increment.

    Returns:
        A parser function that can be used in place of the real parser.
    """

    def test_parser(file_path: Path) -> dict[str, Any]:
        """Test parser that increments a shared counter.

        This parser simulates parsing work with a small sleep to
        encourage race conditions if locking is not working properly.

        Args:
            file_path: Path to file being parsed (not actually used).

        Returns:
            Minimal parse result dict.
        """
        # Small sleep to encourage race conditions
        time.sleep(random.uniform(0.001, 0.005))

        # Increment counter
        if use_lock:
            counter.increment()
        else:
            counter.increment_unsafe()

        # Return minimal result
        return {
            "file_path": str(file_path),
            "status": "success",
            "worker_id": f"worker_{threading.get_ident()}",
        }

    return test_parser
