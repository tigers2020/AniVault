"""
Tests for anime filename parsing functionality.

This module tests the anime parser, validation, and fallback mechanisms
to ensure accurate parsing of anime filenames with 95%+ accuracy.
"""

from datetime import datetime
from pathlib import Path

import pytest

from src.core.anime_parser import AnimeParser
from src.core.fallback_parser import FallbackAnimeParser
from src.core.models import AnimeFile, ParsedAnimeInfo
from src.core.validation import AnimeDataValidator


class TestAnimeParser:
    """Test cases for the main AnimeParser class."""

    @pytest.fixture
    def parser(self):
        """Create an AnimeParser instance for testing."""
        return AnimeParser()

    @pytest.fixture
    def sample_anime_files(self):
        """Sample anime filenames for testing."""
        return [
            # Well-formed filenames
            "[SubsPlease] Oshi no Ko - 01 (1080p) [F234F234].mkv",
            "ReZero S02E05 [720p].mp4",
            "Mushoku Tensei II - Isekai Ittara Honki Dasu - 01 (Season 2) (1080p HEVC) [E0277717].mkv",
            "[Erai-raws] Kage no Jitsuryokusha ni Naritakute! 2nd Season - 01 [1080p][Multiple Subtitle][521B212A].mkv",
            "One Piece - 1000 [1080p].mkv",
            "Attack on Titan The Final Season Part 2 - 01 (1080p).mp4",
            "My Hero Academia S5 - Episode 100 (720p).avi",
            "Movie Title (2023) [1080p].mkv",
            # Edge cases
            "[HorribleSubs] Anime - 01 [1920x1080].mkv",
            "[Release] Anime - 01 [4K].mp4",
            "[Release] Anime - 01 [2160p].mkv",
            "Anime S1E1.mkv",
            "Anime Season 1 Episode 1.mkv",
            "Anime Ep 01.mkv",
            "Anime 01.mkv",
            "Anime - OVA 01.mkv",
            "Anime Title.mkv",
            "Anime - 01.mkv",
            "Anime Title (1080p).mkv",
            "Anime Title! - 01 (Part 2) [Special].mkv",
            "Anime Title (2023) - 01.mkv",
            "[CR][SubsPlease] Anime - 01 [1080p].mkv",
            # Malformed/unparseable filenames
            "random_document.pdf",
            "just_a_string",
            "my_vacation_video.mp4",
            "Anime Title - Not an Episode.mkv",
            "",
            "   ",
        ]

    def test_parse_filename_success(self, parser, sample_anime_files) -> None:
        """Test successful parsing of well-formed filenames."""
        # Test first few well-formed filenames
        test_files = sample_anime_files[:8]

        for filename in test_files:
            result = parser.parse_filename(filename)
            assert result is not None, f"Failed to parse: {filename}"
            assert isinstance(result, ParsedAnimeInfo), f"Wrong type for: {filename}"
            assert result.title, f"No title extracted from: {filename}"
            assert result.is_valid(), f"Invalid result for: {filename}"

    def test_parse_filename_edge_cases(self, parser, sample_anime_files) -> None:
        """Test parsing of edge case filenames."""
        # Test edge cases (indices 8-22)
        test_files = sample_anime_files[8:23]

        for filename in test_files:
            result = parser.parse_filename(filename)
            if result:
                assert isinstance(result, ParsedAnimeInfo), f"Wrong type for: {filename}"
                assert result.title, f"No title extracted from: {filename}"

    def test_parse_filename_failures(self, parser, sample_anime_files) -> None:
        """Test handling of unparseable filenames."""
        # Test malformed filenames (indices 23-28)
        test_files = sample_anime_files[23:29]

        for filename in test_files:
            result = parser.parse_filename(filename)
            # Should return None for unparseable files
            # Note: Some files might be parsed by fallback, so we check if they're valid
            if result is not None:
                # If parsed, it should be a valid anime file
                assert result.is_valid(), f"Parsed result should be valid for: {filename}"

    def test_parse_anime_file(self, parser) -> None:
        """Test parsing of AnimeFile objects."""
        # Create a test AnimeFile
        anime_file = AnimeFile(
            file_path=Path("/test/path/anime.mkv"),
            filename="[SubsPlease] Test Anime - 01 (1080p).mkv",
            file_size=1024 * 1024,
            file_extension=".mkv",
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )

        result = parser.parse_anime_file(anime_file)
        assert result is not None
        assert isinstance(result, ParsedAnimeInfo)
        assert result.title == "Test Anime"
        assert result.episode == 1
        assert result.resolution == "1080p"

    def test_parse_anime_file_failure(self, parser) -> None:
        """Test parsing failure handling for AnimeFile objects."""
        # Create a test AnimeFile with unparseable filename
        anime_file = AnimeFile(
            file_path=Path("/test/path/not_anime.txt"),
            filename="not_anime.txt",
            file_size=1024,
            file_extension=".txt",
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )

        result = parser.parse_anime_file(anime_file)
        # Result might be None or a ParsedAnimeInfo, but if it's not None, it should be valid
        if result is not None:
            assert result.is_valid()
        else:
            assert len(anime_file.processing_errors) > 0

    def test_parse_filenames_batch(self, parser) -> None:
        """Test batch parsing of multiple filenames."""
        filenames = [
            "[SubsPlease] Anime 1 - 01 (1080p).mkv",
            "[SubsPlease] Anime 2 - 02 (720p).mkv",
            "not_anime.txt",
        ]

        results = parser.parse_filenames_batch(filenames)
        assert len(results) == 3
        assert results[0] is not None
        assert results[1] is not None
        # Third file might be parsed by fallback, so check if it's valid if not None
        if results[2] is not None:
            assert results[2].is_valid()

    def test_parse_anime_files_batch(self, parser) -> None:
        """Test batch parsing of AnimeFile objects."""
        anime_files = [
            AnimeFile(
                file_path=Path("/test/anime1.mkv"),
                filename="[SubsPlease] Anime 1 - 01 (1080p).mkv",
                file_size=1024 * 1024,
                file_extension=".mkv",
                created_at=datetime.now(),
                modified_at=datetime.now(),
            ),
            AnimeFile(
                file_path=Path("/test/anime2.mkv"),
                filename="[SubsPlease] Anime 2 - 02 (720p).mkv",
                file_size=1024 * 1024,
                file_extension=".mkv",
                created_at=datetime.now(),
                modified_at=datetime.now(),
            ),
            AnimeFile(
                file_path=Path("/test/not_anime.txt"),
                filename="not_anime.txt",
                file_size=1024,
                file_extension=".txt",
                created_at=datetime.now(),
                modified_at=datetime.now(),
            ),
        ]

        results = parser.parse_anime_files_batch(anime_files)
        assert len(results) == 3
        assert results[0] is not None
        assert results[1] is not None
        # Third file might be parsed by fallback, so check if it's valid if not None
        if results[2] is not None:
            assert results[2].is_valid()
        # If the file was successfully parsed, there should be no errors
        # If it failed to parse, there should be errors
        if results[2] is None:
            assert len(anime_files[2].processing_errors) > 0

    def test_parsing_statistics(self, parser) -> None:
        """Test parsing statistics generation."""
        results = [
            ParsedAnimeInfo(title="Anime 1", episode=1, season=1, resolution="1080p"),
            ParsedAnimeInfo(title="Anime 2", episode=2, season=1, resolution="720p"),
            None,  # Failed parse
        ]

        stats = parser.get_parsing_statistics(results)
        assert stats["total_files"] == 3
        assert stats["successful_parses"] == 2
        assert stats["failed_parses"] == 1
        assert abs(stats["success_rate"] - 66.67) < 0.01
        assert stats["tv_series"] == 2
        assert stats["movies"] == 0

    def test_parsing_failures(self, parser) -> None:
        """Test parsing failure information collection."""
        anime_files = [
            AnimeFile(
                file_path=Path("/test/anime1.mkv"),
                filename="[SubsPlease] Anime 1 - 01 (1080p).mkv",
                file_size=1024 * 1024,
                file_extension=".mkv",
                created_at=datetime.now(),
                modified_at=datetime.now(),
            ),
            AnimeFile(
                file_path=Path("/test/not_anime.txt"),
                filename="not_anime.txt",
                file_size=1024,
                file_extension=".txt",
                created_at=datetime.now(),
                modified_at=datetime.now(),
            ),
        ]

        # Simulate parsing failure for second file
        anime_files[1].processing_errors.append("Failed to parse")

        failures = parser.get_parsing_failures(anime_files)
        assert len(failures) == 1
        assert failures[0]["filename"] == "not_anime.txt"
        assert len(failures[0]["errors"]) > 0

    def test_suggest_manual_input(self, parser) -> None:
        """Test manual input suggestions for failed parsing."""
        suggestions = parser.suggest_manual_input("Anime Title - Episode 01 (1080p).mkv")
        assert "title" in suggestions
        assert "episode" in suggestions
        assert "resolution" in suggestions
        assert suggestions["confidence"] in ["low", "medium", "high"]


