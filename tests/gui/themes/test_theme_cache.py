"""
Tests for ThemeCache module.

This module verifies:
- Mtime-based cache validation (hit/miss logic)
- Cache invalidation (all themes or specific theme)
- Integration with ThemeValidator for security
- Callable loader pattern for flexible content loading
"""

from __future__ import annotations

from pathlib import Path

import pytest

from anivault.gui.themes.theme_cache import ThemeCache
from anivault.gui.themes.theme_validator import ThemeValidator
from anivault.shared.errors import ApplicationError, ErrorCode


class TestThemeCacheInit:
    """Test ThemeCache initialization."""

    def test_init_stores_validator(self, tmp_path):
        """Test that ThemeCache stores validator reference."""
        themes_dir = tmp_path / "themes"
        themes_dir.mkdir()
        base_theme_dir = tmp_path / "base_themes"
        base_theme_dir.mkdir()

        validator = ThemeValidator(themes_dir, base_theme_dir)
        cache = ThemeCache(validator)

        assert cache._validator is validator

    def test_init_creates_empty_cache(self, tmp_path):
        """Test that cache starts empty."""
        themes_dir = tmp_path / "themes"
        themes_dir.mkdir()
        base_theme_dir = tmp_path / "base_themes"
        base_theme_dir.mkdir()

        validator = ThemeValidator(themes_dir, base_theme_dir)
        cache = ThemeCache(validator)

        assert len(cache) == 0


class TestThemeCacheGetOrLoad:
    """Test cache hit/miss logic."""

    @pytest.fixture()
    def setup(self, tmp_path):
        """Setup fixture with validator and cache."""
        themes_dir = tmp_path / "themes"
        themes_dir.mkdir()
        base_theme_dir = tmp_path / "base_themes"
        base_theme_dir.mkdir()

        validator = ThemeValidator(themes_dir, base_theme_dir)
        cache = ThemeCache(validator)

        # Create test theme file
        theme_file = themes_dir / "test.qss"
        theme_file.write_text("QWidget { color: white; }")

        return cache, theme_file

    def test_cache_miss_calls_loader(self, setup):
        """Test that cache miss calls loader and caches result."""
        cache, theme_file = setup

        loader_calls = []

        def loader(path: Path) -> str:
            loader_calls.append(path)
            return path.read_text(encoding="utf-8")

        # First call - cache miss
        content = cache.get_or_load(theme_file, loader)

        assert content == "QWidget { color: white; }"
        assert len(loader_calls) == 1
        assert len(cache) == 1

    def test_cache_hit_skips_loader(self, setup):
        """Test that cache hit does not call loader."""
        cache, theme_file = setup

        loader_calls = []

        def loader(path: Path) -> str:
            loader_calls.append(path)
            return path.read_text(encoding="utf-8")

        # First call - cache miss
        cache.get_or_load(theme_file, loader)

        # Second call - cache hit
        content = cache.get_or_load(theme_file, loader)

        assert content == "QWidget { color: white; }"
        assert len(loader_calls) == 1  # Loader not called second time
        assert len(cache) == 1

    def test_cache_invalidation_on_mtime_change(self, setup):
        """Test that cache invalidates when file mtime changes."""
        import time

        cache, theme_file = setup

        loader_calls = []

        def loader(path: Path) -> str:
            loader_calls.append(path)
            return path.read_text(encoding="utf-8")

        # First call - cache miss
        content1 = cache.get_or_load(theme_file, loader)
        assert content1 == "QWidget { color: white; }"
        assert len(loader_calls) == 1

        # Modify file content to trigger mtime change
        time.sleep(0.01)  # Ensure mtime changes
        theme_file.write_text("QWidget { color: black; }")

        # Second call - cache miss due to mtime change
        content2 = cache.get_or_load(theme_file, loader)
        assert content2 == "QWidget { color: black; }"
        assert len(loader_calls) == 2  # Loader called again

    def test_file_not_found_raises_error(self, setup):
        """Test that missing file raises ApplicationError."""
        cache, _ = setup

        nonexistent = Path("/nonexistent/theme.qss")

        def loader(path: Path) -> str:
            return path.read_text(encoding="utf-8")

        with pytest.raises(ApplicationError) as exc_info:
            cache.get_or_load(nonexistent, loader)

        assert exc_info.value.code == ErrorCode.FILE_NOT_FOUND


