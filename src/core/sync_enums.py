"""Enums for synchronization operations and monitoring.

This module contains shared enums used across the synchronization system
to avoid circular import issues.
"""

from enum import Enum


class SyncOperationType(Enum):
    """Types of synchronization operations."""

    READ_THROUGH = "read_through"
    WRITE_THROUGH = "write_through"
    BULK_INSERT = "bulk_insert"
    BULK_UPDATE = "bulk_update"
    BULK_UPSERT = "bulk_upsert"
    DELETE = "delete"
    CONSISTENCY_CHECK = "consistency_check"
    RECONCILIATION = "reconciliation"
    INCREMENTAL_SYNC = "incremental_sync"


class SyncOperationStatus(Enum):
    """Status of synchronization operations."""

    STARTED = "started"
    SUCCESS = "success"
    FAILED = "failed"
    FAILURE = "failure"
    PARTIAL_SUCCESS = "partial_success"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class SyncEntityType(Enum):
    """Types of entities that can be synchronized."""

    TMDB_METADATA = "tmdb_metadata"
    PARSED_FILES = "parsed_files"