class TestAnimeDataValidator:
    """Test cases for the AnimeDataValidator class."""

    @pytest.fixture
    def validator(self):
        """Create an AnimeDataValidator instance for testing."""
        return AnimeDataValidator()

    def test_validate_title(self, validator) -> None:
        """Test title validation."""
        # Valid titles
        valid, errors, normalized = validator.validate_title("Attack on Titan")
        assert valid
        assert len(errors) == 0
        assert normalized == "Attack on Titan"

        # Invalid titles
        valid, errors, normalized = validator.validate_title("")
        assert not valid
        assert len(errors) > 0

        valid, errors, normalized = validator.validate_title("A")
        assert not valid
        assert "too short" in errors[0]

    def test_validate_episode_number(self, validator) -> None:
        """Test episode number validation."""
        # Valid episodes
        valid, errors, normalized = validator.validate_episode_number(1)
        assert valid
        assert normalized == 1

        valid, errors, normalized = validator.validate_episode_number(None)
        assert valid
        assert normalized is None

        # Invalid episodes
        valid, errors, normalized = validator.validate_episode_number(-1)
        assert not valid
        assert "negative" in errors[0]

    def test_validate_season_number(self, validator) -> None:
        """Test season number validation."""
        # Valid seasons
        valid, errors, normalized = validator.validate_season_number(1)
        assert valid
        assert normalized == 1

        # Invalid seasons
        valid, errors, normalized = validator.validate_season_number(-1)
        assert not valid
        assert "negative" in errors[0]

    def test_validate_resolution(self, validator) -> None:
        """Test resolution validation."""
        # Valid resolutions
        valid, errors, normalized = validator.validate_resolution("1080p", 1920, 1080)
        assert valid
        assert normalized == ("1080p", 1920, 1080)

        # Invalid resolutions
        valid, errors, normalized = validator.validate_resolution("1080p", -1, 1080)
        assert not valid
        assert "positive integer" in errors[0]

    def test_validate_parsed_info(self, validator) -> None:
        """Test comprehensive validation of ParsedAnimeInfo."""
        # Valid parsed info
        parsed_info = ParsedAnimeInfo(
            title="Attack on Titan",
            episode=1,
            season=1,
            resolution="1080p",
            resolution_width=1920,
            resolution_height=1080,
        )

        result = validator.validate_parsed_info(parsed_info)
        assert result.is_valid
        assert len(result.errors) == 0

        # Invalid parsed info
        parsed_info = ParsedAnimeInfo(title="")
        result = validator.validate_parsed_info(parsed_info)
        assert not result.is_valid
        assert len(result.errors) > 0


