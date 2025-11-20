"""
Type Conversion Utilities

This module provides utilities for converting between dict/Any and
typed Pydantic models, facilitating gradual migration.

Conversion Strategy:
- Use TypeAdapter for efficient dict → model conversion
- Cache TypeAdapter instances for performance
- Provide clear error messages on validation failure

Performance Target: <10ms per conversion for typical models
"""

from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Any, TypeVar, cast

import orjson
from pydantic import BaseModel, TypeAdapter, ValidationError

if TYPE_CHECKING:
    from collections.abc import Mapping

T = TypeVar("T", bound=BaseModel)


@functools.lru_cache(maxsize=128)
def _get_type_adapter(model_cls: type[BaseModel]) -> TypeAdapter[BaseModel]:
    """Get or create a cached TypeAdapter for the given model class.

    TypeAdapter instances are expensive to create, so we cache them using
    functools.lru_cache. This provides thread-safe caching with minimal overhead.

    Performance Note:
        - First call per model: ~1-2ms (adapter creation)
        - Cached calls: ~0.001ms (dictionary lookup)
        - Thread-safe by default (lru_cache uses locks internally)

    Args:
        model_cls: Pydantic model class to create adapter for

    Returns:
        Cached TypeAdapter instance for the model

    Example:
        >>> from anivault.services.tmdb import TMDBGenre
        >>> adapter = _get_type_adapter(TMDBGenre)
        >>> isinstance(adapter, TypeAdapter)
        True
    """
    return TypeAdapter(model_cls)


