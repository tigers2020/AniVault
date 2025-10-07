"""File permission utilities for AniVault security.

This module provides cross-platform utilities for setting secure file permissions,
ensuring sensitive data files are only accessible by the owner.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from anivault.shared.errors import ApplicationError, ErrorCode, ErrorContext

logger = logging.getLogger(__name__)


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
        error = ApplicationError(
            ErrorCode.PERMISSION_DENIED,
            f"Cannot set permissions: {file_path}",
            context,
            original_error=e,
        )
        logger.exception("Permission denied: %s", file_path)
        raise error from e
    except Exception as e:
        error = ApplicationError(
            ErrorCode.FILE_WRITE_ERROR,
            f"Failed to set permissions: {file_path}",
            context,
            original_error=e,
        )
        logger.exception("Failed to set permissions: %s", file_path)
        raise error from e


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
            "pywin32 not available, using basic chmod. "
            "For better security on Windows, install pywin32.",
        )
        # This provides minimal protection on Windows
        Path(file_path).chmod(0o600)
        logger.debug("Basic Windows permissions set for: %s", file_path)


def validate_api_key_not_in_data(data: dict[str, Any]) -> None:
    """Validate that data does not contain API keys or sensitive information.

    Args:
        data: Data dictionary to validate

    Raises:
        ApplicationError: If sensitive data is detected
    """
    sensitive_keys = {
        "api_key",
        "apikey",
        "api-key",
        "secret",
        "password",
        "token",
        "access_token",
        "refresh_token",
    }

    context = ErrorContext(
        operation="validate_api_key",
        additional_data={
            "data_keys": list(data.keys()) if isinstance(data, dict) else None,
        },
    )

    def check_dict(d: dict[str, Any], path: str = "") -> None:
        """Recursively check dictionary for sensitive keys."""
        for key, value in d.items():
            key_lower = key.lower()
            current_path = f"{path}.{key}" if path else key

            # Check if key matches sensitive patterns
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                error = ApplicationError(
                    ErrorCode.VALIDATION_ERROR,
                    f"Attempted to cache sensitive data: {current_path}",
                    context,
                )
                logger.error("Sensitive data detected in cache: %s", current_path)
                raise error

            # Recursively check nested dictionaries
            if isinstance(value, dict):
                check_dict(value, current_path)
            elif isinstance(value, list):
                for idx, item in enumerate(value):
                    if isinstance(item, dict):
                        check_dict(item, f"{current_path}[{idx}]")

    if isinstance(data, dict):
        check_dict(data)
