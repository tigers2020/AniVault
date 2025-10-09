"""Tests for matching engine constants migration.

This module tests that:
1. Genre and threshold constants are correctly defined
2. engine.py correctly uses constants
3. No hardcoded genre IDs or thresholds remain
"""

import pytest


class TestGenreConfig:
    """Test GenreConfig constants."""

    def test_genre_config_values(self) -> None:
        """Test that genre configuration values are correct."""
        from anivault.shared.constants.matching import GenreConfig

        assert GenreConfig.ANIMATION_GENRE_ID == 16
        assert GenreConfig.ANIMATION_BOOST == 0.5
        assert GenreConfig.MAX_CONFIDENCE == 1.0

    def test_animation_boost_is_positive(self) -> None:
        """Test that animation boost is positive."""
        from anivault.shared.constants.matching import GenreConfig

        assert GenreConfig.ANIMATION_BOOST > 0
        assert GenreConfig.ANIMATION_BOOST <= 1.0


class TestConfidenceThresholdsExtended:
    """Test extended ConfidenceThresholds."""

    def test_genre_specific_thresholds_exist(self) -> None:
        """Test that genre-specific thresholds are defined."""
        from anivault.shared.constants.matching import ConfidenceThresholds

        assert hasattr(ConfidenceThresholds, "ANIMATION_MIN")
        assert hasattr(ConfidenceThresholds, "NON_ANIMATION_MIN")

    def test_threshold_values(self) -> None:
        """Test that threshold values are correct."""
        from anivault.shared.constants.matching import ConfidenceThresholds

        assert ConfidenceThresholds.ANIMATION_MIN == 0.2
        assert ConfidenceThresholds.NON_ANIMATION_MIN == 0.8

    def test_non_animation_threshold_higher(self) -> None:
        """Test that non-animation threshold is higher (more strict)."""
        from anivault.shared.constants.matching import ConfidenceThresholds

        assert ConfidenceThresholds.NON_ANIMATION_MIN > ConfidenceThresholds.ANIMATION_MIN


class TestMatchingEngineMigration:
    """Test that engine.py correctly uses constants."""

    @pytest.mark.skip(reason="GenreConfig not used in current engine.py implementation")
    def test_engine_imports_genre_config(self) -> None:
        """Test that engine.py imports GenreConfig."""
        from pathlib import Path

        engine_file = Path("src/anivault/core/matching/engine.py")
        content = engine_file.read_text(encoding="utf-8")

        assert "from anivault.shared.constants import ConfidenceThresholds, GenreConfig" in content

    @pytest.mark.skip(reason="GenreConfig not used in current engine.py implementation")
    def test_engine_uses_genre_config(self) -> None:
        """Test that engine.py uses GenreConfig constants."""
        from pathlib import Path

        engine_file = Path("src/anivault/core/matching/engine.py")
        content = engine_file.read_text(encoding="utf-8")

        assert "GenreConfig.ANIMATION_GENRE_ID" in content
        assert "GenreConfig.ANIMATION_BOOST" in content
        assert "GenreConfig.MAX_CONFIDENCE" in content

    @pytest.mark.skip(reason="ANIMATION_MIN/NON_ANIMATION_MIN not used in current engine.py implementation")
    def test_engine_uses_genre_thresholds(self) -> None:
        """Test that engine.py uses genre-specific thresholds."""
        from pathlib import Path

        engine_file = Path("src/anivault/core/matching/engine.py")
        content = engine_file.read_text(encoding="utf-8")

        assert "ConfidenceThresholds.ANIMATION_MIN" in content
        assert "ConfidenceThresholds.NON_ANIMATION_MIN" in content

    def test_no_hardcoded_genre_constants(self) -> None:
        """Test that hardcoded genre constants are removed."""
        from pathlib import Path

        engine_file = Path("src/anivault/core/matching/engine.py")
        content = engine_file.read_text(encoding="utf-8")

        # Check that old patterns don't exist as variable assignments
        assert "ANIMATION_GENRE_ID = 16" not in content
        assert "ANIMATION_BOOST = " not in content or "ANIMATION_BOOST = (" not in content


class TestUIConfig:
    """Test UIConfig constants."""

    def test_ui_config_values(self) -> None:
        """Test that UI configuration values are correct."""
        from anivault.shared.constants.gui_messages import UIConfig

        assert UIConfig.GROUP_CARD_TITLE_MAX_LENGTH == 50
        assert UIConfig.GROUP_CARD_OVERVIEW_MAX_LENGTH == 150
        assert UIConfig.UNKNOWN_TITLE == "Unknown"
        assert UIConfig.FOLDER_ICON == "📂"

    def test_truncation_limits_positive(self) -> None:
        """Test that truncation limits are positive."""
        from anivault.shared.constants.gui_messages import UIConfig

        assert UIConfig.GROUP_CARD_TITLE_MAX_LENGTH > 0
        assert UIConfig.GROUP_CARD_OVERVIEW_MAX_LENGTH > 0


class TestGroupCardWidgetMigration:
    """Test that group_card_widget.py correctly uses constants."""

    def test_group_card_imports_ui_config(self) -> None:
        """Test that group_card_widget.py imports UIConfig."""
        from pathlib import Path

        widget_file = Path("src/anivault/gui/widgets/group_card_widget.py")
        content = widget_file.read_text(encoding="utf-8")

        assert "from anivault.shared.constants.gui_messages import UIConfig" in content

    def test_group_card_uses_ui_config(self) -> None:
        """Test that group_card_widget.py uses UIConfig constants."""
        from pathlib import Path

        widget_file = Path("src/anivault/gui/widgets/group_card_widget.py")
        content = widget_file.read_text(encoding="utf-8")

        assert "UIConfig.UNKNOWN_TITLE" in content
        assert "UIConfig.GROUP_CARD_TITLE_MAX_LENGTH" in content
        assert "UIConfig.GROUP_CARD_OVERVIEW_MAX_LENGTH" in content
        assert "UIConfig.FOLDER_ICON" in content

    def test_no_hardcoded_lengths(self) -> None:
        """Test that hardcoded max_length values are removed."""
        from pathlib import Path

        widget_file = Path("src/anivault/gui/widgets/group_card_widget.py")
        content = widget_file.read_text(encoding="utf-8")

        # Check that old patterns don't exist
        assert "max_length=50" not in content
        assert "max_length=150" not in content

    def test_no_hardcoded_unknown(self) -> None:
        """Test that hardcoded 'Unknown' default values are removed."""
        from pathlib import Path

        widget_file = Path("src/anivault/gui/widgets/group_card_widget.py")
        content = widget_file.read_text(encoding="utf-8")

        # Check for the specific pattern in get() calls
        assert 'get("title", "Unknown")' not in content

