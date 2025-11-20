"""Unit tests for DialogFactory.

This module tests the DialogFactory class, which centralizes dialog creation
logic for the AniVault GUI application.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from anivault.gui.factories.dialog_factory import DialogFactory


class TestDialogFactory:
    """Tests for DialogFactory class."""

    def test_factory_instantiation(self) -> None:
        """Test that DialogFactory can be instantiated."""
        factory = DialogFactory()
        assert factory is not None

    @patch("anivault.gui.dialogs.tmdb_progress_dialog.TMDBProgressDialog")
    def test_create_tmdb_progress_dialog(self, mock_dialog_class: Mock) -> None:
        """Test creating TMDB progress dialog."""
        factory = DialogFactory()
        parent = Mock()

        result = factory.create_tmdb_progress_dialog(parent)

        mock_dialog_class.assert_called_once_with(parent)
        assert result == mock_dialog_class.return_value

    @patch("anivault.gui.dialogs.tmdb_progress_dialog.TMDBProgressDialog")
    def test_create_tmdb_progress_dialog_without_parent(
        self,
        mock_dialog_class: Mock,
    ) -> None:
        """Test creating TMDB progress dialog without parent."""
        factory = DialogFactory()

        result = factory.create_tmdb_progress_dialog(None)

        mock_dialog_class.assert_called_once_with(None)
        assert result == mock_dialog_class.return_value

    @patch("anivault.gui.dialogs.settings_dialog.SettingsDialog")
    def test_create_settings_dialog(self, mock_dialog_class: Mock) -> None:
        """Test creating settings dialog."""
        factory = DialogFactory()
        parent = Mock()
        config_path = Path("/test/config.json")

        result = factory.create_settings_dialog(parent, config_path)

        mock_dialog_class.assert_called_once_with(parent, config_path)
        assert result == mock_dialog_class.return_value

    @patch("anivault.gui.dialogs.settings_dialog.SettingsDialog")
    def test_create_settings_dialog_without_parent(
        self,
        mock_dialog_class: Mock,
    ) -> None:
        """Test creating settings dialog without parent."""
        factory = DialogFactory()
        config_path = Path("/test/config.json")

        result = factory.create_settings_dialog(None, config_path)

        mock_dialog_class.assert_called_once_with(None, config_path)
        assert result == mock_dialog_class.return_value

    @patch("anivault.gui.dialogs.organize_preview_dialog.OrganizePreviewDialog")
    def test_create_organize_preview_dialog(self, mock_dialog_class: Mock) -> None:
        """Test creating organize preview dialog."""
        factory = DialogFactory()
        parent = Mock()
        plan = [Mock(), Mock(), Mock()]

        result = factory.create_organize_preview_dialog(plan, parent)

        mock_dialog_class.assert_called_once_with(plan, parent)
        assert result == mock_dialog_class.return_value

    @patch("anivault.gui.dialogs.organize_preview_dialog.OrganizePreviewDialog")
    def test_create_organize_preview_dialog_without_parent(
        self,
        mock_dialog_class: Mock,
    ) -> None:
        """Test creating organize preview dialog without parent."""
        factory = DialogFactory()
        plan = [Mock(), Mock()]

        result = factory.create_organize_preview_dialog(plan, None)

        mock_dialog_class.assert_called_once_with(plan, None)
        assert result == mock_dialog_class.return_value

    @patch("anivault.gui.dialogs.organize_preview_dialog.OrganizePreviewDialog")
    def test_create_organize_preview_dialog_with_empty_plan(
        self,
        mock_dialog_class: Mock,
    ) -> None:
        """Test creating organize preview dialog with empty plan."""
        factory = DialogFactory()
        parent = Mock()
        plan: list[Mock] = []

        result = factory.create_organize_preview_dialog(plan, parent)

        mock_dialog_class.assert_called_once_with(plan, parent)
        assert result == mock_dialog_class.return_value

    @patch("anivault.gui.dialogs.organize_progress_dialog.OrganizeProgressDialog")
    def test_create_organize_progress_dialog(self, mock_dialog_class: Mock) -> None:
        """Test creating organize progress dialog."""
        factory = DialogFactory()
        parent = Mock()
        total_files = 10

        result = factory.create_organize_progress_dialog(total_files, parent)

        mock_dialog_class.assert_called_once_with(total_files, parent)
        assert result == mock_dialog_class.return_value

    @patch("anivault.gui.dialogs.organize_progress_dialog.OrganizeProgressDialog")
    def test_create_organize_progress_dialog_without_parent(
        self,
        mock_dialog_class: Mock,
    ) -> None:
        """Test creating organize progress dialog without parent."""
        factory = DialogFactory()
        total_files = 5

        result = factory.create_organize_progress_dialog(total_files, None)

        mock_dialog_class.assert_called_once_with(total_files, None)
        assert result == mock_dialog_class.return_value

    @patch("anivault.gui.dialogs.organize_progress_dialog.OrganizeProgressDialog")
    def test_create_organize_progress_dialog_with_zero_files(
        self,
        mock_dialog_class: Mock,
    ) -> None:
        """Test creating organize progress dialog with zero files."""
        factory = DialogFactory()
        parent = Mock()
        total_files = 0

        result = factory.create_organize_progress_dialog(total_files, parent)

        mock_dialog_class.assert_called_once_with(total_files, parent)
        assert result == mock_dialog_class.return_value


class TestDialogFactoryStaticMethods:
    """Tests to verify that all factory methods are static."""

    def test_all_factory_methods_are_static(self) -> None:
        """Test that all factory methods are static methods."""
        factory = DialogFactory()

        # Verify methods can be called without instance
        assert callable(DialogFactory.create_tmdb_progress_dialog)
        assert callable(DialogFactory.create_settings_dialog)
        assert callable(DialogFactory.create_organize_preview_dialog)
        assert callable(DialogFactory.create_organize_progress_dialog)


class TestDialogFactoryIntegration:
    """Integration tests for DialogFactory."""

    @patch("anivault.gui.dialogs.tmdb_progress_dialog.TMDBProgressDialog")
    @patch("anivault.gui.dialogs.settings_dialog.SettingsDialog")
    @patch("anivault.gui.dialogs.organize_preview_dialog.OrganizePreviewDialog")
    @patch("anivault.gui.dialogs.organize_progress_dialog.OrganizeProgressDialog")
    def test_multiple_dialog_creation(
        self,
        mock_organize_progress: Mock,
        mock_organize_preview: Mock,
        mock_settings: Mock,
        mock_tmdb_progress: Mock,
    ) -> None:
        """Test creating multiple different dialogs."""
        factory = DialogFactory()
        parent = Mock()
        config_path = Path("/test/config.json")
        plan = [Mock()]

        # Create all dialog types
        tmdb_dialog = factory.create_tmdb_progress_dialog(parent)
        settings_dialog = factory.create_settings_dialog(parent, config_path)
        preview_dialog = factory.create_organize_preview_dialog(plan, parent)
        progress_dialog = factory.create_organize_progress_dialog(10, parent)

        # Verify all were created
        mock_tmdb_progress.assert_called_once()
        mock_settings.assert_called_once()
        mock_organize_preview.assert_called_once()
        mock_organize_progress.assert_called_once()

        # Verify return values
        assert tmdb_dialog == mock_tmdb_progress.return_value
        assert settings_dialog == mock_settings.return_value
        assert preview_dialog == mock_organize_preview.return_value
        assert progress_dialog == mock_organize_progress.return_value