class ModelConverter:
    """Static utility class for converting between dict and Pydantic models.

    This class provides a unified interface for type conversion operations,
    replacing scattered conversion logic throughout the codebase.

    Design Principles:
        - Static methods only (no state)
        - Performance-optimized (TypeAdapter caching)
        - Type-safe (full mypy support)
        - Clear error messages (wrapped ValidationError)

    Usage:
        >>> from anivault.services.tmdb import TMDBGenre
        >>> data = {"id": 16, "name": "Animation"}
        >>> genre = ModelConverter.to_model(data, TMDBGenre)
        >>> genre.id
        16
    """

    @staticmethod
    def to_model(data: Mapping[str, Any], model_cls: type[T]) -> T:
        """Convert dictionary to Pydantic model with validation.

        This method uses cached TypeAdapter for efficient conversion and
        provides detailed error messages on validation failure.

        Args:
            data: Source dictionary to convert
            model_cls: Target Pydantic model class

        Returns:
            Validated model instance

        Raises:
            TypeCoercionError: If validation fails (wraps Pydantic ValidationError)

        Performance:
            - Typical: 0.1-1ms (cached adapter)
            - Complex models: 1-5ms
            - Target: <10ms

        Example:
            >>> from anivault.services.tmdb import TMDBGenre
            >>> data = {"id": 16, "name": "Animation"}
            >>> genre = ModelConverter.to_model(data, TMDBGenre)
            >>> genre.name
            'Animation'
        """
        try:
            adapter = _get_type_adapter(model_cls)
            result = adapter.validate_python(data)
            return result  # type: ignore[return-value]
        except ValidationError as e:
            model_name = model_cls.__name__
            error_count = len(e.errors())
            # Convert ErrorDetails to dict for compatibility
            validation_errors = cast(
                "list[dict[str, Any]]", [dict(err) for err in e.errors()]
            )
            error_msg = (
                f"Failed to convert dict to {model_name}: "
                f"{error_count} validation error(s)"
            )
            # Lazy import to avoid circular dependency
            from anivault.shared.errors import create_type_coercion_error

            raise create_type_coercion_error(
                message=error_msg,
                model_name=model_name,
                validation_errors=validation_errors,
                operation="dict_to_model",
                original_error=e,
            ) from e

    @staticmethod
    def to_dict(
        model: BaseModel,
        *,
        mode: str = "json",
        by_alias: bool = True,
        exclude_none: bool = True,
    ) -> dict[str, Any]:
        """Convert Pydantic model to dictionary.

        This method uses Pydantic's model_dump for consistent serialization
        with configurable options for different use cases.

        Args:
            model: Source Pydantic model to convert
            mode: Serialization mode ("json" or "python")
                - "json": JSON-safe types (str, int, float, bool, None, list, dict)
                - "python": Python native types (may include date, datetime, etc.)
            by_alias: Use field aliases in output (default: True)
            exclude_none: Exclude None values from output (default: True)

        Returns:
            Dictionary representation of the model

        Performance:
            - Typical: 0.05-0.5ms
            - Target: <1ms

        Example:
            >>> from anivault.services.tmdb import TMDBGenre
            >>> genre = TMDBGenre(id=16, name="Animation")
            >>> result = ModelConverter.to_dict(genre)
            >>> result
            {'id': 16, 'name': 'Animation'}
        """
        return model.model_dump(
            mode=mode,
            by_alias=by_alias,
            exclude_none=exclude_none,
        )

    @staticmethod
    def to_json_bytes(
        model: BaseModel,
        *,
        by_alias: bool = True,
        exclude_none: bool = True,
    ) -> bytes:
        """Convert Pydantic model to JSON bytes using orjson.

        This method combines model_dump with orjson for high-performance
        JSON serialization. orjson is significantly faster than stdlib json
        and produces compact output.

        Args:
            model: Source Pydantic model to convert
            by_alias: Use field aliases in output (default: True)
            exclude_none: Exclude None values from output (default: True)

        Returns:
            UTF-8 encoded JSON bytes

        Performance:
            - orjson is 2-3x faster than stdlib json
            - Typical: 0.02-0.2ms
            - Target: <0.5ms

        Example:
            >>> from anivault.services.tmdb import TMDBGenre
            >>> genre = TMDBGenre(id=16, name="Animation")
            >>> result = ModelConverter.to_json_bytes(genre)
            >>> result
            b'{"id":16,"name":"Animation"}'
        """
        # Use model_dump with mode="json" for JSON-safe serialization
        data = model.model_dump(
            mode="json",
            by_alias=by_alias,
            exclude_none=exclude_none,
        )
        # orjson.dumps is faster than json.dumps and produces compact output
        return orjson.dumps(data)

    @staticmethod
    def to_json_str(
        model: BaseModel,
        *,
        by_alias: bool = True,
        exclude_none: bool = True,
    ) -> str:
        """Convert Pydantic model to JSON string using orjson.

        Convenience wrapper around to_json_bytes that returns a string.

        Args:
            model: Source Pydantic model to convert
            by_alias: Use field aliases in output (default: True)
            exclude_none: Exclude None values from output (default: True)

        Returns:
            JSON string (UTF-8)

        Example:
            >>> from anivault.services.tmdb import TMDBGenre
            >>> genre = TMDBGenre(id=16, name="Animation")
            >>> result = ModelConverter.to_json_str(genre)
            >>> result
            '{"id":16,"name":"Animation"}'
        """
        json_bytes = ModelConverter.to_json_bytes(
            model,
            by_alias=by_alias,
            exclude_none=exclude_none,
        )
        return json_bytes.decode("utf-8")

    @staticmethod
    def try_validate(data: Mapping[str, Any], model_cls: type[T]) -> T | None:
        """Attempt to convert dictionary to model, returning None on failure.

        This is a convenience method for cases where validation failure
        should be handled gracefully without exceptions.

        Args:
            data: Source dictionary to convert
            model_cls: Target Pydantic model class

        Returns:
            Validated model instance, or None if validation fails

        Example:
            >>> from anivault.services.tmdb import TMDBGenre
            >>> valid_data = {"id": 16, "name": "Animation"}
            >>> genre = ModelConverter.try_validate(valid_data, TMDBGenre)
            >>> genre.name if genre else "Failed"
            'Animation'
            >>> invalid_data = {"id": "not_an_int"}
            >>> result = ModelConverter.try_validate(invalid_data, TMDBGenre)
            >>> result is None
            True
        """
        try:
            return ModelConverter.to_model(data, model_cls)
        except ValidationError:
            return None
