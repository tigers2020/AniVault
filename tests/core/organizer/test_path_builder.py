"""Unit tests for PathBuilder service.

This module tests the path construction functionality,
including series title extraction, resolution organization,
and filename sanitization.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from anivault.core.matching.models import MatchResult
from anivault.core.models import ScannedFile
from anivault.core.organizer.path_builder import PathBuilder, PathContext
from anivault.core.parser.models import ParsingResult

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def path_builder() -> PathBuilder:
    """Create PathBuilder instance."""
    return PathBuilder()


@pytest.fixture
def mock_settings() -> Mock:
    """Create mock settings object."""
    settings = Mock()
    settings.app = Mock()
    return settings


# ============================================================================
# PathContext Tests (3 tests)
# ============================================================================


class TestPathContext:
    """Tests for PathContext dataclass."""

    def test_path_context_creation(self, tmp_path: Path) -> None:
        """Test creating a valid PathContext."""
        scanned_file = ScannedFile(
            file_path=tmp_path / "test.mkv",
            metadata=ParsingResult(title="Test", quality=None, other_info={}),
            file_size=1024000,
            last_modified=1640995200.0,
        )

        context = PathContext(
            scanned_file=scanned_file,
            series_has_mixed_resolutions=False,
            target_folder=tmp_path,
            media_type="TV",
            organize_by_resolution=False,
        )

        assert context.scanned_file == scanned_file
        assert context.series_has_mixed_resolutions is False
        assert context.target_folder == tmp_path
        assert context.media_type == "TV"
        assert context.organize_by_resolution is False

    def test_path_context_immutable(self, tmp_path: Path) -> None:
        """Test PathContext is immutable (frozen dataclass)."""
        scanned_file = ScannedFile(
            file_path=tmp_path / "test.mkv",
            metadata=ParsingResult(title="Test", quality=None, other_info={}),
            file_size=1024000,
            last_modified=1640995200.0,
        )

        context = PathContext(
            scanned_file=scanned_file,
            series_has_mixed_resolutions=False,
            target_folder=tmp_path,
            media_type="TV",
            organize_by_resolution=False,
        )

        # Attempt to modify should raise error (frozen dataclass)
        with pytest.raises(AttributeError):
            context.media_type = "Movies"  # type: ignore[misc]

    def test_path_context_validation_empty_media_type(self, tmp_path: Path) -> None:
        """Test PathContext validation rejects empty media_type."""
        scanned_file = ScannedFile(
            file_path=tmp_path / "test.mkv",
            metadata=ParsingResult(title="Test", quality=None, other_info={}),
            file_size=1024000,
            last_modified=1640995200.0,
        )

        with pytest.raises(ValueError, match="media_type cannot be empty"):
            PathContext(
                scanned_file=scanned_file,
                series_has_mixed_resolutions=False,
                target_folder=tmp_path,
                media_type="",  # Empty string
                organize_by_resolution=False,
            )


# ============================================================================
# Series Title Extraction Tests (5 tests)
# ============================================================================


class TestSeriesTitleExtraction:
    """Tests for series title extraction logic."""

    def test_extract_series_title_from_tmdb(
        self, path_builder: PathBuilder, tmp_path: Path
    ) -> None:
        """Test extracting series title from TMDB match result (priority 1)."""
        match_result = MatchResult(
            title="Attack on Titan",
            tmdb_id=1429,
            year=2013,
            confidence_score=0.95,
            media_type="tv",
        )

        scanned_file = ScannedFile(
            file_path=tmp_path / "some_file.mkv",
            metadata=ParsingResult(
                title="Different Title",  # Should be overridden by TMDB
                quality=None,
                other_info={"match_result": match_result},
            ),
            file_size=1024000,
            last_modified=1640995200.0,
        )

        result = path_builder._extract_series_title(scanned_file)
        assert result == "Attack on Titan"

    def test_extract_series_title_from_parsed_metadata(
        self, path_builder: PathBuilder, tmp_path: Path
    ) -> None:
        """Test extracting series title from parsed metadata (priority 2)."""
        scanned_file = ScannedFile(
            file_path=tmp_path / "some_file.mkv",
            metadata=ParsingResult(
                title="Demon Slayer",
                quality=None,
                other_info={},  # No TMDB match
            ),
            file_size=1024000,
            last_modified=1640995200.0,
        )

        result = path_builder._extract_series_title(scanned_file)
        assert result == "Demon Slayer"

    def test_extract_series_title_from_filename_bracket(
        self, path_builder: PathBuilder, tmp_path: Path
    ) -> None:
        """Test extracting series title from filename with brackets (priority 3)."""
        scanned_file = ScannedFile(
            file_path=tmp_path / "[SubGroup] One Piece - 01.mkv",
            metadata=ParsingResult(
                title="",  # Empty title
                quality=None,
                other_info={},
            ),
            file_size=1024000,
            last_modified=1640995200.0,
        )

        result = path_builder._extract_series_title(scanned_file)
        assert "SubGroup" in result

    def test_extract_series_title_from_filename_dash(
        self, path_builder: PathBuilder, tmp_path: Path
    ) -> None:
        """Test extracting series title from filename with dash pattern."""
        scanned_file = ScannedFile(
            file_path=tmp_path / "Jujutsu Kaisen - 05.mkv",
            metadata=ParsingResult(
                title="",
                quality=None,
                other_info={},
            ),
            file_size=1024000,
            last_modified=1640995200.0,
        )

        result = path_builder._extract_series_title(scanned_file)
        assert "Jujutsu Kaisen" in result

    def test_extract_series_title_fallback_uses_stem(
        self, path_builder: PathBuilder, tmp_path: Path
    ) -> None:
        """Test series title fallback to filename stem."""
        scanned_file = ScannedFile(
            file_path=tmp_path / "random_anime_file.mkv",  # No pattern match
            metadata=ParsingResult(
                title="",  # Empty
                quality=None,
                other_info={},
            ),
            file_size=1024000,
            last_modified=1640995200.0,
        )

        result = path_builder._extract_series_title(scanned_file)
        # Should fall back to filename stem
        assert result == "random_anime_file"


# ============================================================================
# Season Extraction Tests (2 tests)
# ============================================================================


class TestSeasonExtraction:
    """Tests for season number extraction."""

    def test_extract_season_number_with_value(
        self, path_builder: PathBuilder, tmp_path: Path
    ) -> None:
        """Test extracting season number when provided."""
        scanned_file = ScannedFile(
            file_path=tmp_path / "anime.mkv",
            metadata=ParsingResult(
                title="Test",
                season=2,
                quality=None,
                other_info={},
            ),
            file_size=1024000,
            last_modified=1640995200.0,
        )

        result = path_builder._extract_season_number(scanned_file)
        assert result == 2

    def test_extract_season_number_default(
        self, path_builder: PathBuilder, tmp_path: Path
    ) -> None:
        """Test season number defaults to 1 when not provided."""
        scanned_file = ScannedFile(
            file_path=tmp_path / "anime.mkv",
            metadata=ParsingResult(
                title="Test",
                season=None,  # Not provided
                quality=None,
                other_info={},
            ),
            file_size=1024000,
            last_modified=1640995200.0,
        )

        result = path_builder._extract_season_number(scanned_file)
        assert result == 1


# ============================================================================
# Season Directory Tests (1 test)
# ============================================================================


class TestSeasonDirectory:
    """Tests for season directory string building."""

    @pytest.mark.parametrize(
        ("season_number", "expected"),
        [
            (1, "Season 01"),
            (2, "Season 02"),
            (10, "Season 10"),
            (99, "Season 99"),
        ],
    )
    def test_build_season_dir(self, season_number: int, expected: str) -> None:
        """Test season directory formatting."""
        result = PathBuilder._build_season_dir(season_number)
        assert result == expected


# ============================================================================
# Resolution Extraction Tests (4 tests)
# ============================================================================


class TestResolutionExtraction:
    """Tests for resolution extraction logic."""

    def test_extract_resolution_from_metadata(
        self, path_builder: PathBuilder, tmp_path: Path
    ) -> None:
        """Test extracting resolution from metadata quality field."""
        scanned_file = ScannedFile(
            file_path=tmp_path / "anime.mkv",
            metadata=ParsingResult(
                title="Test",
                quality="1080p",  # Resolution in metadata
                other_info={},
            ),
            file_size=1024000,
            last_modified=1640995200.0,
        )

        result = path_builder._extract_resolution(scanned_file)
        assert result == "1080P"

    @pytest.mark.parametrize(
        ("filename", "expected"),
        [
            ("anime_[1080p].mkv", "1080P"),
            ("anime_(720p).mp4", "720P"),
            ("anime 4K.mkv", "4K"),
            ("anime.480p.avi", "480P"),
            ("anime SD.mkv", "SD"),
        ],
    )
    def test_extract_resolution_from_filename_patterns(
        self, path_builder: PathBuilder, tmp_path: Path, filename: str, expected: str
    ) -> None:
        """Test extracting resolution from various filename patterns."""
        scanned_file = ScannedFile(
            file_path=tmp_path / filename,
            metadata=ParsingResult(
                title="Test",
                quality=None,  # No metadata quality
                other_info={},
            ),
            file_size=1024000,
            last_modified=1640995200.0,
        )

        result = path_builder._extract_resolution(scanned_file)
        assert result == expected

    @pytest.mark.parametrize(
        ("filename", "expected"),
        [
            ("anime_1920x1080.mkv", "1080P"),
            ("anime_1280x720.mp4", "720P"),
            ("anime_854x480.avi", "480P"),
            ("anime_640x360.mkv", "SD"),
        ],
    )
    def test_extract_resolution_from_dimensions(
        self, path_builder: PathBuilder, tmp_path: Path, filename: str, expected: str
    ) -> None:
        """Test extracting resolution from dimension patterns."""
        scanned_file = ScannedFile(
            file_path=tmp_path / filename,
            metadata=ParsingResult(
                title="Test",
                quality=None,
                other_info={},
            ),
            file_size=1024000,
            last_modified=1640995200.0,
        )

        result = path_builder._extract_resolution(scanned_file)
        assert result == expected

    def test_extract_resolution_returns_none(
        self, path_builder: PathBuilder, tmp_path: Path
    ) -> None:
        """Test resolution extraction returns None when not found."""
        scanned_file = ScannedFile(
            file_path=tmp_path / "anime_episode_01.mkv",  # No resolution info
            metadata=ParsingResult(
                title="Test",
                quality=None,
                other_info={},
            ),
            file_size=1024000,
            last_modified=1640995200.0,
        )

        result = path_builder._extract_resolution(scanned_file)
        assert result is None


# ============================================================================
# Dimension Mapping Tests (1 test)
# ============================================================================


class TestDimensionMapping:
    """Tests for dimension to resolution mapping."""

    @pytest.mark.parametrize(
        ("width", "height", "expected"),
        [
            (1920, 1080, "1080P"),
            (1280, 720, "720P"),
            (854, 480, "480P"),
            (640, 360, "SD"),
            (3840, 2160, "1080P"),  # 4K maps to 1080P
        ],
    )
    def test_map_dimensions_to_resolution(
        self, width: int, height: int, expected: str
    ) -> None:
        """Test mapping video dimensions to resolution."""
        result = PathBuilder._map_dimensions_to_resolution(width, height)
        assert result == expected


# ============================================================================
# Filename Sanitization Tests (5 tests)
# ============================================================================


class TestFilenameSanitization:
    """Tests for filename sanitization logic."""

    @pytest.mark.parametrize(
        ("filename", "expected"),
        [
            ("Attack<>Titan?", "Attack Titan"),
            ("My_Series_Name", "My Series Name"),
            ("Series:Name", "Series Name"),
            ('Quote"Test', "Quote Test"),
            ("Path/Test", "Path Test"),
            ("Pipe|Test", "Pipe Test"),
            ("Star*Test", "Star Test"),
        ],
    )
    def test_sanitize_filename_invalid_chars(
        self, filename: str, expected: str
    ) -> None:
        """Test sanitization of invalid characters."""
        result = PathBuilder.sanitize_filename(filename)
        assert result == expected

    def test_sanitize_filename_multiple_spaces(self) -> None:
        """Test collapsing multiple spaces."""
        result = PathBuilder.sanitize_filename("Test    Multiple   Spaces")
        assert result == "Test Multiple Spaces"

    def test_sanitize_filename_strip_whitespace(self) -> None:
        """Test stripping leading/trailing whitespace and dots."""
        result = PathBuilder.sanitize_filename("  Test Series  ")
        assert result == "Test Series"

        result = PathBuilder.sanitize_filename("...Test Series...")
        assert result == "Test Series"

    def test_sanitize_filename_empty_fallback(self) -> None:
        """Test empty filename fallback to 'Unknown'."""
        result = PathBuilder.sanitize_filename("")
        assert result == "Unknown"

        result = PathBuilder.sanitize_filename("   ")
        assert result == "Unknown"

    def test_sanitize_filename_underscores_to_spaces(self) -> None:
        """Test conversion of underscores to spaces."""
        result = PathBuilder.sanitize_filename("My_Awesome_Series")
        assert result == "My Awesome Series"


# ============================================================================
# Full Path Construction Tests (6 tests)
# ============================================================================


class TestFullPathConstruction:
    """Tests for complete path construction."""

    def test_build_path_basic(self, path_builder: PathBuilder, tmp_path: Path) -> None:
        """Test basic path construction without resolution organization."""
        scanned_file = ScannedFile(
            file_path=tmp_path / "anime_episode_01.mkv",
            metadata=ParsingResult(
                title="Test Anime",
                season=1,
                quality=None,
                other_info={},
            ),
            file_size=1024000,
            last_modified=1640995200.0,
        )

        context = PathContext(
            scanned_file=scanned_file,
            series_has_mixed_resolutions=False,
            target_folder=Path("/media"),
            media_type="TV",
            organize_by_resolution=False,
        )

        result = path_builder.build_path(context)

        # Expected: /media/TV/Test Anime/Season 01/anime_episode_01.mkv
        assert result.parts[-5:] == (
            "media",
            "TV",
            "Test Anime",
            "Season 01",
            "anime_episode_01.mkv",
        )

    def test_build_path_with_tmdb_title(
        self, path_builder: PathBuilder, tmp_path: Path
    ) -> None:
        """Test path construction with TMDB matched title."""
        match_result = MatchResult(
            title="진격의 거인",  # Korean title
            tmdb_id=1429,
            year=2013,
            confidence_score=0.95,
            media_type="tv",
        )

        scanned_file = ScannedFile(
            file_path=tmp_path / "[SubGroup] Attack on Titan - 01.mkv",
            metadata=ParsingResult(
                title="Attack on Titan",
                season=1,
                quality=None,
                other_info={"match_result": match_result},
            ),
            file_size=1024000,
            last_modified=1640995200.0,
        )

        context = PathContext(
            scanned_file=scanned_file,
            series_has_mixed_resolutions=False,
            target_folder=Path("/media"),
            media_type="TV",
            organize_by_resolution=False,
        )

        result = path_builder.build_path(context)

        # Should use TMDB title (Korean)
        assert "진격의 거인" in result.parts

    def test_build_path_with_resolution_high(
        self, path_builder: PathBuilder, tmp_path: Path
    ) -> None:
        """Test path construction with high resolution organization."""
        scanned_file = ScannedFile(
            file_path=tmp_path / "anime_1080p.mkv",
            metadata=ParsingResult(
                title="Test Anime",
                season=1,
                quality="1080p",
                other_info={},
            ),
            file_size=1024000,
            last_modified=1640995200.0,
        )

        context = PathContext(
            scanned_file=scanned_file,
            series_has_mixed_resolutions=True,  # Mixed resolutions
            target_folder=Path("/media"),
            media_type="TV",
            organize_by_resolution=True,  # Feature enabled
        )

        result = path_builder.build_path(context)

        # High resolution: /media/TV/Test Anime/Season 01/anime_1080p.mkv
        # Should NOT include low_res folder
        assert "low_res" not in result.parts
        assert result.parts[-5:] == (
            "media",
            "TV",
            "Test Anime",
            "Season 01",
            "anime_1080p.mkv",
        )

    def test_build_path_with_resolution_low(
        self, path_builder: PathBuilder, tmp_path: Path
    ) -> None:
        """Test path construction with low resolution organization."""
        scanned_file = ScannedFile(
            file_path=tmp_path / "anime_720p.mkv",
            metadata=ParsingResult(
                title="Test Anime",
                season=1,
                quality="720p",
                other_info={},
            ),
            file_size=1024000,
            last_modified=1640995200.0,
        )

        context = PathContext(
            scanned_file=scanned_file,
            series_has_mixed_resolutions=True,  # Mixed resolutions
            target_folder=Path("/media"),
            media_type="TV",
            organize_by_resolution=True,  # Feature enabled
        )

        result = path_builder.build_path(context)

        # Low resolution: /media/TV/low_res/Test Anime/Season 01/anime_720p.mkv
        assert "low_res" in result.parts
        assert result.parts[-6:] == (
            "media",
            "TV",
            "low_res",
            "Test Anime",
            "Season 01",
            "anime_720p.mkv",
        )

    def test_build_path_no_resolution_org_when_disabled(
        self, path_builder: PathBuilder, tmp_path: Path
    ) -> None:
        """Test no resolution organization when feature is disabled."""
        scanned_file = ScannedFile(
            file_path=tmp_path / "anime_720p.mkv",
            metadata=ParsingResult(
                title="Test Anime",
                season=1,
                quality="720p",
                other_info={},
            ),
            file_size=1024000,
            last_modified=1640995200.0,
        )

        context = PathContext(
            scanned_file=scanned_file,
            series_has_mixed_resolutions=True,
            target_folder=Path("/media"),
            media_type="TV",
            organize_by_resolution=False,  # Feature DISABLED
        )

        result = path_builder.build_path(context)

        # Should NOT include low_res folder even though it's low resolution
        assert "low_res" not in result.parts

    def test_build_path_no_resolution_org_single_quality(
        self, path_builder: PathBuilder, tmp_path: Path
    ) -> None:
        """Test no resolution organization when series has single quality."""
        scanned_file = ScannedFile(
            file_path=tmp_path / "anime_720p.mkv",
            metadata=ParsingResult(
                title="Test Anime",
                season=1,
                quality="720p",
                other_info={},
            ),
            file_size=1024000,
            last_modified=1640995200.0,
        )

        context = PathContext(
            scanned_file=scanned_file,
            series_has_mixed_resolutions=False,  # Single quality
            target_folder=Path("/media"),
            media_type="TV",
            organize_by_resolution=True,
        )

        result = path_builder.build_path(context)

        # Should NOT include low_res folder because series has single quality
        assert "low_res" not in result.parts
