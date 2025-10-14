"""Unit tests for file grouper models."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from anivault.core.file_grouper.models import Group, GroupingEvidence
from anivault.core.models import ScannedFile

if TYPE_CHECKING:
    from anivault.core.parser.models import ParsingResult


@pytest.fixture
def sample_evidence() -> GroupingEvidence:
    """Create a sample GroupingEvidence for testing."""
    return GroupingEvidence(
        match_scores={"title": 0.92, "hash": 0.85, "season": 0.0},
        selected_matcher="title",
        explanation="Grouped by title similarity (92%)",
        confidence=0.92,
    )


@pytest.fixture
def sample_scanned_files() -> list[ScannedFile]:
    """Create sample ScannedFile objects for testing."""
    from anivault.core.parser.models import ParsingResult

    return [
        ScannedFile(
            file_path=Path("/test/aot_01.mkv"),
            metadata=ParsingResult(
                title="Attack on Titan",
                episode=1,
                quality="1080p",
            ),
            file_size=500 * 1024 * 1024,  # 500 MB in bytes
        ),
        ScannedFile(
            file_path=Path("/test/aot_02.mkv"),
            metadata=ParsingResult(
                title="Attack on Titan",
                episode=2,
                quality="1080p",
            ),
            file_size=480 * 1024 * 1024,  # 480 MB in bytes
        ),
    ]


class TestGroupingEvidence:
    """Test cases for GroupingEvidence dataclass."""

    def test_instantiation(self, sample_evidence: GroupingEvidence) -> None:
        """Test GroupingEvidence can be instantiated with valid data."""
        assert sample_evidence.match_scores["title"] == 0.92
        assert sample_evidence.selected_matcher == "title"
        assert sample_evidence.explanation == "Grouped by title similarity (92%)"
        assert sample_evidence.confidence == 0.92

    def test_to_dict(self, sample_evidence: GroupingEvidence) -> None:
        """Test evidence can be converted to dictionary."""
        result = sample_evidence.to_dict()

        assert isinstance(result, dict)
        assert result["match_scores"] == {"title": 0.92, "hash": 0.85, "season": 0.0}
        assert result["selected_matcher"] == "title"
        assert result["explanation"] == "Grouped by title similarity (92%)"
        assert result["confidence"] == 0.92

    def test_multiple_matcher_scores(self) -> None:
        """Test evidence can track scores from multiple matchers."""
        evidence = GroupingEvidence(
            match_scores={"title": 0.95, "hash": 0.88, "season": 0.75},
            selected_matcher="title",
            explanation="Multi-matcher grouping",
            confidence=0.95,
        )

        assert len(evidence.match_scores) == 3
        assert evidence.match_scores["title"] == 0.95
        assert evidence.match_scores["hash"] == 0.88
        assert evidence.match_scores["season"] == 0.75

    def test_confidence_range(self) -> None:
        """Test evidence accepts confidence values in 0.0-1.0 range."""
        # Minimum confidence
        low_conf = GroupingEvidence(
            match_scores={"title": 0.0},
            selected_matcher="title",
            explanation="Low confidence",
            confidence=0.0,
        )
        assert low_conf.confidence == 0.0

        # Maximum confidence
        high_conf = GroupingEvidence(
            match_scores={"title": 1.0},
            selected_matcher="title",
            explanation="Perfect match",
            confidence=1.0,
        )
        assert high_conf.confidence == 1.0


class TestGroup:
    """Test cases for Group dataclass."""

    def test_instantiation_empty(self) -> None:
        """Test Group can be instantiated with just a title."""
        group = Group(title="Test Group")

        assert group.title == "Test Group"
        assert group.files == []
        assert group.evidence is None

    def test_instantiation_with_files(
        self, sample_scanned_files: list[ScannedFile]
    ) -> None:
        """Test Group can be instantiated with files."""
        group = Group(title="Attack on Titan", files=sample_scanned_files)

        assert group.title == "Attack on Titan"
        assert len(group.files) == 2
        assert group.files[0].file_path.name == "aot_01.mkv"

    def test_instantiation_with_evidence(
        self,
        sample_scanned_files: list[ScannedFile],
        sample_evidence: GroupingEvidence,
    ) -> None:
        """Test Group can be instantiated with evidence."""
        group = Group(
            title="Test",
            files=sample_scanned_files,
            evidence=sample_evidence,
        )

        assert group.evidence is not None
        assert group.evidence.confidence == 0.92
        assert group.evidence.selected_matcher == "title"

    def test_add_file(self, sample_scanned_files: list[ScannedFile]) -> None:
        """Test adding files to a group."""
        group = Group(title="Test")
        assert len(group.files) == 0

        group.add_file(sample_scanned_files[0])
        assert len(group.files) == 1
        assert group.files[0].file_path.name == "aot_01.mkv"

        group.add_file(sample_scanned_files[1])
        assert len(group.files) == 2

    def test_has_duplicates_false_single_file(
        self, sample_scanned_files: list[ScannedFile]
    ) -> None:
        """Test has_duplicates returns False for single file."""
        group = Group(title="Test", files=[sample_scanned_files[0]])
        assert group.has_duplicates() is False

    def test_has_duplicates_false_no_files(self) -> None:
        """Test has_duplicates returns False for empty group."""
        group = Group(title="Test")
        assert group.has_duplicates() is False

    def test_has_duplicates_no_metadata(
        self, sample_scanned_files: list[ScannedFile]
    ) -> None:
        """Test has_duplicates returns False when no episode metadata."""
        group = Group(title="Test", files=sample_scanned_files)
        # Files don't have episode metadata, so can't detect duplicates
        assert group.has_duplicates() is False

    def test_to_dict_empty(self) -> None:
        """Test converting empty group to dictionary."""
        group = Group(title="Test Group")
        result = group.to_dict()

        assert isinstance(result, dict)
        assert result["title"] == "Test Group"
        assert result["file_count"] == 0
        assert result["files"] == []
        assert result["evidence"] is None

    def test_to_dict_with_files(self, sample_scanned_files: list[ScannedFile]) -> None:
        """Test converting group with files to dictionary."""
        group = Group(title="Test", files=sample_scanned_files)
        result = group.to_dict()

        assert result["title"] == "Test"
        assert result["file_count"] == 2
        assert len(result["files"]) == 2
        assert "aot_01.mkv" in result["files"][0]

    def test_to_dict_with_evidence(
        self,
        sample_scanned_files: list[ScannedFile],
        sample_evidence: GroupingEvidence,
    ) -> None:
        """Test converting group with evidence to dictionary."""
        group = Group(
            title="Test",
            files=sample_scanned_files,
            evidence=sample_evidence,
        )
        result = group.to_dict()

        assert result["evidence"] is not None
        assert isinstance(result["evidence"], dict)
        assert result["evidence"]["confidence"] == 0.92
        assert result["evidence"]["selected_matcher"] == "title"

    def test_to_dict_serialization(
        self,
        sample_scanned_files: list[ScannedFile],
        sample_evidence: GroupingEvidence,
    ) -> None:
        """Test full serialization for logging."""
        group = Group(
            title="Attack on Titan",
            files=sample_scanned_files,
            evidence=sample_evidence,
        )
        result = group.to_dict()

        # Verify all fields are JSON-serializable types
        assert isinstance(result["title"], str)
        assert isinstance(result["file_count"], int)
        assert isinstance(result["files"], list)
        assert all(isinstance(f, str) for f in result["files"])
        assert isinstance(result["evidence"], dict)
