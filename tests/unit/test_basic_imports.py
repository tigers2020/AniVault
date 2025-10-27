"""Test basic imports to ensure the project structure is correct."""

import pytest


def test_anivault_imports():
    """Test that core AniVault modules can be imported."""
    # Test core imports
    from anivault.core.models import ScannedFile
    from anivault.core.parser.models import ParsingResult
    from anivault.shared.constants import FileSystem

    # Verify classes exist
    assert ScannedFile is not None
    assert ParsingResult is not None
    assert FileSystem is not None


def test_shared_constants():
    """Test that shared constants are properly defined."""
    from anivault.shared.constants import FileSystem

    # Test that constants have expected values
    assert hasattr(FileSystem, "SUPPORTED_VIDEO_EXTENSIONS")
    assert isinstance(FileSystem.SUPPORTED_VIDEO_EXTENSIONS, list)
    assert len(FileSystem.SUPPORTED_VIDEO_EXTENSIONS) > 0


def test_config_imports():
    """Test that configuration modules can be imported."""
    from anivault.config.loader import SettingsLoader
    from anivault.config.models.api_settings import TMDBSettings

    assert SettingsLoader is not None
    assert TMDBSettings is not None
