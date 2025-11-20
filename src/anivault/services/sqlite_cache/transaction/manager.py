"""Transaction manager for SQLite cache.

This module provides transaction management for cache operations.
"""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    import sqlite3

logger = logging.getLogger(__name__)


class TransactionManager:
    """Transaction management for cache operations."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        """Initialize transaction manager.

        Args:
            conn: SQLite database connection
        """
        self.conn = conn

    def __enter__(self) -> Self:
        """Enter context manager - begin transaction."""
        self.begin()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> bool | None:
        """Exit context manager - commit or rollback."""
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        return None  # Don't suppress exceptions

    def begin(self) -> None:
        """Begin a transaction."""
        self.conn.execute("BEGIN")

    def commit(self) -> None:
        """Commit the current transaction."""
        self.conn.execute("COMMIT")

    def rollback(self) -> None:
        """Rollback the current transaction."""
        self.conn.execute("ROLLBACK")

    @contextmanager
    def transaction(self) -> Generator[None, None, None]:
        """Context manager for transactions.

        Automatically commits on success or rolls back on exception.

        Example:
            >>> with transaction_manager.transaction():
            ...     cache.set("key1", data1)
            ...     cache.set("key2", data2)
        """
        self.begin()
        try:
            yield
            self.commit()
        except Exception:
            self.rollback()
            raise
