"""
Custom exceptions for file movement operations.

This module defines specific exceptions for handling various error conditions
that can occur during file movement, renaming, and transactional operations.
"""

from typing import Any


class AniVaultException(Exception):
    """Base exception class for all AniVault-specific exceptions."""

    def __init__(self, message: str, details: Any | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class FileMovementException(AniVaultException):
    """Base exception for file movement operations."""

    pass


class MoveRollbackError(FileMovementException):
    """
    Raised when a file movement operation fails and rollback cannot be completed.

    This exception indicates that the original file state cannot be restored
    after a failed move operation, potentially leaving the system in an
    inconsistent state.
    """

    def __init__(
        self,
        message: str,
        original_path: str,
        target_path: str,
        rollback_attempts: int = 0,
        details: Any | None = None,
    ) -> None:
        super().__init__(message, details)
        self.original_path = original_path
        self.target_path = target_path
        self.rollback_attempts = rollback_attempts


class MoveConflictError(FileMovementException):
    """
    Raised when a file movement operation encounters a naming conflict.

    This exception is raised when attempting to move a file to a location
    where a file with the same name already exists and cannot be resolved
    through automatic renaming.
    """

    def __init__(
        self,
        message: str,
        source_path: str,
        target_path: str,
        conflict_path: str,
        details: Any | None = None,
    ) -> None:
        super().__init__(message, details)
        self.source_path = source_path
        self.target_path = target_path
        self.conflict_path = conflict_path


class MovePermissionError(FileMovementException):
    """
    Raised when file movement fails due to insufficient permissions.

    This exception covers various permission-related issues including:
    - Read permission on source file
    - Write permission on target directory
    - Execute permission on parent directories
    """

    def __init__(
        self, message: str, path: str, required_permission: str, details: Any | None = None
    ) -> None:
        super().__init__(message, details)
        self.path = path
        self.required_permission = required_permission


class MoveDiskSpaceError(FileMovementException):
    """
    Raised when file movement fails due to insufficient disk space.

    This exception is raised when there's not enough space to complete
    the file movement operation, including temporary file creation.
    """

    def __init__(
        self,
        message: str,
        required_space: int,
        available_space: int,
        target_path: str,
        details: Any | None = None,
    ) -> None:
        super().__init__(message, details)
        self.required_space = required_space
        self.available_space = available_space
        self.target_path = target_path


class MoveValidationError(FileMovementException):
    """
    Raised when file movement fails validation checks.

    This exception covers various validation failures including:
    - File integrity checks
    - Path validation
    - File type validation
    """

    def __init__(
        self, message: str, validation_type: str, path: str, details: Any | None = None
    ) -> None:
        super().__init__(message, details)
        self.validation_type = validation_type
        self.path = path


class MoveTransactionError(FileMovementException):
    """
    Raised when a transactional file movement operation fails.

    This exception indicates that the entire transaction should be rolled back
    and provides information about which operations failed.
    """

    def __init__(
        self,
        message: str,
        failed_operations: list,
        transaction_id: str | None = None,
        details: Any | None = None,
    ) -> None:
        super().__init__(message, details)
        self.failed_operations = failed_operations
        self.transaction_id = transaction_id


class FileClassificationError(AniVaultException):
    """
    Raised when file classification fails.

    This exception covers errors in determining file resolution,
    quality, or other classification criteria.
    """

    def __init__(
        self, message: str, file_path: str, classification_type: str, details: Any | None = None
    ) -> None:
        super().__init__(message, details)
        self.file_path = file_path
        self.classification_type = classification_type


class FileNamingError(AniVaultException):
    """
    Raised when file naming operations fail.

    This exception covers errors in generating safe filenames,
    handling conflicts, or applying naming rules.
    """

    def __init__(
        self, message: str, original_name: str, target_name: str, details: Any | None = None
    ) -> None:
        super().__init__(message, details)
        self.original_name = original_name
        self.target_name = target_name
