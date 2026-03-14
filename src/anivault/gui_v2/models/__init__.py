"""Shared models for GUI v2."""

from .errors import OperationError
from .progress import OperationProgress, format_progress_message

__all__ = ["OperationError", "OperationProgress", "format_progress_message"]
