"""File permission utilities for AniVault security.

This module provides cross-platform utilities for setting secure file permissions,
ensuring sensitive data files are only accessible by the owner.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from anivault.shared.errors import (
    AniVaultError,
    AniVaultFileError,
    AniVaultPermissionError,
    ApplicationError,
    ErrorCode,
    ErrorContext,
)

logger = logging.getLogger(__name__)

# Log message template for permission-setting failures (avoid S1192 literal duplication)
_MSG_FAILED_SET_PERMISSIONS = "Failed to set permissions: %s"


def set_secure_file_permissions(file_path: Path | str) -> None:
    """Set secure file permissions (600 - owner read/write only).

    Args:
        file_path: Path to the file to secure

    Raises:
        ApplicationError: If permission setting fails
    """
    file_path = Path(file_path)

    context = ErrorContext(
        operation="set_secure_file_permissions",
        file_path=str(file_path),
    )

    if not file_path.exists():
        error = ApplicationError(
            ErrorCode.FILE_NOT_FOUND,
            f"Cannot set permissions: file does not exist: {file_path}",
            context,
        )
        logger.error("File not found: %s", file_path)
        raise error

    try:
        if sys.platform == "win32":
            _set_windows_permissions(file_path)
        else:
            _set_unix_permissions(file_path)

        logger.info("Secure permissions set for: %s", file_path)

    except PermissionError as e:
        logger.exception("Permission denied: %s", file_path)
        raise AniVaultPermissionError(
            ErrorCode.PERMISSION_DENIED,
            f"Cannot set permissions: {file_path}",
            context,
            original_error=e,
        ) from e
    except OSError as e:
        if isinstance(e, FileNotFoundError):
            logger.exception(_MSG_FAILED_SET_PERMISSIONS, file_path)
            raise AniVaultFileError(
                ErrorCode.FILE_NOT_FOUND,
                f"File not found while setting permissions: {file_path}",
                context,
                original_error=e,
            ) from e
        logger.exception(_MSG_FAILED_SET_PERMISSIONS, file_path)
        raise AniVaultFileError(
            ErrorCode.FILE_WRITE_ERROR,
            f"File system error setting permissions: {file_path}",
            context,
            original_error=e,
        ) from e
    except Exception as e:
        logger.exception(_MSG_FAILED_SET_PERMISSIONS, file_path)
        raise AniVaultError(
            ErrorCode.FILE_WRITE_ERROR,
            f"Unexpected error setting permissions: {file_path}",
            context,
            original_error=e,
        ) from e


def _set_unix_permissions(file_path: Path) -> None:
    """Set Unix file permissions to 600 (owner read/write only).

    Args:
        file_path: Path to the file
    """
    # 600 = owner read/write, no access for group/others
    file_path.chmod(0o600)
    logger.debug("Unix permissions (600) set for: %s", file_path)


def _set_windows_permissions(file_path: Path) -> None:
    """Set Windows file permissions to owner-only access.

    Args:
        file_path: Path to the file

    Note:
        Windows permission model is complex. This implementation uses
        os.chmod as a best-effort approach. For production environments,
        consider using pywin32 or icacls for more granular control.
    """
    try:
        # Try to import win32security for proper ACL management
        # pylint: disable=import-outside-toplevel
        # Windows-only import
        import ntsecuritycon as con
        import win32security

        # Get current user's SID
        user_sid = win32security.GetFileSecurity(
            str(file_path),
            win32security.OWNER_SECURITY_INFORMATION,
        ).GetSecurityDescriptorOwner()

        # Create new DACL with owner-only access
        dacl = win32security.ACL()
        dacl.AddAccessAllowedAce(
            win32security.ACL_REVISION,
            con.FILE_ALL_ACCESS,
            user_sid,
        )

        # Set new security descriptor
        sd = win32security.SECURITY_DESCRIPTOR()
        sd.SetSecurityDescriptorDacl(1, dacl, 0)

        win32security.SetFileSecurity(
            str(file_path),
            win32security.DACL_SECURITY_INFORMATION,
            sd,
        )

        logger.debug("Windows ACL (owner-only) set for: %s", file_path)

    except ImportError:
        # Fallback to basic chmod if pywin32 is not available
        logger.warning(
            "pywin32 not available, using basic chmod. For better security on Windows, install pywin32.",
        )
        # This provides minimal protection on Windows
        Path(file_path).chmod(0o600)
        logger.debug("Basic Windows permissions set for: %s", file_path)


_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "api-key",
        "secret",
        "password",
        "token",
        "access_token",
        "refresh_token",
    }
)


def _key_is_sensitive(key: str) -> bool:
    """Return True if key matches any sensitive pattern."""
    key_lower = key.lower()
    return any(s in key_lower for s in _SENSITIVE_KEYS)


def _raise_sensitive_data_error(path: str, context: ErrorContext) -> None:
    """Raise ApplicationError for sensitive data at path."""
    error = ApplicationError(
        ErrorCode.VALIDATION_ERROR,
        f"Attempted to cache sensitive data: {path}",
        context,
    )
    logger.error("Sensitive data detected in cache: %s", path)
    raise error


def _check_nested_value(
    value: Any,
    current_path: str,
    context: ErrorContext,
) -> None:
    """Recursively check nested dict/list for sensitive keys."""
    if isinstance(value, dict):
        _check_dict_recursive(value, current_path, context)
    elif isinstance(value, list):
        for idx, item in enumerate(value):
            if isinstance(item, dict):
                _check_dict_recursive(item, f"{current_path}[{idx}]", context)


def _check_dict_recursive(
    d: dict[str, Any],
    path: str,
    context: ErrorContext,
) -> None:
    """Recursively check dictionary for sensitive keys."""
    for key, value in d.items():
        current_path = f"{path}.{key}" if path else key
        if _key_is_sensitive(key):
            _raise_sensitive_data_error(current_path, context)
        _check_nested_value(value, current_path, context)


def validate_api_key_not_in_data(data: dict[str, Any]) -> None:
    """Validate that data does not contain API keys or sensitive information.

    Args:
        data: Data dictionary to validate

    Raises:
        ApplicationError: If sensitive data is detected
    """
    additional_data: dict[str, str | int | float | bool] = {
        "data_keys_count": len(data),
    }
    context = ErrorContext(
        operation="validate_api_key",
        additional_data=additional_data,
    )
    _check_dict_recursive(data, "", context)
