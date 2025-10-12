"""Tests for update_and_save_config() helper function."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from anivault.config.settings import (
    Settings,
    get_config,
    reload_config,
    update_and_save_config,
)
from anivault.shared.errors import ApplicationError


@pytest.fixture
def temp_config(tmp_path: Path) -> Path:
    """Create temporary config file."""
    config_file = tmp_path / "config.toml"
    config_content = """
[app]
name = "AniVault"
version = "0.1.0"

[tmdb]
api_key = ""
timeout = 30

[cache]
enabled = true
"""
    config_file.write_text(config_content)
    return config_file


def test_update_and_save_success(temp_config: Path):
    """Test successful config update and save."""

    # Define updater
    def update_timeout(cfg: Settings):
        cfg.tmdb.timeout = 60

    # Update and save
    update_and_save_config(update_timeout, temp_config)

    # Verify cache updated
    cfg = get_config()
    assert cfg.tmdb.timeout == 60

    # Verify file saved
    reloaded = reload_config()
    assert reloaded.tmdb.timeout == 60


def test_update_validation_failure(temp_config: Path):
    """Test that validation failure prevents save."""
    original_cfg = get_config()
    original_timeout = original_cfg.tmdb.timeout

    # Define invalid updater
    def invalid_update(cfg: Settings):
        cfg.tmdb.timeout = -1  # Invalid (must be > 0)

    # Should raise error
    with pytest.raises(ApplicationError):
        update_and_save_config(invalid_update, temp_config)

    # Cache should remain unchanged
    cfg = get_config()
    assert cfg.tmdb.timeout == original_timeout


def test_update_exception_rollback(temp_config: Path):
    """Test that exception during update doesn't corrupt cache."""
    original_cfg = get_config()
    original_version = original_cfg.app.version

    # Define failing updater
    def failing_update(cfg: Settings):
        cfg.app.version = "2.0.0"
        raise RuntimeError("Intentional failure")

    # Should raise error
    with pytest.raises(ApplicationError):
        update_and_save_config(failing_update, temp_config)

    # Cache should remain unchanged
    cfg = get_config()
    assert cfg.app.version == original_version


def test_api_key_not_saved_to_file(temp_config: Path):
    """Test that API key is excluded from saved file (Security test)."""

    # Update config with API key
    def set_api_key(cfg: Settings):
        cfg.tmdb.api_key = "test_secret_key_12345"  # pragma: allowlist secret

    update_and_save_config(set_api_key, temp_config)

    # Verify API key in memory
    cfg = get_config()
    assert cfg.tmdb.api_key == "test_secret_key_12345"  # pragma: allowlist secret

    # Verify API key NOT in file
    saved_content = temp_config.read_text()
    assert "test_secret_key_12345" not in saved_content
    assert 'api_key = ""' in saved_content or "api_key" not in saved_content
