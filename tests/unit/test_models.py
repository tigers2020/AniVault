"""Test core data models."""

import pytest
from pathlib import Path

from anivault.core.models import ScannedFile
from anivault.core.parser.models import ParsingResult


class TestScannedFile:
    """Test ScannedFile model."""

    def test_scanned_file_creation(self):
        """Test creating a ScannedFile instance."""
        file_path = Path("test_anime.mkv")
        metadata = ParsingResult(title="Test Anime")

        scanned_file = ScannedFile(
            file_path=file_path,
            metadata=metadata,
            file_size=1024,
            last_modified=1234567890.0
        )

        assert scanned_file.file_path == file_path
        assert scanned_file.metadata == metadata
        assert scanned_file.file_size == 1024
        assert scanned_file.last_modified == 1234567890.0

    def test_scanned_file_with_defaults(self):
        """Test creating ScannedFile with default values."""
        file_path = Path("test_anime.mkv")
        metadata = ParsingResult(title="Test Anime")

        scanned_file = ScannedFile(
            file_path=file_path,
            metadata=metadata
        )

        assert scanned_file.file_path == file_path
        assert scanned_file.metadata == metadata
        assert scanned_file.file_size == 0
        assert scanned_file.last_modified == 0.0


class TestParsingResult:
    """Test ParsingResult model."""

    def test_parsing_result_creation(self):
        """Test creating a ParsingResult instance."""
        result = ParsingResult(
            title="Attack on Titan",
            season=1,
            episode=1,
            year=2013
        )

        assert result.title == "Attack on Titan"
        assert result.season == 1
        assert result.episode == 1
        assert result.year == 2013

    def test_parsing_result_with_defaults(self):
        """Test creating ParsingResult with default values."""
        result = ParsingResult(title="Test Anime")

        assert result.title == "Test Anime"
        assert result.season is None
        assert result.episode is None
        assert result.year is None

    def test_has_episode_info(self):
        """Test has_episode_info method."""
        result_with_episode = ParsingResult(title="Test", season=1, episode=1)
        result_without_episode = ParsingResult(title="Test")

        assert result_with_episode.has_episode_info() is True
        assert result_without_episode.has_episode_info() is False

    def test_has_season_info(self):
        """Test has_season_info method."""
        result_with_season = ParsingResult(title="Test", season=1)
        result_without_season = ParsingResult(title="Test")

        assert result_with_season.has_season_info() is True
        assert result_without_season.has_season_info() is False
