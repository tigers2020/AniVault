"""Dataclass serialization utilities for AniVault.

This module provides utilities for converting dataclasses to/from dictionaries,
replacing Pydantic model_dump() with type-safe dataclass serialization.

Design Principles:
- Type-safe (full mypy support)
- Simple and maintainable (minimal complexity)
- Compatible with existing dataclass patterns in codebase
- Performance-optimized for typical use cases

Migration Strategy:
- Replace ModelConverter.to_dict() usage
- Replace Pydantic BaseModel inheritance with dataclass
- Gradual migration supported via feature flags if needed
"""

from __future__ import annotations

from dataclasses import MISSING, asdict, fields, is_dataclass
from datetime import datetime
from typing import Any, get_args, get_origin, get_type_hints
from uuid import UUID


def to_dict(obj: Any) -> dict[str, Any]:
    """Convert dataclass to dictionary.

    Supports:
    - Basic dataclasses (via dataclasses.asdict)
    - Nested dataclasses
    - datetime -> ISO 8601 string
    - UUID -> string
    - tmdbv3api.as_obj.AsObj -> dict (recursive conversion)

    Args:
        obj: Dataclass instance to convert

    Returns:
        Dictionary representation of the dataclass

    Raises:
        TypeError: If obj is not a dataclass

    Example:
        >>> @dataclass
        ... class User:
        ...     name: str
        ...     age: int
        >>> user = User(name="Alice", age=30)
        >>> to_dict(user)
        {'name': 'Alice', 'age': 30}
    """
    if not is_dataclass(obj):
        error_msg = f"{type(obj).__name__} is not a dataclass"
        raise TypeError(error_msg)

    data = asdict(obj)

    # Handle datetime, UUID, and AsObj serialization
    for field in fields(obj):
        value = getattr(obj, field.name)
        if isinstance(value, datetime):
            data[field.name] = value.isoformat()
        elif isinstance(value, UUID):
            data[field.name] = str(value)
        else:
            # Handle nested objects (including AsObj)
            data[field.name] = _convert_to_dict_recursive(value)

    return data


def _convert_to_dict_recursive(obj: Any) -> Any:
    """Recursively convert objects to JSON-serializable format.

    Handles:
    - Basic types (None, bool, int, float, str)
    - Collections (dict, list, tuple)
    - Objects with __dict__ (including tmdbv3api.as_obj.AsObj)
    - Fallback to string representation

    Args:
        obj: Object to convert

    Returns:
        JSON-serializable representation
    """
    # None, 기본 타입은 그대로 반환
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj

    # 딕셔너리
    if isinstance(obj, dict):
        return {key: _convert_to_dict_recursive(value) for key, value in obj.items()}

    # 리스트/튜플
    if isinstance(obj, (list, tuple)):
        return [_convert_to_dict_recursive(item) for item in obj]

    # AsObj 또는 __dict__ 속성이 있는 객체
    if hasattr(obj, "__dict__"):
        result = {}
        for key, value in obj.__dict__.items():
            if not key.startswith("_"):  # private 속성 제외
                result[key] = _convert_to_dict_recursive(value)
        return result

    # 기타: 문자열로 변환
    return str(obj)


