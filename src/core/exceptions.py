"""Custom exceptions for file movement operations.

This module defines specific exceptions for handling various error conditions
that can occur during file movement, renaming, and transactional operations.
"""

from typing import Union

# Type alias for exception details
ExceptionDetails = Union[str, int, float, bool, list, dict, None]


class AniVaultException(Exception):
    """Base exception class for all AniVault-specific exceptions."""

    def __init__(self, message: str, details: ExceptionDetails | None = None) -> None:
        """Initialize the AniVault exception.

        Args:
            message (str): The error message describing the exception.
            details (Any | None, optional): Additional details about the exception. Defaults to None.
        """
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        """Return a string representation of the exception.

        Returns:
            str: The exception message with optional details.
        """
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class FileMovementException(AniVaultException):
    """Base exception for file movement operations."""

    pass


class MoveRollbackError(FileMovementException):
    """Raised when a file movement operation fails and rollback cannot be completed.

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
        details: ExceptionDetails | None = None,
    ) -> None:
        """Initialize the move rollback error.

        Args:
            message (str): The error message describing the rollback failure.
            original_path (str): The original file path before the move attempt.
            target_path (str): The target file path for the move operation.
            rollback_attempts (int, optional): Number of rollback attempts made. Defaults to 0.
            details (Any | None, optional): Additional details about the error. Defaults to None.
        """
        super().__init__(message, details)
        self.original_path = original_path
        self.target_path = target_path
        self.rollback_attempts = rollback_attempts


class MoveConflictError(FileMovementException):
    """Raised when a file movement operation encounters a naming conflict.

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
        details: ExceptionDetails | None = None,
    ) -> None:
        """Initialize the move conflict error.

        Args:
            message (str): The error message describing the naming conflict.
            source_path (str): The source file path of the move operation.
            target_path (str): The intended target file path.
            conflict_path (str): The path where the naming conflict occurred.
            details (Any | None, optional): Additional details about the error. Defaults to None.
        """
        super().__init__(message, details)
        self.source_path = source_path
        self.target_path = target_path
        self.conflict_path = conflict_path


class MovePermissionError(FileMovementException):
    """Raised when file movement fails due to insufficient permissions.

    This exception covers various permission-related issues including:
    - Read permission on source file
    - Write permission on target directory
    - Execute permission on parent directories
    """

    def __init__(
        self,
        message: str,
        path: str,
        required_permission: str,
        details: ExceptionDetails | None = None,
    ) -> None:
        """Initialize the move permission error.

        Args:
            message (str): The error message describing the permission issue.
            path (str): The file or directory path where permission was denied.
            required_permission (str): The specific permission that was required.
            details (Any | None, optional): Additional details about the error. Defaults to None.
        """
        super().__init__(message, details)
        self.path = path
        self.required_permission = required_permission


class MoveDiskSpaceError(FileMovementException):
    """Raised when file movement fails due to insufficient disk space.

    This exception is raised when there's not enough space to complete
    the file movement operation, including temporary file creation.
    """

    def __init__(
        self,
        message: str,
        required_space: int,
        available_space: int,
        target_path: str,
        details: ExceptionDetails | None = None,
    ) -> None:
        """Initialize the move disk space error.

        Args:
            message (str): The error message describing the disk space issue.
            required_space (int): The amount of disk space required in bytes.
            available_space (int): The amount of disk space available in bytes.
            target_path (str): The target path where space was insufficient.
            details (Any | None, optional): Additional details about the error. Defaults to None.
        """
        super().__init__(message, details)
        self.required_space = required_space
        self.available_space = available_space
        self.target_path = target_path


class MoveValidationError(FileMovementException):
    """Raised when file movement fails validation checks.

    This exception covers various validation failures including:
    - File integrity checks
    - Path validation
    - File type validation
    """

    def __init__(
        self,
        message: str,
        validation_type: str,
        path: str,
        details: ExceptionDetails | None = None,
    ) -> None:
        """Initialize the move validation error.

        Args:
            message (str): The error message describing the validation failure.
            validation_type (str): The type of validation that failed.
            path (str): The file path that failed validation.
            details (Any | None, optional): Additional details about the error. Defaults to None.
        """
        super().__init__(message, details)
        self.validation_type = validation_type
        self.path = path


class MoveTransactionError(FileMovementException):
    """Raised when a transactional file movement operation fails.

    This exception indicates that the entire transaction should be rolled back
    and provides information about which operations failed.
    """

    def __init__(
        self,
        message: str,
        failed_operations: list,
        transaction_id: str | None = None,
        details: ExceptionDetails | None = None,
    ) -> None:
        """Initialize the move transaction error.

        Args:
            message (str): The error message describing the transaction failure.
            failed_operations (list): List of operations that failed in the transaction.
            transaction_id (str | None, optional): Unique identifier for the failed transaction. Defaults to None.
            details (Any | None, optional): Additional details about the error. Defaults to None.
        """
        super().__init__(message, details)
        self.failed_operations = failed_operations
        self.transaction_id = transaction_id


class FileClassificationError(AniVaultException):
    """Raised when file classification fails.

    This exception covers errors in determining file resolution,
    quality, or other classification criteria.
    """

    def __init__(
        self,
        message: str,
        file_path: str,
        classification_type: str,
        details: ExceptionDetails | None = None,
    ) -> None:
        """Initialize the file classification error.

        Args:
            message (str): The error message describing the classification failure.
            file_path (str): The path to the file that could not be classified.
            classification_type (str): The type of classification that failed.
            details (Any | None, optional): Additional details about the error. Defaults to None.
        """
        super().__init__(message, details)
        self.file_path = file_path
        self.classification_type = classification_type


class FileNamingError(AniVaultException):
    """Raised when file naming operations fail.

    This exception covers errors in generating safe filenames,
    handling conflicts, or applying naming rules.
    """

    def __init__(
        self,
        message: str,
        original_name: str,
        target_name: str,
        details: ExceptionDetails | None = None,
    ) -> None:
        """Initialize the file naming error.

        Args:
            message (str): The error message describing the naming failure.
            original_name (str): The original filename that caused the error.
            target_name (str): The intended target filename.
            details (Any | None, optional): Additional details about the error. Defaults to None.
        """
        super().__init__(message, details)
        self.original_name = original_name
        self.target_name = target_name
