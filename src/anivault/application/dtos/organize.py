"""Organize DTOs for application ??presentation contract.

Presentation layer consumes these types only. Domain entities
(FileOperation, OperationResult) are never exposed to presentation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field


class OrganizeScanInput(Protocol):
    """Temporary S4 adapter contract ??NOT the final model.

    S2: Cleanest form is application returning DTO. This marker Protocol
    exists only to remove type-only core dependency in S4 scope.
    Long-term: organize scan result should become application DTO (e.g. OrganizeScanDTO).

    Presentation does NOT access file_path, metadata, or any domain shape.
    Handler treats scan result as opaque; passes through to use case only.
    """

    # marker protocol ??no attributes; presentation must not interpret


class OrganizePlanItem(BaseModel):
    """DTO for a single organize plan operation.

    Replaces FileOperation for presentation consumption.
    """

    operation_type: str = Field(..., description="move or copy")
    source_path: str = Field(..., description="Source file path")
    destination_path: str = Field(..., description="Destination file path")

    @property
    def source_path_obj(self) -> Path:
        """Path object for source (convenience)."""
        return Path(self.source_path)

    @property
    def destination_path_obj(self) -> Path:
        """Path object for destination (convenience)."""
        return Path(self.destination_path)


class OrganizeResultItem(BaseModel):
    """DTO for a single organize execution result.

    Replaces OperationResult for presentation consumption.
    """

    operation_type: str = Field(..., description="move or copy")
    source_path: str = Field(..., description="Source file path")
    destination_path: str = Field(..., description="Destination file path")
    success: bool = Field(..., description="Whether the operation succeeded")
    message: str | None = Field(None, description="Optional message")
    skipped: bool = Field(False, description="Whether the operation was skipped")


def file_operation_to_dto(op: object) -> OrganizePlanItem:
    """Convert FileOperation to OrganizePlanItem (duck-typed, no core import)."""
    ot = getattr(op, "operation_type", "move")
    ot_str = getattr(ot, "value", None) or str(ot)
    return OrganizePlanItem(
        operation_type=ot_str,
        source_path=str(getattr(op, "source_path", "")),
        destination_path=str(getattr(op, "destination_path", "")),
    )


def operation_result_to_dto(res: object) -> OrganizeResultItem:
    """Convert OperationResult to OrganizeResultItem."""
    op = getattr(res, "operation", None)
    op_type = "move"
    src = ""
    dst = ""
    if op is not None:
        op_type = getattr(getattr(op, "operation_type", None), "value", None) or "move"
        src = str(getattr(op, "source_path", ""))
        dst = str(getattr(op, "destination_path", ""))
    else:
        src = str(getattr(res, "source_path", ""))
        dst = str(getattr(res, "destination_path", ""))
    return OrganizeResultItem(
        operation_type=op_type,
        source_path=src,
        destination_path=dst,
        success=bool(getattr(res, "success", False)),
        message=getattr(res, "message", None),
        skipped=bool(getattr(res, "skipped", False)),
    )