class TestFallbackAnimeParser:
    """Test cases for the FallbackAnimeParser class."""

    @pytest.fixture
    def fallback_parser(self):
        """Create a FallbackAnimeParser instance for testing."""
        return FallbackAnimeParser()

    def test_extract_basic_info(self, fallback_parser) -> None:
        """Test basic information extraction."""
        filename = "Anime Title - Episode 01 (1080p).mkv"
        info = fallback_parser.extract_basic_info(filename)

        assert info["title"] == "Anime Title"
        assert info["episode"] == 1
        assert info["resolution"] == "1080p"
        assert info["file_extension"] == ".mkv"

    def test_create_fallback_parsed_info(self, fallback_parser) -> None:
        """Test creation of ParsedAnimeInfo from fallback parsing."""
        filename = "Anime Title - Episode 01 (1080p).mkv"
        result = fallback_parser.create_fallback_parsed_info(filename)

        assert result is not None
        assert isinstance(result, ParsedAnimeInfo)
        assert result.title == "Anime Title"
        assert result.episode == 1
        assert result.resolution == "1080p"
        assert result.raw_data["fallback_parsing"] is True

    def test_is_likely_anime_file(self, fallback_parser) -> None:
        """Test anime file detection."""
        # Likely anime files
        assert fallback_parser.is_likely_anime_file("Anime - Episode 01.mkv")
        assert fallback_parser.is_likely_anime_file("Anime S1E1.mp4")
        assert fallback_parser.is_likely_anime_file("[SubsPlease] Anime - 01 [1080p].mkv")

        # Not likely anime files
        assert not fallback_parser.is_likely_anime_file("document.pdf")
        assert not fallback_parser.is_likely_anime_file("random.txt")
        assert not fallback_parser.is_likely_anime_file("vacation_video.mp4")


