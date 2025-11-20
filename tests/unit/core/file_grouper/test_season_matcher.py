"""Unit tests for SeasonEpisodeMatcher."""

from __future__ import annotations

from pathlib import Path

import pytest

from anivault.core.file_grouper.matchers.season_matcher import SeasonEpisodeMatcher
from anivault.core.models import ScannedFile
from anivault.core.parser.models import ParsingResult


def create_test_file(
    filename: str,
    title: str,
    season: int | None = None,
    episode: int | None = None,
) -> ScannedFile:
    """Helper to create test ScannedFile with season/episode metadata."""
    metadata = ParsingResult(
        title=title,
        season=season,
        episode=episode,
    )
    return ScannedFile(
        file_path=Path(filename),
        metadata=metadata,
        file_size=1_000_000,
    )


class TestMetadataExtraction:
    """Test metadata extraction from files."""

    def test_extract_with_full_metadata(self) -> None:
        """Test extraction with complete season/episode metadata."""
        matcher = SeasonEpisodeMatcher()
        file = create_test_file(
            "anime_S01E01.mkv", "Attack on Titan", season=1, episode=1
        )

        metadata = matcher._extract_metadata(file)

        assert metadata is not None
        series, season, episode = metadata
        assert series == "Attack on Titan"
        assert season == 1
        assert episode == 1

    def test_extract_without_season(self) -> None:
        """Test extraction defaults to season 1 when missing."""
        matcher = SeasonEpisodeMatcher()
        file = create_test_file("anime_01.mkv", "Naruto", season=None, episode=1)

        metadata = matcher._extract_metadata(file)

        assert metadata is not None
        series, season, episode = metadata
        assert series == "Naruto"
        assert season == 1  # Default
        assert episode == 1

    def test_extract_without_episode(self) -> None:
        """Test extraction allows None episode."""
        matcher = SeasonEpisodeMatcher()
        file = create_test_file("anime_S02.mkv", "Bleach", season=2, episode=None)

        metadata = matcher._extract_metadata(file)

        assert metadata is not None
        series, season, episode = metadata
        assert series == "Bleach"
        assert season == 2
        assert episode is None

    def test_extract_without_title(self) -> None:
        """Test extraction returns None when title missing."""
        matcher = SeasonEpisodeMatcher()
        metadata_obj = ParsingResult(title="", season=1, episode=1)
        file = ScannedFile(
            file_path=Path("unknown.mkv"),
            metadata=metadata_obj,
            file_size=1_000_000,
        )

        metadata = matcher._extract_metadata(file)

        assert metadata is None

    def test_extract_without_metadata(self) -> None:
        """Test extraction returns None when metadata missing."""
        matcher = SeasonEpisodeMatcher()
        # Create file with None metadata
        metadata_obj = ParsingResult(title="Title")
        file = ScannedFile(
            file_path=Path("file.mkv"),
            metadata=metadata_obj,
            file_size=1_000_000,
        )
        file.metadata = None  # type: ignore

        metadata = matcher._extract_metadata(file)

        assert metadata is None