class TestThemeCacheRefresh:
    """Test cache invalidation methods."""

    @pytest.fixture()
    def setup(self, tmp_path):
        """Setup fixture with multiple cached themes."""
        themes_dir = tmp_path / "themes"
        themes_dir.mkdir()
        base_theme_dir = tmp_path / "base_themes"
        base_theme_dir.mkdir()

        validator = ThemeValidator(themes_dir, base_theme_dir)
        cache = ThemeCache(validator)

        # Create test theme files
        light_file = themes_dir / "light.qss"
        light_file.write_text("QWidget { color: black; }")

        dark_file = themes_dir / "dark.qss"
        dark_file.write_text("QWidget { color: white; }")

        def loader(path: Path) -> str:
            return path.read_text(encoding="utf-8")

        # Load both themes to populate cache
        cache.get_or_load(light_file, loader)
        cache.get_or_load(dark_file, loader)

        return cache, light_file, dark_file

    def test_refresh_all_clears_cache(self, setup):
        """Test that refresh(None) clears entire cache."""
        cache, _, _ = setup

        assert len(cache) == 2

        cache.refresh(None)

        assert len(cache) == 0

    def test_refresh_specific_theme_keeps_others(self, setup):
        """Test that refresh(theme_name) only clears that theme."""
        cache, light_file, dark_file = setup

        assert len(cache) == 2

        cache.refresh("light")

        assert len(cache) == 1
        assert dark_file in cache
        assert light_file not in cache

    def test_refresh_invalid_theme_name_raises_error(self, setup):
        """Test that invalid theme name raises validation error."""
        cache, _, _ = setup

        with pytest.raises(ApplicationError) as exc_info:
            cache.refresh("../../../etc/passwd")

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR

    def test_refresh_nonexistent_theme_no_error(self, setup):
        """Test that refreshing nonexistent theme does not raise error."""
        cache, light_file, dark_file = setup

        # Should not raise error
        cache.refresh("nonexistent")

        # Cache should remain unchanged
        assert len(cache) == 2
        assert light_file in cache
        assert dark_file in cache

    def test_clear_method_clears_all(self, setup):
        """Test that clear() is equivalent to refresh(None)."""
        cache, _, _ = setup

        assert len(cache) == 2

        cache.clear()

        assert len(cache) == 0


class TestThemeCacheMagicMethods:
    """Test magic methods (__len__, __contains__)."""

    @pytest.fixture()
    def setup(self, tmp_path):
        """Setup fixture with cache and theme files."""
        themes_dir = tmp_path / "themes"
        themes_dir.mkdir()
        base_theme_dir = tmp_path / "base_themes"
        base_theme_dir.mkdir()

        validator = ThemeValidator(themes_dir, base_theme_dir)
        cache = ThemeCache(validator)

        light_file = themes_dir / "light.qss"
        light_file.write_text("QWidget { color: black; }")

        return cache, light_file

    def test_len_reflects_cache_size(self, setup):
        """Test that len() returns cache size."""
        cache, light_file = setup

        assert len(cache) == 0

        def loader(path: Path) -> str:
            return path.read_text(encoding="utf-8")

        cache.get_or_load(light_file, loader)

        assert len(cache) == 1

    def test_contains_checks_cache_membership(self, setup):
        """Test that 'in' operator works correctly."""
        cache, light_file = setup

        assert light_file not in cache

        def loader(path: Path) -> str:
            return path.read_text(encoding="utf-8")

        cache.get_or_load(light_file, loader)

        assert light_file in cache
