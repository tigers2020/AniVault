"""Pipeline utilities package.

This package provides core utilities for the file processing pipeline:
- BoundedQueue: Thread-safe queue with size limits for backpressure
- Statistics classes: For collecting pipeline metrics
"""

from __future__ import annotations

from anivault.core.pipeline.utils.bounded_queue import BoundedQueue
from anivault.core.pipeline.utils.statistics import (
    ParserStatistics,
    QueueStatistics,
    ScanStatistics,
)
from anivault.core.pipeline.utils.synchronization import (
    ThreadSafeStatsUpdater,
    synchronized,
    thread_safe_operation,
)

__all__ = [
    "BoundedQueue",
    "ParserStatistics",
    "QueueStatistics",
    "ScanStatistics",
    "ThreadSafeStatsUpdater",
    "synchronized",
    "thread_safe_operation",
]
