"""Type definitions for operation history dictionary representations.

This module provides TypedDict definitions for type-safe operation history
structures, eliminating dict[str, Any] usage in GUI state serialization.
"""

from __future__ import annotations

from typing import TypedDict


class OperationDetailsDict(TypedDict, total=False):
    """Type-safe dictionary representation of operation details."""

    file_path: str | None
    operation_type: str | None
    source_path: str | None
    destination_path: str | None
    status: str | None
    message: str | None


class OperationHistoryDict(TypedDict):
    """Type-safe dictionary representation of operation history entry."""

    id: str
    type: str
    timestamp: str
    details: OperationDetailsDict


__all__ = [
    "OperationDetailsDict",
    "OperationHistoryDict",
]
