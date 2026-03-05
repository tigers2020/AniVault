"""AniVault Exception Classes (Phase 4).

Exception hierarchy for structured error handling with context.
"""

from __future__ import annotations

from typing import Any

from anivault.shared.errors.codes import ErrorCode
from anivault.shared.errors.context import ErrorContextModel


class AniVaultError(Exception):
    """Base exception class for all AniVault errors."""

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        code: ErrorCode,
        message: str,
        context: ErrorContextModel | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """Initialize AniVaultError.

        Args:
            code: Error code from ErrorCode enum
            message: Human-readable error message
            context: Additional context information
            original_error: Original exception that caused this error
        """
        self.code = code
        self.message = message
        self.context = context or ErrorContextModel()
        self.original_error = original_error

        formatted_message = f"{code.value}: {message}"
        super().__init__(formatted_message)

    def __str__(self) -> str:
        """Return string representation of the error."""
        return f"{self.code.value}: {self.message}"

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for logging with PII masking."""
        return {
            "code": self.code.value,
            "message": self.message,
            "context": self.context.safe_dict(),
            "original_error": str(self.original_error) if self.original_error else None,
        }


class DomainError(AniVaultError):
    """Domain-specific errors (business logic, validation, parsing)."""


class InfrastructureError(AniVaultError):
    """Infrastructure-related errors (file system, network, APIs)."""


class AniVaultFileError(InfrastructureError):
    """File I/O related errors."""


class AniVaultPermissionError(InfrastructureError):
    """Permission-related errors."""


class AniVaultNetworkError(InfrastructureError):
    """Network-related errors."""


class AniVaultParsingError(DomainError):
    """Data parsing and processing errors."""


class ApplicationError(AniVaultError):
    """Application-level errors (config, CLI, app flow)."""


class DataProcessingError(AniVaultError):
    """Data processing errors."""


class SecurityError(AniVaultError):
    """Security-related errors."""


class CliError(ApplicationError):
    """CLI-specific error with enhanced context."""

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        code: ErrorCode,
        message: str,
        context: ErrorContextModel | None = None,
        original_error: Exception | None = None,
        command: str | None = None,
        exit_code: int = 1,
    ) -> None:
        super().__init__(code, message, context, original_error)
        self.command = command
        self.exit_code = exit_code


class TypeCoercionError(DomainError):
    """Exception raised when type conversion/coercion fails."""

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        code: ErrorCode,
        message: str,
        context: ErrorContextModel | None = None,
        original_error: Exception | None = None,
        model_name: str | None = None,
        validation_errors: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(code, message, context, original_error)
        self.model_name = model_name
        self.validation_errors = validation_errors or []
