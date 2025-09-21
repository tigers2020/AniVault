"""Services module for AniVault application.

This module contains service classes that handle background operations
and provide interfaces between the ViewModel and Model layers.
"""

from .file_pipeline_worker import FilePipelineWorker
from .thread_safety import (
    ThreadSafeCounter,
    ThreadSafeDict,
    ThreadSafeList,
    ThreadSafeProperty,
    ThreadSafetyValidator,
    ensure_main_thread,
    prevent_deadlock,
    python_thread_safe_method,
    thread_safe_method,
)

__all__ = [
    "FilePipelineWorker",
    "ThreadSafeCounter",
    "ThreadSafeDict",
    "ThreadSafeList",
    "ThreadSafeProperty",
    "ThreadSafetyValidator",
    "ensure_main_thread",
    "prevent_deadlock",
    "python_thread_safe_method",
    "thread_safe_method",
]