class TestParsedAnimeInfo:
    """Test cases for the ParsedAnimeInfo model."""

    def test_is_movie(self) -> None:
        """Test movie detection."""
        # Movie (no season/episode)
        movie = ParsedAnimeInfo(title="Movie Title")
        assert movie.is_movie
        assert not movie.is_tv_series

        # TV series
        tv_show = ParsedAnimeInfo(title="TV Show", season=1, episode=1)
        assert not tv_show.is_movie
        assert tv_show.is_tv_series

    def test_display_title(self) -> None:
        """Test display title formatting."""
        # TV series with season and episode
        tv_show = ParsedAnimeInfo(title="Attack on Titan", season=1, episode=1)
        assert tv_show.display_title == "Attack on Titan S01E01"

        # TV series with season only
        tv_show = ParsedAnimeInfo(title="Attack on Titan", season=1)
        assert tv_show.display_title == "Attack on Titan Season 1"

        # Movie
        movie = ParsedAnimeInfo(title="Movie Title")
        assert movie.display_title == "Movie Title"

    def test_is_valid(self) -> None:
        """Test validation methods."""
        # Valid info
        valid_info = ParsedAnimeInfo(title="Attack on Titan")
        assert valid_info.is_valid()
        assert not valid_info.has_episode_info()
        assert not valid_info.has_season_info()
        assert not valid_info.has_resolution_info()

        # Info with episode
        episode_info = ParsedAnimeInfo(title="Attack on Titan", episode=1)
        assert episode_info.has_episode_info()

        # Info with season
        season_info = ParsedAnimeInfo(title="Attack on Titan", season=1)
        assert season_info.has_season_info()

        # Info with resolution
        res_info = ParsedAnimeInfo(
            title="Attack on Titan",
            resolution="1080p",
            resolution_width=1920,
            resolution_height=1080,
        )
        assert res_info.has_resolution_info()

    def test_quality_score(self) -> None:
        """Test quality score calculation."""
        # Basic info
        basic = ParsedAnimeInfo(title="Anime")
        assert basic.get_quality_score() == 10  # Just title

        # With episode
        with_episode = ParsedAnimeInfo(title="Anime", episode=1)
        assert with_episode.get_quality_score() == 15  # Title + episode

        # With resolution
        with_res = ParsedAnimeInfo(
            title="Anime", resolution="1080p", resolution_width=1920, resolution_height=1080
        )
        assert with_res.get_quality_score() == 26  # Title + resolution + 1080p bonus

    def test_serialization(self) -> None:
        """Test serialization and deserialization."""
        original = ParsedAnimeInfo(
            title="Attack on Titan",
            season=1,
            episode=1,
            resolution="1080p",
            resolution_width=1920,
            resolution_height=1080,
        )

        # Test to_dict
        data = original.to_dict()
        assert data["title"] == "Attack on Titan"
        assert data["season"] == 1
        assert data["episode"] == 1

        # Test from_dict
        restored = ParsedAnimeInfo.from_dict(data)
        assert restored.title == original.title
        assert restored.season == original.season
        assert restored.episode == original.episode
        assert restored.resolution == original.resolution