def from_dict(cls: type, data: dict[str, Any], extra: str = "ignore") -> Any:
    """Create dataclass instance from dictionary.

    Supports:
    - Basic type conversion
    - Nested dataclasses (Subtask 2.1)
    - List/Dict types (Subtask 2.2)
    - Optional fields (Subtask 2.3)
    - Field aliases (Subtask 3.2)
    - extra='forbid' mode (Subtask 3.3)

    Args:
        cls: Dataclass class to instantiate
        data: Dictionary with field values
        extra: How to handle extra fields - "ignore" (default) or "forbid"

    Returns:
        Dataclass instance

    Raises:
        TypeError: If cls is not a dataclass or if extra='forbid' and extra fields found

    Example:
        >>> @dataclass
        ... class User:
        ...     name: str
        ...     age: int
        >>> data = {'name': 'Alice', 'age': 30}
        >>> user = from_dict(User, data)
        >>> user.name
        'Alice'
    """
    if not is_dataclass(cls):
        error_msg = f"{cls.__name__} is not a dataclass"
        raise TypeError(error_msg)

    # Convert datetime/UUID strings back to objects
    type_hints = get_type_hints(cls)

    # Build alias mapping (Subtask 3.2)
    alias_to_field: dict[str, str] = {}
    for field in fields(cls):
        if field.metadata and "alias" in field.metadata:
            alias = field.metadata["alias"]
            alias_to_field[alias] = field.name

    # Check for extra fields if extra='forbid' (Subtask 3.3)
    if extra == "forbid":
        allowed_keys: set[str] = set()
        for f in fields(cls):
            allowed_keys.add(f.name)
            # Add aliases to allowed keys
            if f.metadata and "alias" in f.metadata:
                allowed_keys.add(f.metadata["alias"])

        data_keys = set(data.keys())
        extra_keys = data_keys - allowed_keys
        if extra_keys:
            error_msg = f"Extra fields not allowed: {sorted(extra_keys)}"
            raise TypeError(error_msg)

    result: dict[str, Any] = {}

    for field in fields(cls):
        # Check if data contains this field (by name or alias)
        field_key = None
        if field.name in data:
            field_key = field.name
        elif field.name in alias_to_field.values():
            # This field has an alias, check if alias is in data
            for alias, actual_field in alias_to_field.items():
                if actual_field == field.name and alias in data:
                    field_key = alias
                    break

        # Check if field has a default value
        if field.default is not MISSING or field.default_factory is not MISSING:
            # If field not in data, use default
            if field_key is None:
                continue

        if field_key is None:
            raise KeyError(f"Missing required field: {field.name}")

        value = data[field_key]

        # Get actual type from type hints (handles string annotations)
        field_type = type_hints.get(field.name)

        if field_type is not None:
            # Handle type hints properly (considering Optional, Union, etc.)
            origin = get_origin(field_type)
            args = get_args(field_type) if origin is not None else ()

            # Handle Optional[T] -> Union[T, None]
            if origin is not None and origin not in (list, dict):
                # Get the actual type from Union types
                # Find non-None types
                actual_types = [a for a in args if a is not type(None)]
                if actual_types:
                    field_type = actual_types[0]
                    origin = get_origin(field_type)
                    args = get_args(field_type) if origin is not None else ()

            # Basic datetime/UUID conversion
            if field_type is datetime and isinstance(value, str):
                result[field.name] = datetime.fromisoformat(value)
            elif field_type is UUID and isinstance(value, str):
                uuid_value: UUID = UUID(value)
                result[field.name] = uuid_value
            # Handle None values for Optional fields
            elif value is None:
                result[field.name] = None
            # Handle nested dataclasses (Subtask 2.1)
            elif is_dataclass(field_type) and isinstance(value, dict):
                # Type guard: field_type is a dataclass
                nested_result = from_dict(field_type, value)
                result[field.name] = nested_result
            # Handle List types (Subtask 2.2)
            elif origin is list and isinstance(value, list):
                # Get item type from List[T]
                item_type = args[0] if args else None
                if item_type and is_dataclass(item_type):
                    # List of dataclasses: convert each item
                    result[field.name] = [from_dict(item_type, item) for item in value]
                else:
                    result[field.name] = value
            # Handle Dict types (Subtask 2.2)
            elif origin is dict and isinstance(value, dict):
                # Get value type from Dict[K, V]
                value_type = args[1] if len(args) > 1 else None
                if value_type and is_dataclass(value_type):
                    # Dict with dataclass values: convert each value
                    result[field.name] = {
                        k: from_dict(value_type, v) for k, v in value.items()
                    }
                else:
                    result[field.name] = value
            else:
                result[field.name] = value
        else:
            result[field.name] = value

    return cls(**result)


__all__ = ["from_dict", "to_dict"]
