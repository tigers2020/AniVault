"""AniVault Error Handling Package (Phase 4).

Structured error classes, context, and factory functions.
"""

from __future__ import annotations

from anivault.shared.errors.codes import ErrorCode
from anivault.shared.errors.context import (
    SAFE_DICT_MASK_KEYS,
    ErrorContext,
    ErrorContextModel,
    PrimitiveContextValue,
)
from anivault.shared.errors.exceptions import (
    AniVaultError,
    AniVaultFileError,
    AniVaultNetworkError,
    AniVaultParsingError,
    AniVaultPermissionError,
    ApplicationError,
    CliError,
    DataProcessingError,
    DomainError,
    InfrastructureError,
    SecurityError,
    TypeCoercionError,
)
from anivault.shared.errors.factory import (
    create_api_error,
    create_cli_error,
    create_cli_output_error,
    create_config_error,
    create_data_processing_error,
    create_file_not_found_error,
    create_parsing_error,
    create_permission_denied_error,
    create_type_coercion_error,
    create_validation_error,
)

__all__ = [
    "SAFE_DICT_MASK_KEYS",
    # Exceptions
    "AniVaultError",
    "AniVaultFileError",
    "AniVaultNetworkError",
    "AniVaultParsingError",
    "AniVaultPermissionError",
    "ApplicationError",
    "CliError",
    "DataProcessingError",
    "DomainError",
    # Codes
    "ErrorCode",
    # Context
    "ErrorContext",
    "ErrorContextModel",
    "InfrastructureError",
    "PrimitiveContextValue",
    "SecurityError",
    "TypeCoercionError",
    # Factory
    "create_api_error",
    "create_cli_error",
    "create_cli_output_error",
    "create_config_error",
    "create_data_processing_error",
    "create_file_not_found_error",
    "create_parsing_error",
    "create_permission_denied_error",
    "create_type_coercion_error",
    "create_validation_error",
]
