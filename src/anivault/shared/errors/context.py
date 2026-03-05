"""Error context catalog (Phase 4).

Structured context for errors with PII masking.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Union

PrimitiveContextValue = Union[str, int, float, bool]
SAFE_DICT_MASK_KEYS: tuple[str, ...] = ("user_id",)


def _coerce_primitives(value: Any | None) -> dict[str, PrimitiveContextValue] | None:
    """Coerce additional_data values to primitives."""
    if value is None:
        return None
    if not isinstance(value, dict):
        msg = f"additional_data must be dict, got {type(value).__name__}"
        raise TypeError(msg)

    coerced: dict[str, PrimitiveContextValue] = {}
    for key, val in value.items():
        if val is None:
            continue
        if isinstance(val, (str, int, float, bool)):
            coerced[key] = val
        elif isinstance(val, Path):
            coerced[key] = str(val)
        elif isinstance(val, Enum):
            coerced[key] = val.value
        elif isinstance(val, Decimal):
            coerced[key] = float(val)
        else:
            msg = f"Cannot coerce {type(val).__name__} to primitive. Only str, int, float, bool, Path, Enum, Decimal allowed."
            raise TypeError(msg)
    return coerced


@dataclass(frozen=True)
class ErrorContextModel:
    """Context information for errors with PII masking."""

    file_path: str | None = None
    operation: str | None = None
    user_id: str | None = None
    additional_data: dict[str, PrimitiveContextValue] | None = None

    def __post_init__(self) -> None:
        if self.additional_data is not None:
            coerced = _coerce_primitives(self.additional_data)
            object.__setattr__(self, "additional_data", coerced)

    def safe_dict(self, *, mask_keys: tuple[str, ...] | None = None) -> dict[str, Any]:
        """Export context as dict with PII masking."""
        if mask_keys is None:
            mask_keys = SAFE_DICT_MASK_KEYS

        data: dict[str, Any] = {}
        if self.file_path is not None and "file_path" not in mask_keys:
            data["file_path"] = self.file_path
        if self.operation is not None and "operation" not in mask_keys:
            data["operation"] = self.operation
        if self.user_id is not None and "user_id" not in mask_keys:
            data["user_id"] = self.user_id
        if self.additional_data is not None and "additional_data" not in mask_keys:
            data["additional_data"] = self.additional_data
        else:
            data["additional_data"] = {}
        return data


ErrorContext = ErrorContextModel  # Backward compatibility alias
