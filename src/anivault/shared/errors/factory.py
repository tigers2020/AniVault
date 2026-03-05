"""AniVault Error Factory Functions (Phase 4).

Convenience functions for creating common error instances.
"""

from __future__ import annotations

from typing import Any

from anivault.shared.errors.codes import ErrorCode
from anivault.shared.errors.context import ErrorContextModel, PrimitiveContextValue
from anivault.shared.errors.exceptions import (
    ApplicationError,
    CliError,
    DataProcessingError,
    DomainError,
    InfrastructureError,
    TypeCoercionError,
)


def create_file_not_found_error(
    file_path: str,
    operation: str | None = None,
    original_error: Exception | None = None,
) -> InfrastructureError:
    """Create a file not found error with context."""
    context = ErrorContextModel(
        file_path=file_path,
        operation=operation,
    )
    return InfrastructureError(
        ErrorCode.FILE_NOT_FOUND,
        f"File not found: {file_path}",
        context,
        original_error,
    )


def create_permission_denied_error(
    path: str,
    operation: str | None = None,
    original_error: Exception | None = None,
) -> InfrastructureError:
    """Create a permission denied error with context."""
    context = ErrorContextModel(
        file_path=path,
        operation=operation,
    )
    return InfrastructureError(
        ErrorCode.PERMISSION_DENIED,
        f"Permission denied: {path}",
        context,
        original_error,
    )


def create_validation_error(
    message: str,
    field: str | None = None,
    operation: str | None = None,
    original_error: Exception | None = None,
) -> DomainError:
    """Create a validation error with context."""
    additional_data: dict[str, PrimitiveContextValue] | None = {"field": field} if field else None
    context = ErrorContextModel(
        operation=operation,
        additional_data=additional_data,
    )
    return DomainError(
        ErrorCode.VALIDATION_ERROR,
        message,
        context,
        original_error,
    )


def create_api_error(
    message: str,
    operation: str | None = None,
    original_error: Exception | None = None,
) -> InfrastructureError:
    """Create an API error with context."""
    context = ErrorContextModel(
        operation=operation,
    )
    return InfrastructureError(
        ErrorCode.API_REQUEST_FAILED,
        message,
        context,
        original_error,
    )


def create_parsing_error(
    message: str,
    file_path: str | None = None,
    operation: str | None = None,
    original_error: Exception | None = None,
) -> DomainError:
    """Create a parsing error with context."""
    context = ErrorContextModel(
        file_path=file_path,
        operation=operation,
    )
    return DomainError(
        ErrorCode.PARSING_ERROR,
        message,
        context,
        original_error,
    )


def create_config_error(
    message: str,
    config_key: str | None = None,
    operation: str | None = None,
    original_error: Exception | None = None,
) -> ApplicationError:
    """Create a configuration error with context."""
    additional_data: dict[str, PrimitiveContextValue] | None = {"config_key": config_key} if config_key else None
    context = ErrorContextModel(
        operation=operation,
        additional_data=additional_data,
    )
    return ApplicationError(
        ErrorCode.CONFIG_ERROR,
        message,
        context,
        original_error,
    )


def create_data_processing_error(
    message: str,
    field: str | None = None,
    operation: str | None = None,
    original_error: Exception | None = None,
) -> DataProcessingError:
    """Create a data processing error with context."""
    additional_data: dict[str, PrimitiveContextValue] | None = {"field": field} if field else None
    context = ErrorContextModel(
        operation=operation,
        additional_data=additional_data,
    )
    return DataProcessingError(
        ErrorCode.DATA_PROCESSING_ERROR,
        message,
        context,
        original_error,
    )


def create_cli_error(
    message: str,
    command: str | None = None,
    operation: str | None = None,
    original_error: Exception | None = None,
    exit_code: int = 1,
) -> CliError:
    """Create a CLI error with context."""
    additional_data: dict[str, PrimitiveContextValue] | None = {"command": command} if command else None
    context = ErrorContextModel(
        operation=operation,
        additional_data=additional_data,
    )
    return CliError(
        ErrorCode.CLI_UNEXPECTED_ERROR,
        message,
        context,
        original_error,
        command,
        exit_code,
    )


def create_cli_output_error(
    message: str,
    command: str | None = None,
    output_type: str | None = None,
    original_error: Exception | None = None,
) -> CliError:
    """Create a CLI output error with context."""
    additional_data: dict[str, PrimitiveContextValue] = {}
    if command is not None:
        additional_data["command"] = command
    if output_type is not None:
        additional_data["output_type"] = output_type

    context = ErrorContextModel(
        operation="cli_output",
        additional_data=additional_data if additional_data else None,
    )
    return CliError(
        ErrorCode.CLI_OUTPUT_ERROR,
        message,
        context,
        original_error,
        command,
        exit_code=1,
    )


def create_type_coercion_error(
    message: str,
    model_name: str,
    validation_errors: list[dict[str, Any]] | None = None,
    operation: str | None = None,
    original_error: Exception | None = None,
) -> TypeCoercionError:
    """Create a type coercion error with context."""
    additional_data: dict[str, PrimitiveContextValue] = {
        "model_name": model_name,
        "validation_error_count": len(validation_errors) if validation_errors else 0,
    }
    context = ErrorContextModel(
        operation=operation or "type_conversion",
        additional_data=additional_data,
    )
    return TypeCoercionError(
        code=ErrorCode.TYPE_COERCION_ERROR,
        message=message,
        context=context,
        original_error=original_error,
        model_name=model_name,
        validation_errors=validation_errors,
    )
