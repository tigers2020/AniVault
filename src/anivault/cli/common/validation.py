"""
Pydantic validation utilities for CLI commands.

This module provides reusable validation models and Typer callbacks
for consistent argument validation across CLI commands.
"""

from __future__ import annotations

import re
from typing import Any, Callable

import typer
from pydantic import BaseModel, ValidationError, field_validator


def create_validator(model: type[BaseModel]) -> Callable[[Any], Any]:
    """
    Create a Typer callback function for Pydantic model validation.

    Args:
        model: Pydantic model class to validate against

    Returns:
        Typer callback function that validates input against the model

    Example:
        >>> validator = create_validator(DirectoryPath)
        >>> typer.Option(..., callback=validator)
    """

    def validator(value: Any) -> Any:
        """Validate value against the Pydantic model."""
        try:
            # Create model instance with the value
            if hasattr(model, "model_fields") and "path" in model.model_fields:
                instance = model(path=value)
                return instance.path
            instance = model(value=value)
            return instance.value
        except ValidationError as e:
            # Convert Pydantic validation error to Typer BadParameter
            error_messages = []
            for error in e.errors():
                field = error.get("loc", ("unknown",))[-1]
                message = error.get("msg", "Validation failed")
                error_messages.append(f"{field}: {message}")

            msg = f"Validation failed: {'; '.join(error_messages)}"
            raise typer.BadParameter(
                msg,
            ) from e
        except Exception as e:
            msg = f"Unexpected validation error: {e}"
            raise typer.BadParameter(msg) from e

    return validator


class NamingFormat(BaseModel):
    """Validated naming format string model."""

    value: str

    @field_validator("value", mode="before")
    @classmethod
    def validate_format_string(cls, v: Any) -> str:
        """Validate the naming format string."""
        if isinstance(v, dict):
            # Handle case where value is passed as dict
            if "format_string" in v:
                v = v["format_string"]
            elif "value" in v:
                v = v["value"]

        format_str = str(v)

        # Check for valid placeholders
        valid_placeholders = {
            "{series_name}",
            "{season}",
            "{episode}",
            "{title}",
            "{year}",
            "{quality}",
            "{resolution}",
            "{codec}",
        }

        # Find all placeholders in the format string (including format specifiers like :02d)
        placeholder_pattern = r"\{([^}:]+)(?::[^}]*)?\}"
        found_placeholders = set(re.findall(placeholder_pattern, format_str))
        # Convert to full placeholder format
        found_placeholders = {f"{{{p}}}" for p in found_placeholders}

        # Check for unclosed curly braces first
        open_braces = format_str.count("{")
        close_braces = format_str.count("}")
        if open_braces != close_braces:
            msg = f"Format string has mismatched braces: {open_braces} opening, {close_braces} closing"
            raise ValueError(
                msg,
            )

        # Check for invalid placeholders
        invalid_placeholders = found_placeholders - valid_placeholders
        if invalid_placeholders:
            msg = (
                f"Invalid placeholders found: {', '.join(sorted(invalid_placeholders))}. "
                f"Valid placeholders: {', '.join(sorted(valid_placeholders))}"
            )
            raise ValueError(
                msg,
            )

        # Check if at least one valid placeholder is present
        if not any(
            placeholder in valid_placeholders for placeholder in found_placeholders
        ):
            msg = (
                f"Format string must contain at least one valid placeholder. "
                f"Valid placeholders: {', '.join(sorted(valid_placeholders))}"
            )
            raise ValueError(
                msg,
            )

        return format_str
