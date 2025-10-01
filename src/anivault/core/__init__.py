"""
Core components for AniVault.

This module contains fundamental data structures and utilities
used throughout the AniVault system.
"""

from .bounded_queue import BoundedQueue
from .log_manager import (
    LogFileCorruptedError,
    LogFileNotFoundError,
    OperationLogManager,
)
from .models import FileOperation, OperationType, ScannedFile
from .normalization import normalize_query, normalize_query_from_anitopy
from .organizer import FileOrganizer
from .statistics import StatisticsCollector, get_statistics_collector

__all__ = [
    "BoundedQueue",
    "FileOperation",
    "FileOrganizer",
    "LogFileCorruptedError",
    "LogFileNotFoundError",
    "normalize_query",
    "normalize_query_from_anitopy",
    "OperationLogManager",
    "OperationType",
    "ScannedFile",
    "StatisticsCollector",
    "get_statistics_collector",
]
