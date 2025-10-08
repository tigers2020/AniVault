"""Tests for GUI constants migration.

This module tests that:
1. GUI constants are correctly defined
2. main_window.py and dialogs correctly use constants
3. No hardcoded GUI messages remain
"""

import pytest


class TestGUIConstants:
    """Test GUI message constants."""

    def test_dialog_titles_exist(self) -> None:
        """Test that all dialog titles are defined."""
        from anivault.shared.constants.gui_messages import DialogTitles

        assert hasattr(DialogTitles, "ERROR")
        assert hasattr(DialogTitles, "WARNING")
        assert hasattr(DialogTitles, "SUCCESS")
        assert hasattr(DialogTitles, "SETTINGS_SAVED")
        assert hasattr(DialogTitles, "API_KEY_REQUIRED")

    def test_dialog_messages_exist(self) -> None:
        """Test that all dialog messages are defined."""
        from anivault.shared.constants.gui_messages import DialogMessages

        assert hasattr(DialogMessages, "API_KEY_SAVED")
        assert hasattr(DialogMessages, "API_KEY_REQUIRED")
        assert hasattr(DialogMessages, "API_KEY_TOO_SHORT")
        assert hasattr(DialogMessages, "TMDB_API_KEY_MISSING")

    def test_button_texts_exist(self) -> None:
        """Test that button texts are defined."""
        from anivault.shared.constants.gui_messages import ButtonTexts

        assert hasattr(ButtonTexts, "OK")
        assert hasattr(ButtonTexts, "CANCEL")
        assert hasattr(ButtonTexts, "CANCEL_MATCHING")

    def test_progress_messages_exist(self) -> None:
        """Test that progress messages are defined."""
        from anivault.shared.constants.gui_messages import ProgressMessages

        assert hasattr(ProgressMessages, "PREPARING_TMDB")
        assert hasattr(ProgressMessages, "MATCHING_IN_PROGRESS")
        assert hasattr(ProgressMessages, "MATCHING_COMPLETE")

    def test_messages_not_empty(self) -> None:
        """Test that messages are not empty strings."""
        from anivault.shared.constants.gui_messages import DialogMessages

        assert len(DialogMessages.API_KEY_SAVED) > 0
        assert len(DialogMessages.API_KEY_REQUIRED) > 0
        assert len(DialogMessages.TMDB_API_KEY_MISSING) > 0


class TestGUIMigration:
    """Test that GUI files correctly use constants."""

    def test_main_window_imports_constants(self) -> None:
        """Test that main_window.py imports GUI constants."""
        from pathlib import Path

        main_window_file = Path("src/anivault/gui/main_window.py")
        content = main_window_file.read_text(encoding="utf-8")

        assert "from anivault.shared.constants.gui_messages import" in content

    def test_main_window_uses_dialog_titles(self) -> None:
        """Test that main_window.py uses DialogTitles constants."""
        from pathlib import Path

        main_window_file = Path("src/anivault/gui/main_window.py")
        content = main_window_file.read_text(encoding="utf-8")

        assert "DialogTitles.ERROR" in content
        assert "DialogTitles.SCAN_ERROR" in content
        assert "DialogTitles.API_KEY_REQUIRED" in content

    def test_settings_dialog_imports_constants(self) -> None:
        """Test that settings_dialog.py imports GUI constants."""
        from pathlib import Path

        settings_file = Path("src/anivault/gui/dialogs/settings_dialog.py")
        content = settings_file.read_text(encoding="utf-8")

        assert "from anivault.shared.constants.gui_messages import" in content

    def test_settings_dialog_uses_constants(self) -> None:
        """Test that settings_dialog.py uses GUI constants."""
        from pathlib import Path

        settings_file = Path("src/anivault/gui/dialogs/settings_dialog.py")
        content = settings_file.read_text(encoding="utf-8")

        assert "DialogTitles.API_KEY_REQUIRED" in content
        assert "DialogMessages.API_KEY_REQUIRED" in content
        assert "DialogTitles.SETTINGS_SAVED" in content
        assert "DialogMessages.API_KEY_SAVED" in content

    def test_tmdb_progress_uses_constants(self) -> None:
        """Test that tmdb_progress_dialog.py uses GUI constants."""
        from pathlib import Path

        progress_file = Path("src/anivault/gui/dialogs/tmdb_progress_dialog.py")
        content = progress_file.read_text(encoding="utf-8")

        assert "ButtonTexts.CANCEL_MATCHING" in content
        assert "ProgressMessages.PREPARING_TMDB" in content
        assert "ProgressMessages.MATCHING_COMPLETE" in content

    def test_no_hardcoded_dialog_titles(self) -> None:
        """Test that hardcoded dialog titles are removed."""
        from pathlib import Path

        files_to_check = [
            "src/anivault/gui/main_window.py",
            "src/anivault/gui/dialogs/settings_dialog.py",
        ]

        for file_path in files_to_check:
            content = Path(file_path).read_text(encoding="utf-8")

            # These should not appear as hardcoded strings anymore
            # (they should use DialogTitles constants)
            assert 'QMessageBox.warning(self, "API Key Required"' not in content
            assert 'QMessageBox.information(self, "Settings Saved"' not in content

