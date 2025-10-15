"""Tests for SettingsDialog API key saving to .env file."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from anivault.gui.dialogs.settings_dialog import SettingsDialog


@pytest.fixture
def temp_env_file(tmp_path: Path) -> Path:
    """Create temporary .env file."""
    env_file = tmp_path / ".env"
    return env_file


def test_save_api_key_to_env_file_new(qapp, temp_env_file: Path):
    """Test saving API key to new .env file."""
    # Create SettingsDialog instance
    dialog = SettingsDialog()

    # Save API key
    test_key = "test_api_key_12345678901234567890"  # pragma: allowlist secret
    dialog._save_api_key_to_env_file(test_key, env_file_path=temp_env_file)

    # Verify file created
    assert temp_env_file.exists()

    # Verify content
    content = temp_env_file.read_text()
    assert f"TMDB_API_KEY={test_key}" in content

    # Verify environment variable
    assert os.environ.get("TMDB_API_KEY") == test_key


def test_save_api_key_to_env_file_update_existing(qapp, temp_env_file: Path):
    """Test updating existing TMDB_API_KEY in .env file."""
    # Create existing .env with old key
    old_key = "old_key_12345678901234567890"  # pragma: allowlist secret
    temp_env_file.write_text(f"TMDB_API_KEY={old_key}\nOTHER_VAR=value\n")

    # Create SettingsDialog instance
    dialog = SettingsDialog()

    # Save new API key
    new_key = "new_key_09876543210987654321"  # pragma: allowlist secret
    dialog._save_api_key_to_env_file(new_key, env_file_path=temp_env_file)

    # Verify content
    content = temp_env_file.read_text()
    assert f"TMDB_API_KEY={new_key}" in content
    assert old_key not in content
    assert "OTHER_VAR=value" in content  # Other vars preserved


def test_save_api_key_to_env_file_preserves_comments(qapp, temp_env_file: Path):
    """Test that comments and other lines are preserved."""
    # Create .env with comments
    existing_content = """# AniVault Environment Variables
TMDB_API_KEY=old_key  # pragma: allowlist secret
# Another comment
OTHER_VAR=value
"""
    temp_env_file.write_text(existing_content)

    # Create SettingsDialog instance
    dialog = SettingsDialog()

    # Save new key
    new_key = "updated_key_12345"  # pragma: allowlist secret
    dialog._save_api_key_to_env_file(new_key, env_file_path=temp_env_file)

    # Verify
    content = temp_env_file.read_text()
    assert "# AniVault Environment Variables" in content
    assert f"TMDB_API_KEY={new_key}" in content
    assert "OTHER_VAR=value" in content
