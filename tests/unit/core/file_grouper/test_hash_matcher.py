"""Unit tests for HashSimilarityMatcher."""

from __future__ import annotations

from pathlib import Path

import pytest

from anivault.core.file_grouper.grouper import TitleExtractor
from anivault.core.file_grouper.matchers.hash_matcher import (
    HashSimilarityMatcher,
    MAX_TITLE_LENGTH,
)
from anivault.core.models import ScannedFile
from anivault.core.parser.models import ParsingResult


def create_test_file(filename: str, title: str | None = None) -> ScannedFile:
    """Helper to create test ScannedFile with metadata."""
    metadata = ParsingResult(title=title or "Test Anime")
    return ScannedFile(
        file_path=Path(filename),
        metadata=metadata,
        file_size=1_000_000,
    )


class TestTitleNormalization:
    """Test title normalization logic."""

    def test_normalize_lowercase(self) -> None:
        """Test normalization converts to lowercase."""
        extractor = TitleExtractor()
        matcher = HashSimilarityMatcher(title_extractor=extractor)

        assert matcher._normalize_title("Attack on Titan") == "attack on titan"
        assert matcher._normalize_title("NARUTO") == "naruto"

    def test_normalize_remove_punctuation(self) -> None:
        """Test normalization removes punctuation."""
        extractor = TitleExtractor()
        matcher = HashSimilarityMatcher(title_extractor=extractor)

        assert matcher._normalize_title("Attack on Titan!") == "attack on titan"
        assert matcher._normalize_title("Sword.Art.Online") == "swordartonline"
        assert matcher._normalize_title("Title-With-Dashes") == "titlewithdashes"
        assert matcher._normalize_title("Title@#$%Special") == "titlespecial"

    def test_normalize_whitespace(self) -> None:
        """Test normalization handles whitespace correctly."""
        extractor = TitleExtractor()
        matcher = HashSimilarityMatcher(title_extractor=extractor)

        assert matcher._normalize_title("  Multiple   Spaces  ") == "multiple spaces"
        # Tab and newline are kept as whitespace, then normalized to single space
        assert matcher._normalize_title("Tab\tTitle") == "tab title"
        assert matcher._normalize_title("New\nLine") == "new line"

    def test_normalize_length_limit(self) -> None:
        """Test normalization truncates overly long titles."""
        extractor = TitleExtractor()
        matcher = HashSimilarityMatcher(title_extractor=extractor)

        long_title = "a" * (MAX_TITLE_LENGTH + 100)
        normalized = matcher._normalize_title(long_title)

        assert len(normalized) == MAX_TITLE_LENGTH

    def test_normalize_empty_string(self) -> None:
        """Test normalization handles empty strings."""
        extractor = TitleExtractor()
        matcher = HashSimilarityMatcher(title_extractor=extractor)

        assert matcher._normalize_title("") == ""
        assert matcher._normalize_title("   ") == ""


class TestHashGrouping:
    """Test hash-based file grouping."""

    def test_group_identical_titles(self) -> None:
        """Test grouping files with identical normalized titles."""
        extractor = TitleExtractor()
        matcher = HashSimilarityMatcher(title_extractor=extractor)

        files = [
            create_test_file("Anime.Title.S01E01.mkv", "Anime Title"),
            create_test_file("Anime_Title_S01E02.mkv", "Anime Title"),
            create_test_file("Anime-Title-S01E03.mkv", "Anime Title"),
        ]

        groups = matcher.match(files)

        assert len(groups) == 1
        assert len(groups[0].files) == 3
        assert groups[0].title == "Anime Title"

    def test_group_different_titles(self) -> None:
        """Test that different titles create separate groups."""
        extractor = TitleExtractor()
        matcher = HashSimilarityMatcher(title_extractor=extractor)

        files = [
            create_test_file("Naruto.S01E01.mkv", "Naruto"),
            create_test_file("Bleach.S01E01.mkv", "Bleach"),
            create_test_file("OnePiece.S01E01.mkv", "One Piece"),
        ]

        groups = matcher.match(files)

        assert len(groups) == 3
        titles = {group.title for group in groups}
        assert titles == {"Naruto", "Bleach", "One Piece"}

    def test_group_case_insensitive(self) -> None:
        """Test grouping is case-insensitive."""
        extractor = TitleExtractor()
        matcher = HashSimilarityMatcher(title_extractor=extractor)

        files = [
            create_test_file("anime.mkv", "Anime Title"),
            create_test_file("ANIME.mkv", "ANIME TITLE"),
            create_test_file("AnImE.mkv", "AnImE TiTlE"),
        ]

        groups = matcher.match(files)

        assert len(groups) == 1
        assert len(groups[0].files) == 3

    def test_group_punctuation_removed(self) -> None:
        """Test that punctuation (except underscore) is removed."""
        extractor = TitleExtractor()
        matcher = HashSimilarityMatcher(title_extractor=extractor)

        # Underscore is kept because \w includes it
        assert matcher._normalize_title("Attack on Titan") == "attack on titan"
        assert matcher._normalize_title("Attack-on-Titan") == "attackontitan"
        assert matcher._normalize_title("Attack.on.Titan") == "attackontitan"
        assert matcher._normalize_title("Attack_on_Titan") == "attack_on_titan"

        # But dots and hyphens without spaces normalize the same
        normalized1 = matcher._normalize_title("Attack-on-Titan")
        normalized2 = matcher._normalize_title("Attack.on.Titan")
        assert normalized1 == normalized2 == "attackontitan"

    def test_group_empty_list(self) -> None:
        """Test grouping empty file list."""
        extractor = TitleExtractor()
        matcher = HashSimilarityMatcher(title_extractor=extractor)

        groups = matcher.match([])

        assert len(groups) == 0

    def test_group_single_file(self) -> None:
        """Test grouping single file."""
        extractor = TitleExtractor()
        matcher = HashSimilarityMatcher(title_extractor=extractor)

        files = [create_test_file("anime.mkv", "Anime Title")]

        groups = matcher.match(files)

        assert len(groups) == 1
        assert len(groups[0].files) == 1
        assert groups[0].title == "Anime Title"


