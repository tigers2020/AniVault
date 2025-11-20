"""Unit tests for DuplicateResolver."""

from __future__ import annotations

from pathlib import Path

import pytest

from anivault.core.file_grouper.duplicate_resolver import (
    DuplicateResolver,
    ResolutionConfig,
    resolve_duplicates,
)
from anivault.core.models import ScannedFile
from anivault.core.parser.models import ParsingResult


def create_test_file(filename: str, file_size: int = 1_000_000) -> ScannedFile:
    """Helper to create test ScannedFile with required metadata."""
    return ScannedFile(
        file_path=Path(filename),
        metadata=ParsingResult(title="Test Anime"),
        file_size=file_size,
    )


class TestVersionExtraction:
    """Test version number extraction from filenames."""

    def test_extract_version_underscore_pattern(self) -> None:
        """Test _v1, _v2 pattern."""
        resolver = DuplicateResolver()
        assert resolver._extract_version("anime_ep01_v2_1080p.mkv") == 2
        assert resolver._extract_version("anime_ep01_v1_720p.mkv") == 1
        assert resolver._extract_version("anime_ep01_v10_1080p.mkv") == 10

    def test_extract_version_dot_pattern(self) -> None:
        """Test .v1, .v2 pattern."""
        resolver = DuplicateResolver()
        assert resolver._extract_version("anime.v2.mkv") == 2
        assert resolver._extract_version("anime.v1.1080p.mkv") == 1

    def test_extract_version_bracket_patterns(self) -> None:
        """Test [v1], (v2), {v3} patterns."""
        resolver = DuplicateResolver()
        assert resolver._extract_version("anime_[v2]_1080p.mkv") == 2
        assert resolver._extract_version("anime_(v3).mkv") == 3
        assert resolver._extract_version("anime_{v1}.mkv") == 1

    def test_extract_version_word_patterns(self) -> None:
        """Test version1, ver2 patterns."""
        resolver = DuplicateResolver()
        assert resolver._extract_version("anime_version2.mkv") == 2
        assert resolver._extract_version("anime_ver1.mkv") == 1
        assert resolver._extract_version("anime_ver_3.mkv") == 3

    def test_extract_version_no_version(self) -> None:
        """Test files without version tags."""
        resolver = DuplicateResolver()
        assert resolver._extract_version("anime_ep01_1080p.mkv") is None
        assert resolver._extract_version("anime.mkv") is None
        assert resolver._extract_version("video_file.mp4") is None

    def test_extract_version_edge_cases(self) -> None:
        """Test edge cases in version extraction."""
        resolver = DuplicateResolver()
        # Should not match 'version' as a word without number
        assert resolver._extract_version("anime_reversion.mkv") is None
        # Should match first version found
        assert resolver._extract_version("anime_v2_v3.mkv") == 2


class TestQualityExtraction:
    """Test quality score extraction from filenames."""

    def test_extract_quality_common_resolutions(self) -> None:
        """Test common resolution tags."""
        resolver = DuplicateResolver()
        assert resolver._extract_quality("anime_2160p.mkv") == 2160
        assert resolver._extract_quality("anime_1080p.mkv") == 1080
        assert resolver._extract_quality("anime_720p.mkv") == 720
        assert resolver._extract_quality("anime_480p.mkv") == 480

    def test_extract_quality_named_tags(self) -> None:
        """Test named quality tags (4K, UHD, FHD, HD, SD)."""
        resolver = DuplicateResolver()
        assert resolver._extract_quality("anime_4K.mkv") == 3840
        assert resolver._extract_quality("anime_UHD.mkv") == 3840
        assert resolver._extract_quality("anime_FHD.mkv") == 1080
        assert resolver._extract_quality("anime_HD.mkv") == 720
        assert resolver._extract_quality("anime_SD.mkv") == 360

    def test_extract_quality_no_quality_tag(self) -> None:
        """Test files without quality tags."""
        resolver = DuplicateResolver()
        assert resolver._extract_quality("anime.mkv") == 0
        assert resolver._extract_quality("video_file.mp4") == 0

    def test_extract_quality_case_insensitive(self) -> None:
        """Test case insensitivity."""
        resolver = DuplicateResolver()
        assert resolver._extract_quality("anime_1080P.mkv") == 1080
        assert resolver._extract_quality("anime_4k.mkv") == 3840
        assert resolver._extract_quality("anime_fhd.mkv") == 1080

    def test_extract_quality_custom_scores(self) -> None:
        """Test custom quality score mapping."""
        config = ResolutionConfig(quality_scores={"ULTRA": 5000})
        resolver = DuplicateResolver(config=config)
        assert resolver._extract_quality("anime_ULTRA.mkv") == 5000
        # Default scores should still work
        assert resolver._extract_quality("anime_1080p.mkv") == 1080