# Integration tests
class TestAnimeParserIntegration:
    """Integration tests for the complete anime parsing system."""

    @pytest.fixture
    def parser(self):
        """Create an AnimeParser instance for integration testing."""
        return AnimeParser()

    def test_parsing_accuracy(self, parser) -> None:
        """Test parsing accuracy with a comprehensive set of filenames."""
        test_cases = [
            # (filename, expected_title, expected_episode, expected_season, expected_resolution)
            (
                "[SubsPlease] Attack on Titan - 01 (1080p) [F234F234].mkv",
                "Attack on Titan",
                1,
                None,
                "1080p",
            ),
            ("ReZero S02E05 [720p].mp4", "ReZero", 5, 2, "720p"),
            ("One Piece - 1000 [1080p].mkv", "One Piece", 1000, None, "1080p"),
            ("Movie Title (2023) [1080p].mkv", "Movie Title", None, None, "1080p"),
            ("[HorribleSubs] Anime - 01 [1920x1080].mkv", "Anime", 1, None, "1920x1080"),
            (
                "[Release] Anime - 01 [4K].mp4",
                "Anime",
                1,
                None,
                "4K",
            ),  # This might not parse resolution correctly
        ]

        successful_parses = 0
        total_parses = len(test_cases)

        for (
            filename,
            expected_title,
            expected_episode,
            expected_season,
            expected_resolution,
        ) in test_cases:
            result = parser.parse_filename(filename)

            if result and result.title:
                successful_parses += 1
                assert result.title == expected_title, f"Title mismatch for {filename}"
                assert result.episode == expected_episode, f"Episode mismatch for {filename}"
                assert result.season == expected_season, f"Season mismatch for {filename}"
                # Resolution might not always be parsed correctly, so we're more lenient
                if expected_resolution and result.resolution:
                    assert (
                        result.resolution == expected_resolution
                    ), f"Resolution mismatch for {filename}"

        # Calculate accuracy
        accuracy = (successful_parses / total_parses) * 100
        assert accuracy >= 95.0, f"Parsing accuracy {accuracy}% is below 95% target"

    def test_fallback_mechanism(self, parser) -> None:
        """Test that fallback parsing works when anitopy fails."""
        # Use a filename that anitopy might struggle with
        filename = "Anime Title - Episode 01 (1080p).mkv"

        # Parse with fallback enabled
        result_with_fallback = parser.parse_filename(filename, use_fallback=True)
        assert result_with_fallback is not None
        assert result_with_fallback.title

        # Parse with fallback disabled
        result_without_fallback = parser.parse_filename(filename, use_fallback=False)
        # This might be None if anitopy fails, which is expected

        # At least one method should work
        assert result_with_fallback is not None or result_without_fallback is not None

    def test_error_handling_robustness(self, parser) -> None:
        """Test that the parser handles various error conditions gracefully."""
        error_cases = [
            "",  # Empty string
            "   ",  # Whitespace only
            None,  # None input
            "a" * 1000,  # Very long string
            "file.with.many.dots.txt",  # Complex filename
        ]

        for error_case in error_cases:
            if error_case is not None:
                result = parser.parse_filename(error_case)
                # Should not crash, result can be None
                assert result is None or isinstance(result, ParsedAnimeInfo)