class TestTitleExtraction:
    """Test title extraction from files."""

    def test_extract_from_metadata(self) -> None:
        """Test extraction prioritizes metadata title."""
        extractor = TitleExtractor()
        matcher = HashSimilarityMatcher(title_extractor=extractor)

        file = create_test_file("some_filename.mkv", "Correct Title")

        title = matcher._extract_title_from_file(file)

        assert title == "Correct Title"

    def test_extract_fallback_to_filename(self) -> None:
        """Test extraction falls back to filename when metadata missing."""
        extractor = TitleExtractor()
        matcher = HashSimilarityMatcher(title_extractor=extractor)

        # Create file without proper metadata title
        metadata = ParsingResult(title=Path("Attack_on_Titan_01.mkv").name)
        file = ScannedFile(
            file_path=Path("Attack_on_Titan_01.mkv"),
            metadata=metadata,
            file_size=1_000_000,
        )

        title = matcher._extract_title_from_file(file)

        # Should fall back to filename extraction
        assert title is not None
        assert len(title) > 0


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_very_long_title(self) -> None:
        """Test handling of extremely long titles."""
        extractor = TitleExtractor()
        matcher = HashSimilarityMatcher(title_extractor=extractor)

        long_title = "A" * (MAX_TITLE_LENGTH + 100)
        files = [create_test_file("anime.mkv", long_title)]

        groups = matcher.match(files)

        assert len(groups) == 1

    def test_unicode_titles(self) -> None:
        """Test handling of Unicode characters in titles."""
        extractor = TitleExtractor()
        matcher = HashSimilarityMatcher(title_extractor=extractor)

        files = [
            create_test_file("anime1.mkv", "進撃の巨人"),
            create_test_file("anime2.mkv", "進撃の巨人"),
        ]

        groups = matcher.match(files)

        assert len(groups) == 1
        assert len(groups[0].files) == 2

    def test_special_characters(self) -> None:
        """Test handling of special characters."""
        extractor = TitleExtractor()
        matcher = HashSimilarityMatcher(title_extractor=extractor)

        files = [
            create_test_file("anime1.mkv", "Title@#$%^&*()"),
            create_test_file("anime2.mkv", "Title!@#$%^&*()"),
        ]

        groups = matcher.match(files)

        # Both should normalize to "title"
        assert len(groups) == 1
        assert len(groups[0].files) == 2


class TestComponentInterface:
    """Test BaseMatcher protocol compliance."""

    def test_has_component_name(self) -> None:
        """Test matcher has component_name attribute."""
        extractor = TitleExtractor()
        matcher = HashSimilarityMatcher(title_extractor=extractor)

        assert hasattr(matcher, "component_name")
        assert matcher.component_name == "hash"

    def test_match_signature(self) -> None:
        """Test match method signature is correct."""
        extractor = TitleExtractor()
        matcher = HashSimilarityMatcher(title_extractor=extractor)

        # Should accept list[ScannedFile] and return list[Group]
        files = [create_test_file("anime.mkv", "Title")]
        result = matcher.match(files)

        assert isinstance(result, list)
        assert all(
            hasattr(group, "title") and hasattr(group, "files") for group in result
        )
