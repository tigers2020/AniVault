"""Unit tests for file_grouper data models."""

from __future__ import annotations

from pathlib import Path

from anivault.core.file_grouper.models import Group, GroupingEvidence
from anivault.core.models import ParsingResult, ScannedFile


def create_test_file(filename: str, episode: int | None = None) -> ScannedFile:
    """Helper to create ScannedFile."""
    return ScannedFile(
        file_path=Path(filename),
        metadata=ParsingResult(title="Test Anime", episode=episode),
    )


class TestGroupingEvidence:
    """Test GroupingEvidence dataclass."""

    def test_create_evidence(self) -> None:
        """Test creating evidence instance."""
        evidence = GroupingEvidence(
            match_scores={"title": 0.92, "hash": 0.85},
            selected_matcher="title",
            explanation="Grouped by title similarity (92%)",
            confidence=0.92,
        )

        assert evidence.match_scores == {"title": 0.92, "hash": 0.85}
        assert evidence.selected_matcher == "title"
        assert evidence.confidence == 0.92

    def test_to_dict(self) -> None:
        """Test converting evidence to dictionary."""
        evidence = GroupingEvidence(
            match_scores={"title": 0.92},
            selected_matcher="title",
            explanation="Title match",
            confidence=0.92,
        )

        result = evidence.to_dict()

        assert result["match_scores"] == {"title": 0.92}
        assert result["selected_matcher"] == "title"
        assert result["explanation"] == "Title match"
        assert result["confidence"] == 0.92


class TestGroup:
    """Test Group dataclass."""

    def test_create_group_basic(self) -> None:
        """Test creating basic group."""
        file = create_test_file("test.mkv")
        group = Group(title="Test Group", files=[file])

        assert group.title == "Test Group"
        assert len(group.files) == 1
        assert group.evidence is None

    def test_create_group_with_evidence(self) -> None:
        """Test creating group with evidence."""
        evidence = GroupingEvidence(
            match_scores={"title": 0.95},
            selected_matcher="title",
            explanation="High similarity",
            confidence=0.95,
        )
        group = Group(title="Test", files=[], evidence=evidence)

        assert group.evidence is evidence
        assert group.evidence.confidence == 0.95

    def test_add_file(self) -> None:
        """Test adding file to group."""
        group = Group(title="Test Group")
        file = create_test_file("test.mkv")

        assert len(group.files) == 0
        group.add_file(file)
        assert len(group.files) == 1
        assert file in group.files

    def test_add_multiple_files(self) -> None:
        """Test adding multiple files."""
        group = Group(title="Test")
        file1 = create_test_file("test1.mkv")
        file2 = create_test_file("test2.mkv")

        group.add_file(file1)
        group.add_file(file2)

        assert len(group.files) == 2

    def test_has_duplicates_single_file(self) -> None:
        """Test has_duplicates with single file."""
        file = create_test_file("test.mkv", episode=1)
        group = Group(title="Test", files=[file])

        assert not group.has_duplicates()

    def test_has_duplicates_no_episode_metadata(self) -> None:
        """Test has_duplicates with no episode metadata."""
        file1 = create_test_file("test1.mkv", episode=None)
        file2 = create_test_file("test2.mkv", episode=None)
        group = Group(title="Test", files=[file1, file2])

        # Without episode metadata, can't determine duplicates
        assert not group.has_duplicates()

    def test_has_duplicates_different_episodes(self) -> None:
        """Test has_duplicates with different episodes."""
        file1 = create_test_file("test1.mkv", episode=1)
        file2 = create_test_file("test2.mkv", episode=2)
        group = Group(title="Test", files=[file1, file2])

        assert not group.has_duplicates()

    def test_has_duplicates_same_episode(self) -> None:
        """Test has_duplicates with same episode."""
        file1 = create_test_file("test1_1080p.mkv", episode=1)
        file2 = create_test_file("test1_720p.mkv", episode=1)
        group = Group(title="Test", files=[file1, file2])

        assert group.has_duplicates()

    def test_has_duplicates_mixed_metadata(self) -> None:
        """Test has_duplicates with mixed metadata."""
        file1 = create_test_file("test1.mkv", episode=1)
        file2 = create_test_file("test2.mkv", episode=None)
        file3 = create_test_file("test3.mkv", episode=1)
        group = Group(title="Test", files=[file1, file2, file3])

        # Should detect duplicate episode 1
        assert group.has_duplicates()

    def test_to_dict(self) -> None:
        """Test converting group to dictionary."""
        file1 = create_test_file("test1.mkv")
        file2 = create_test_file("test2.mkv")
        group = Group(title="Test Group", files=[file1, file2])

        result = group.to_dict()

        assert result["title"] == "Test Group"
        assert result["file_count"] == 2
        assert len(result["files"]) == 2
        assert result["evidence"] is None

    def test_to_dict_with_evidence(self) -> None:
        """Test to_dict with evidence."""
        evidence = GroupingEvidence(
            match_scores={"title": 0.92},
            selected_matcher="title",
            explanation="Title match",
            confidence=0.92,
        )
        group = Group(title="Test", files=[], evidence=evidence)

        result = group.to_dict()

        assert result["evidence"] is not None
        assert result["evidence"]["confidence"] == 0.92

    def test_to_dict_empty_group(self) -> None:
        """Test to_dict with empty group."""
        group = Group(title="Empty")

        result = group.to_dict()

        assert result["title"] == "Empty"
        assert result["file_count"] == 0
        assert result["files"] == []
