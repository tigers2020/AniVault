"""Tests for parser data models."""

from __future__ import annotations

import pytest

from anivault.core.parser.models import ParsingResult


def test_parsing_result_minimal_instantiation():
    """Test that ParsingResult can be created with only required fields."""
    result = ParsingResult(title="Evangelion")

    assert result.title == "Evangelion"
    assert result.episode is None
    assert result.season is None
    assert result.quality is None
    assert result.confidence == 0.0
    assert result.parser_used == "unknown"
    assert result.other_info == {}


def test_parsing_result_full_instantiation():
    """Test that ParsingResult can be created with all fields."""
    result = ParsingResult(
        title="Attack on Titan",
        episode=1,
        season=1,
        quality="1080p",
        source="BluRay",
        codec="H.264",
        audio="AAC",
        release_group="SubsPlease",
        confidence=0.95,
        parser_used="anitopy",
        other_info={"year": 2013, "language": "japanese"},
    )

    assert result.title == "Attack on Titan"
    assert result.episode == 1
    assert result.season == 1
    assert result.quality == "1080p"
    assert result.source == "BluRay"
    assert result.codec == "H.264"
    assert result.audio == "AAC"
    assert result.release_group == "SubsPlease"
    assert result.confidence == 0.95
    assert result.parser_used == "anitopy"
    assert result.other_info == {"year": 2013, "language": "japanese"}


def test_parsing_result_confidence_validation_valid():
    """Test that valid confidence values are accepted."""
    # Edge cases
    result_min = ParsingResult(title="Test", confidence=0.0)
    assert result_min.confidence == 0.0

    result_max = ParsingResult(title="Test", confidence=1.0)
    assert result_max.confidence == 1.0

    # Mid-range
    result_mid = ParsingResult(title="Test", confidence=0.5)
    assert result_mid.confidence == 0.5


def test_parsing_result_confidence_validation_invalid_high():
    """Test that confidence values above 1.0 raise ValueError."""
    with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
        ParsingResult(title="Test", confidence=1.5)


def test_parsing_result_confidence_validation_invalid_low():
    """Test that confidence values below 0.0 raise ValueError."""
    with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
        ParsingResult(title="Test", confidence=-0.1)


def test_parsing_result_is_valid_with_title():
    """Test that is_valid returns True when title is present."""
    result = ParsingResult(title="One Piece")
    assert result.is_valid() is True


def test_parsing_result_is_valid_with_empty_title():
    """Test that is_valid returns False when title is empty."""
    result = ParsingResult(title="")
    assert result.is_valid() is False


def test_parsing_result_is_valid_with_whitespace_title():
    """Test that is_valid returns False when title is only whitespace."""
    result = ParsingResult(title="   ")
    assert result.is_valid() is False


def test_parsing_result_has_episode_info():
    """Test has_episode_info method."""
    result_with_episode = ParsingResult(title="Test", episode=5)
    assert result_with_episode.has_episode_info() is True

    result_without_episode = ParsingResult(title="Test")
    assert result_without_episode.has_episode_info() is False


def test_parsing_result_has_season_info():
    """Test has_season_info method."""
    result_with_season = ParsingResult(title="Test", season=2)
    assert result_with_season.has_season_info() is True

    result_without_season = ParsingResult(title="Test")
    assert result_without_season.has_season_info() is False


def test_parsing_result_other_info_default():
    """Test that other_info defaults to empty dict and is mutable."""
    result1 = ParsingResult(title="Test1")
    result2 = ParsingResult(title="Test2")

    result1.other_info["key"] = "value"

    # Ensure default factory creates separate dicts for each instance
    assert "key" not in result2.other_info
    assert result1.other_info == {"key": "value"}
    assert result2.other_info == {}
