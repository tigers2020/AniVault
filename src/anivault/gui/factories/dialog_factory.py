"""Dialog Factory for creating dialog instances.

This module contains the DialogFactory class that centralizes dialog creation
logic, making it easier to manage dialog instantiation and configuration.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

    from anivault.gui.dialogs.organize_preview_dialog import OrganizePreviewDialog
    from anivault.gui.dialogs.organize_progress_dialog import OrganizeProgressDialog
    from anivault.gui.dialogs.settings_dialog import SettingsDialog
    from anivault.gui.dialogs.tmdb_progress_dialog import TMDBProgressDialog


class DialogFactory:
    """Factory for creating dialog instances.

    This class centralizes dialog creation logic, providing a consistent
    interface for instantiating various dialogs used throughout the application.

    Benefits:
    - Centralized dialog creation logic
    - Consistent dialog configuration
    - Easier testing through dependency injection
    - Single point of change for dialog instantiation

    Example:
        >>> factory = DialogFactory()
        >>> dialog = factory.create_settings_dialog(parent, config_path)
        >>> dialog.exec()
    """

    @staticmethod
    def create_tmdb_progress_dialog(
        parent: QWidget | None = None,
    ) -> TMDBProgressDialog:
        """Create a TMDB progress dialog.

        Args:
            parent: Parent widget for the dialog

        Returns:
            TMDBProgressDialog: Configured TMDB progress dialog instance
        """
        from anivault.gui.dialogs.tmdb_progress_dialog import TMDBProgressDialog

        return TMDBProgressDialog(parent)

    @staticmethod
    def create_settings_dialog(
        parent: QWidget | None,
        config_path: Path,
    ) -> SettingsDialog:
        """Create a settings dialog.

        Args:
            parent: Parent widget for the dialog
            config_path: Path to the configuration file

        Returns:
            SettingsDialog: Configured settings dialog instance
        """
        from anivault.gui.dialogs.settings_dialog import SettingsDialog

        return SettingsDialog(parent, config_path)

    @staticmethod
    def create_organize_preview_dialog(
        plan: list[Any],
        parent: QWidget | None = None,
    ) -> OrganizePreviewDialog:
        """Create an organize preview dialog.

        Args:
            plan: List of FileOperation objects to preview
            parent: Parent widget for the dialog

        Returns:
            OrganizePreviewDialog: Configured preview dialog instance
        """
        from anivault.gui.dialogs.organize_preview_dialog import OrganizePreviewDialog

        return OrganizePreviewDialog(plan, parent)

    @staticmethod
    def create_organize_progress_dialog(
        total_files: int,
        parent: QWidget | None = None,
    ) -> OrganizeProgressDialog:
        """Create an organize progress dialog.

        Args:
            total_files: Total number of files to be organized
            parent: Parent widget for the dialog

        Returns:
            OrganizeProgressDialog: Configured progress dialog instance
        """
        from anivault.gui.dialogs.organize_progress_dialog import OrganizeProgressDialog

        return OrganizeProgressDialog(total_files, parent)
