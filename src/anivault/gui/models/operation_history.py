"""Data models for GUI operation history."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from anivault.shared.types.operation_types import (
    OperationDetailsDict,
    OperationHistoryDict,
)


@dataclass
class OperationDetails:
    """Operation details for audit history."""

    file_path: str | None = None
    operation_type: str | None = None
    source_path: str | None = None
    destination_path: str | None = None
    status: str | None = None
    message: str | None = None

    def to_dict(self) -> OperationDetailsDict:
        """Convert operation details to a dict representation."""
        return {
            "file_path": self.file_path,
            "operation_type": self.operation_type,
            "source_path": self.source_path,
            "destination_path": self.destination_path,
            "status": self.status,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: OperationDetailsDict) -> OperationDetails:
        """Create OperationDetails from a dict representation."""
        return cls(
            file_path=data.get("file_path"),
            operation_type=data.get("operation_type"),
            source_path=data.get("source_path"),
            destination_path=data.get("destination_path"),
            status=data.get("status"),
            message=data.get("message"),
        )


@dataclass
class OperationHistoryEntry:
    """Single operation history entry."""

    id: str
    type: str
    timestamp: datetime
    details: OperationDetails

    def to_dict(self) -> OperationHistoryDict:
        """Convert history entry to a dict representation."""
        return {
            "id": self.id,
            "type": self.type,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: OperationHistoryDict) -> OperationHistoryEntry:
        """Create OperationHistoryEntry from a dict representation."""
        return cls(
            id=data["id"],
            type=data["type"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            details=OperationDetails.from_dict(data.get("details", {})),
        )


@dataclass
class OperationHistory:
    """Collection of operation history entries."""

    entries: list[OperationHistoryEntry] = field(default_factory=list)

    def add(self, entry: OperationHistoryEntry) -> None:
        """Add an entry to the history."""
        self.entries.append(entry)

    def to_dict(self) -> list[OperationHistoryDict]:
        """Convert history to a list of dict representations."""
        return [entry.to_dict() for entry in self.entries]

    @classmethod
    def from_dict_list(cls, data: list[OperationHistoryDict]) -> OperationHistory:
        """Create OperationHistory from a list of dict representations."""
        return cls(entries=[OperationHistoryEntry.from_dict(item) for item in data])


__all__ = [
    "OperationDetails",
    "OperationHistoryEntry",
    "OperationHistory",
]