class TestSeasonGrouping:
    """Test season-based file grouping."""

    def test_group_same_season(self) -> None:
        """Test grouping files from the same season."""
        matcher = SeasonEpisodeMatcher()
        files = [
            create_test_file("ep01.mkv", "Anime", season=1, episode=1),
            create_test_file("ep02.mkv", "Anime", season=1, episode=2),
            create_test_file("ep03.mkv", "Anime", season=1, episode=3),
        ]

        groups = matcher.match(files)

        assert len(groups) == 1
        assert groups[0].title == "Anime S01"
        assert len(groups[0].files) == 3

    def test_group_different_seasons(self) -> None:
        """Test grouping files from different seasons."""
        matcher = SeasonEpisodeMatcher()
        files = [
            create_test_file("s01e01.mkv", "Anime", season=1, episode=1),
            create_test_file("s01e02.mkv", "Anime", season=1, episode=2),
            create_test_file("s02e01.mkv", "Anime", season=2, episode=1),
            create_test_file("s02e02.mkv", "Anime", season=2, episode=2),
        ]

        groups = matcher.match(files)

        assert len(groups) == 2
        titles = {group.title for group in groups}
        assert titles == {"Anime S01", "Anime S02"}

        # Check file counts
        s01_group = [g for g in groups if g.title == "Anime S01"][0]
        s02_group = [g for g in groups if g.title == "Anime S02"][0]
        assert len(s01_group.files) == 2
        assert len(s02_group.files) == 2

    def test_group_different_series(self) -> None:
        """Test grouping files from different series."""
        matcher = SeasonEpisodeMatcher()
        files = [
            create_test_file("naruto.mkv", "Naruto", season=1, episode=1),
            create_test_file("bleach.mkv", "Bleach", season=1, episode=1),
            create_test_file("onepiece.mkv", "One Piece", season=1, episode=1),
        ]

        groups = matcher.match(files)

        assert len(groups) == 3
        titles = {group.title for group in groups}
        assert titles == {"Naruto S01", "Bleach S01", "One Piece S01"}

    def test_group_mixed_seasons(self) -> None:
        """Test grouping with mixed series and seasons."""
        matcher = SeasonEpisodeMatcher()
        files = [
            create_test_file("a_s01e01.mkv", "Anime A", season=1, episode=1),
            create_test_file("a_s01e02.mkv", "Anime A", season=1, episode=2),
            create_test_file("a_s02e01.mkv", "Anime A", season=2, episode=1),
            create_test_file("b_s01e01.mkv", "Anime B", season=1, episode=1),
        ]

        groups = matcher.match(files)

        assert len(groups) == 3
        titles = {group.title for group in groups}
        assert titles == {"Anime A S01", "Anime A S02", "Anime B S01"}

    def test_group_empty_list(self) -> None:
        """Test grouping empty file list."""
        matcher = SeasonEpisodeMatcher()

        groups = matcher.match([])

        assert len(groups) == 0

    def test_group_single_file(self) -> None:
        """Test grouping single file."""
        matcher = SeasonEpisodeMatcher()
        files = [create_test_file("anime.mkv", "Anime", season=1, episode=1)]

        groups = matcher.match(files)

        assert len(groups) == 1
        assert groups[0].title == "Anime S01"
        assert len(groups[0].files) == 1


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_skip_files_without_metadata(self) -> None:
        """Test that files without metadata are skipped."""
        matcher = SeasonEpisodeMatcher()
        # Create file with no metadata
        file_no_meta = ScannedFile(
            file_path=Path("no_meta.mkv"),
            metadata=ParsingResult(title="Title"),
            file_size=1_000_000,
        )
        file_no_meta.metadata = None  # type: ignore

        # Create file with valid metadata
        file_valid = create_test_file("valid.mkv", "Anime", season=1, episode=1)

        files = [file_no_meta, file_valid]
        groups = matcher.match(files)

        # Only valid file should be grouped
        assert len(groups) == 1
        assert len(groups[0].files) == 1

    def test_skip_files_without_title(self) -> None:
        """Test that files without title are skipped."""
        matcher = SeasonEpisodeMatcher()
        files = [
            create_test_file("no_title.mkv", "", season=1, episode=1),
            create_test_file("valid.mkv", "Anime", season=1, episode=1),
        ]

        groups = matcher.match(files)

        # Only valid file should be grouped
        assert len(groups) == 1
        assert len(groups[0].files) == 1

    def test_default_season_to_1(self) -> None:
        """Test that missing season defaults to 1."""
        matcher = SeasonEpisodeMatcher()
        files = [
            create_test_file("ep01.mkv", "Anime", season=None, episode=1),
            create_test_file("ep02.mkv", "Anime", season=None, episode=2),
        ]

        groups = matcher.match(files)

        assert len(groups) == 1
        assert groups[0].title == "Anime S01"
        assert len(groups[0].files) == 2

    def test_handle_high_season_numbers(self) -> None:
        """Test handling of high season numbers."""
        matcher = SeasonEpisodeMatcher()
        files = [
            create_test_file("ep01.mkv", "Long Running", season=10, episode=1),
            create_test_file("ep02.mkv", "Long Running", season=15, episode=1),
        ]

        groups = matcher.match(files)

        assert len(groups) == 2
        titles = {group.title for group in groups}
        assert titles == {"Long Running S10", "Long Running S15"}

    def test_unicode_series_names(self) -> None:
        """Test handling of Unicode characters in series names."""
        matcher = SeasonEpisodeMatcher()
        files = [
            create_test_file("ep01.mkv", "進撃の巨人", season=1, episode=1),
            create_test_file("ep02.mkv", "進撃の巨人", season=1, episode=2),
        ]

        groups = matcher.match(files)

        assert len(groups) == 1
        assert groups[0].title == "進撃の巨人 S01"
        assert len(groups[0].files) == 2


class TestComponentInterface:
    """Test BaseMatcher protocol compliance."""

    def test_has_component_name(self) -> None:
        """Test matcher has component_name attribute."""
        matcher = SeasonEpisodeMatcher()

        assert hasattr(matcher, "component_name")
        assert matcher.component_name == "season"

    def test_match_signature(self) -> None:
        """Test match method signature is correct."""
        matcher = SeasonEpisodeMatcher()

        # Should accept list[ScannedFile] and return list[Group]
        files = [create_test_file("anime.mkv", "Title", season=1, episode=1)]
        result = matcher.match(files)

        assert isinstance(result, list)
        assert all(
            hasattr(group, "title") and hasattr(group, "files") for group in result
        )
