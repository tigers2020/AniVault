"""Base operation class for SQLite cache operations.

This module provides shared functionality for all cache operations.
"""

from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3

    from anivault.core.statistics import StatisticsCollector

logger = logging.getLogger(__name__)


class BaseOperation:
    """Base class for cache operations with shared functionality."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        statistics: StatisticsCollector,
    ) -> None:
        """Initialize base operation.

        Args:
            conn: SQLite database connection
            statistics: Statistics collector for performance tracking
        """
        self.conn = conn
        self.statistics = statistics

    def _generate_cache_key_hash(self, key: str) -> tuple[str, str]:
        """Generate cache key hash for indexing.

        Args:
            key: Cache key string

        Returns:
            Tuple of (original_key, key_hash)
        """
        key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return key, key_hash

    def _validate_connection(self) -> None:
        """Validate database connection is available.

        Raises:
            RuntimeError: If connection is not initialized
        """
        if self.conn is None:
            raise RuntimeError("Database connection not initialized")