class TestDuplicateResolution:
    """Test duplicate file resolution logic."""

    def test_resolve_by_version(self) -> None:
        """Test resolution prioritizes version number."""
        files = [
            create_test_file("anime_v1_1080p.mkv", 800_000_000),
            create_test_file("anime_v2_720p.mkv", 500_000_000),
        ]
        resolver = DuplicateResolver()
        best = resolver.resolve_duplicates(files)
        # v2 should win even with lower quality
        assert best.file_path.name == "anime_v2_720p.mkv"

    def test_resolve_by_quality_when_same_version(self) -> None:
        """Test resolution uses quality when version is same."""
        files = [
            create_test_file("anime_v1_720p.mkv", 500_000_000),
            create_test_file("anime_v1_1080p.mkv", 800_000_000),
        ]
        resolver = DuplicateResolver()
        best = resolver.resolve_duplicates(files)
        # 1080p should win (same version)
        assert best.file_path.name == "anime_v1_1080p.mkv"

    def test_resolve_by_size_when_same_quality(self) -> None:
        """Test resolution uses file size as fallback."""
        files = [
            create_test_file("anime_1080p_small.mkv", 500_000_000),
            create_test_file("anime_1080p_large.mkv", 800_000_000),
        ]
        resolver = DuplicateResolver()
        best = resolver.resolve_duplicates(files)
        # Larger file should win (same version, same quality)
        assert best.file_path.name == "anime_1080p_large.mkv"

    def test_resolve_single_file(self) -> None:
        """Test resolution with single file."""
        files = [create_test_file("anime.mkv", 1_000_000)]
        resolver = DuplicateResolver()
        best = resolver.resolve_duplicates(files)
        assert best.file_path.name == "anime.mkv"

    def test_resolve_empty_list_raises(self) -> None:
        """Test resolution with empty list raises ValueError."""
        resolver = DuplicateResolver()
        with pytest.raises(ValueError, match="empty"):
            resolver.resolve_duplicates([])

    def test_resolve_no_version_tags(self) -> None:
        """Test resolution when no version tags present."""
        files = [
            create_test_file("anime_720p.mkv", 500_000_000),
            create_test_file("anime_1080p.mkv", 800_000_000),
        ]
        resolver = DuplicateResolver()
        best = resolver.resolve_duplicates(files)
        # Should use quality (1080p > 720p)
        assert best.file_path.name == "anime_1080p.mkv"

    def test_resolve_no_quality_tags(self) -> None:
        """Test resolution when no quality tags present."""
        files = [
            create_test_file("anime_v1.mkv", 500_000_000),
            create_test_file("anime_v2.mkv", 400_000_000),
        ]
        resolver = DuplicateResolver()
        best = resolver.resolve_duplicates(files)
        # Should use version (v2 > v1)
        assert best.file_path.name == "anime_v2.mkv"

    def test_resolve_all_equal(self) -> None:
        """Test resolution when all criteria are equal."""
        files = [
            create_test_file("anime_a.mkv", 1_000_000),
            create_test_file("anime_b.mkv", 1_000_000),
        ]
        resolver = DuplicateResolver()
        best = resolver.resolve_duplicates(files)
        # Should return first file (stable sort)
        assert best.file_path.name in ["anime_a.mkv", "anime_b.mkv"]


class TestResolutionConfig:
    """Test configuration options."""

    def test_config_prefer_lower_version(self) -> None:
        """Test configuration to prefer lower versions."""
        config = ResolutionConfig(prefer_higher_version=False)
        resolver = DuplicateResolver(config=config)
        files = [
            create_test_file("anime_v1.mkv", 1_000_000),
            create_test_file("anime_v2.mkv", 1_000_000),
        ]
        best = resolver.resolve_duplicates(files)
        # v1 should win (prefer_higher_version=False)
        assert best.file_path.name == "anime_v1.mkv"

    def test_config_prefer_lower_quality(self) -> None:
        """Test configuration to prefer lower quality."""
        config = ResolutionConfig(prefer_higher_quality=False)
        resolver = DuplicateResolver(config=config)
        files = [
            create_test_file("anime_720p.mkv", 1_000_000),
            create_test_file("anime_1080p.mkv", 1_000_000),
        ]
        best = resolver.resolve_duplicates(files)
        # 720p should win (prefer_higher_quality=False)
        assert best.file_path.name == "anime_720p.mkv"

    def test_config_prefer_smaller_size(self) -> None:
        """Test configuration to prefer smaller files."""
        config = ResolutionConfig(prefer_larger_size=False)
        resolver = DuplicateResolver(config=config)
        files = [
            create_test_file("anime_small.mkv", 500_000_000),
            create_test_file("anime_large.mkv", 800_000_000),
        ]
        best = resolver.resolve_duplicates(files)
        # Smaller file should win (prefer_larger_size=False)
        assert best.file_path.name == "anime_small.mkv"


class TestConvenienceFunction:
    """Test the convenience function."""

    def test_resolve_duplicates_function(self) -> None:
        """Test convenience function works correctly."""
        files = [
            create_test_file("anime_v1.mkv", 500_000_000),
            create_test_file("anime_v2.mkv", 600_000_000),
        ]
        best = resolve_duplicates(files)
        assert best.file_path.name == "anime_v2.mkv"

    def test_resolve_duplicates_with_config(self) -> None:
        """Test convenience function with custom config."""
        config = ResolutionConfig(prefer_higher_version=False)
        files = [
            create_test_file("anime_v1.mkv", 500_000_000),
            create_test_file("anime_v2.mkv", 600_000_000),
        ]
        best = resolve_duplicates(files, config=config)
        assert best.file_path.name == "anime_v1.mkv"
