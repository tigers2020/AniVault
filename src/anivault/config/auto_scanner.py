"""
Auto Scanner Module

This module provides automatic scanning functionality for the AniVault application.
It handles startup scanning and periodic scanning based on configuration settings.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from anivault.config.folder_validator import FolderValidator
from anivault.config.validation import FolderSettings
from anivault.shared.errors import ApplicationError, ErrorCode, ErrorContext

logger = logging.getLogger(__name__)


class AutoScanner:
    """Handles automatic scanning of configured folders."""

    def __init__(self, config_manager: Any) -> None:
        """Initialize the auto scanner.

        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.scan_callback: Callable[[str], None] | None = None
        self._scan_in_progress = False

    def set_scan_callback(self, callback: Callable[[str], None]) -> None:
        """Set the callback function to execute when scanning.

        Args:
            callback: Function to call with folder path when scanning
        """
        self.scan_callback = callback

    def should_auto_scan_on_startup(self) -> tuple[bool, str]:
        """Check if auto scan should run on startup.

        Returns:
            Tuple of (should_scan, source_folder_path)
        """
        try:
            config = self.config_manager.load_config()
            folder_settings = config.folders

            # Check if auto scan is enabled
            if not folder_settings.auto_scan_on_startup:
                return False, ""

            # Check if source folder is configured
            source_folder = folder_settings.source_folder
            if not source_folder or not source_folder.strip():
                logger.warning("Auto scan enabled but no source folder configured")
                return False, ""

            # Validate source folder
            is_valid, error = FolderValidator.validate_folder_path(source_folder)
            if not is_valid:
                logger.warning("Auto scan enabled but source folder invalid: %s", error)
                return False, ""

            logger.info("Auto scan on startup enabled for folder: %s", source_folder)
            return True, source_folder

        except Exception as e:
            logger.exception("Error checking auto scan startup condition")
            context = ErrorContext(operation="should_auto_scan_on_startup")
            raise ApplicationError(
                ErrorCode.CONFIGURATION_ERROR,
                "Failed to check auto scan configuration",
                context,
                e,
            ) from e

    def get_auto_scan_interval(self) -> int:
        """Get the auto scan interval in minutes.

        Returns:
            Scan interval in minutes (0 if disabled)
        """
        try:
            config = self.config_manager.load_config()
            return config.folders.auto_scan_interval_minutes
        except Exception as e:
            logger.exception("Error getting auto scan interval: %s", e)
            return 0

    def can_auto_scan(self) -> tuple[bool, str]:
        """Check if auto scan can be performed.

        Returns:
            Tuple of (can_scan, reason_if_not)
        """
        if self._scan_in_progress:
            return False, "Scan already in progress"

        if not self.scan_callback:
            return False, "No scan callback configured"

        try:
            config = self.config_manager.load_config()
            folder_settings = config.folders

            # Check if source folder is configured
            source_folder = folder_settings.source_folder
            if not source_folder or not source_folder.strip():
                return False, "No source folder configured"

            # Validate source folder
            is_valid, error = FolderValidator.validate_folder_path(source_folder)
            if not is_valid:
                return False, f"Source folder invalid: {error}"

            return True, ""

        except Exception as e:
            return False, f"Configuration error: {e}"

    def perform_auto_scan(self) -> tuple[bool, str]:
        """Perform automatic scan if conditions are met.

        Returns:
            Tuple of (success, message)
        """
        can_scan, reason = self.can_auto_scan()
        if not can_scan:
            logger.info("Auto scan skipped: %s", reason)
            return False, reason

        try:
            config = self.config_manager.load_config()
            source_folder = config.folders.source_folder

            logger.info("Starting auto scan for folder: %s", source_folder)
            self._scan_in_progress = True

            # Execute the scan callback
            if self.scan_callback:
                self.scan_callback(source_folder)

            logger.info("Auto scan completed successfully")
            return True, "Auto scan completed"

        except Exception as e:
            logger.exception("Auto scan failed: %s", e)
            return False, f"Auto scan failed: {e}"
        finally:
            self._scan_in_progress = False

    def get_folder_settings(self) -> FolderSettings:
        """Get current folder settings.

        Returns:
            FolderSettings object

        Raises:
            ApplicationError: If failed to retrieve folder settings
        """
        try:
            config = self.config_manager.load_config()
            return config.folders
        except Exception as e:
            logger.exception("Error getting folder settings")
            context = ErrorContext(operation="get_folder_settings")
            raise ApplicationError(
                ErrorCode.CONFIGURATION_ERROR,
                "Failed to retrieve folder settings",
                context,
                e,
            ) from e

    def update_folder_settings(
        self,
        source_folder: str = "",
        target_folder: str = "",
        auto_scan_on_startup: bool = False,
        auto_scan_interval_minutes: int = 0,
        include_subdirectories: bool = True,
    ) -> tuple[bool, str]:
        """Update folder settings in configuration.

        Args:
            source_folder: Source folder path
            target_folder: Target folder path
            auto_scan_on_startup: Enable auto scan on startup
            auto_scan_interval_minutes: Auto scan interval in minutes
            include_subdirectories: Include subdirectories when scanning

        Returns:
            Tuple of (success, error_message)
        """
        try:
            config = self.config_manager.load_config()

            # Update folder settings
            config.folders.source_folder = source_folder
            config.folders.target_folder = target_folder
            config.folders.auto_scan_on_startup = auto_scan_on_startup
            config.folders.auto_scan_interval_minutes = auto_scan_interval_minutes
            config.folders.include_subdirectories = include_subdirectories

            # Validate the updated configuration
            errors = self.config_manager.validate_config()
            if errors:
                return False, f"Configuration validation failed: {', '.join(errors)}"

            # Save the configuration
            self.config_manager.save_config(config)

            logger.info("Folder settings updated successfully")
            return True, ""

        except Exception as e:
            logger.exception("Error updating folder settings: %s", e)
            return False, f"Failed to update folder settings: {e}"

    def get_scan_status(self) -> dict[str, Any]:
        """Get current scan status information.

        Returns:
            Dictionary with scan status information
        """
        try:
            folder_settings = self.get_folder_settings()
            can_scan, reason = self.can_auto_scan()

            return {
                "enabled": bool(folder_settings.source_folder),
                "source_folder": folder_settings.source_folder,
                "target_folder": folder_settings.target_folder,
                "auto_scan_on_startup": folder_settings.auto_scan_on_startup,
                "auto_scan_interval_minutes": folder_settings.auto_scan_interval_minutes,
                "include_subdirectories": folder_settings.include_subdirectories,
                "can_scan": can_scan,
                "scan_in_progress": self._scan_in_progress,
                "error": "" if can_scan else reason,
            }

        except ApplicationError as e:
            # ApplicationError from get_folder_settings - contains detailed context
            logger.exception("Error getting scan status")
            return {
                "enabled": False,
                "source_folder": "",
                "target_folder": "",
                "auto_scan_on_startup": False,
                "auto_scan_interval_minutes": 0,
                "include_subdirectories": True,
                "can_scan": False,
                "scan_in_progress": self._scan_in_progress,
                "error": f"Failed to get scan status: {e.message}",
            }
        except Exception as e:
            # Unexpected errors
            logger.exception("Unexpected error getting scan status")
            return {
                "enabled": False,
                "source_folder": "",
                "target_folder": "",
                "auto_scan_on_startup": False,
                "auto_scan_interval_minutes": 0,
                "include_subdirectories": True,
                "can_scan": False,
                "scan_in_progress": self._scan_in_progress,
                "error": f"Unexpected error getting scan status: {e}",
            }
