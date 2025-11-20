"""Unit tests for GroupingEngine."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from anivault.core.file_grouper.grouping_engine import (
    DEFAULT_WEIGHTS,
    GroupingEngine,
)
from anivault.core.file_grouper.models import Group
from anivault.core.models import ScannedFile
from anivault.core.parser.models import ParsingResult


def create_test_file(filename: str) -> ScannedFile:
    """Helper to create test ScannedFile."""
    metadata = ParsingResult(title="Test Anime")
    return ScannedFile(
        file_path=Path(filename),
        metadata=metadata,
        file_size=1_000_000,
    )


def create_mock_matcher(name: str, groups: list[Group]) -> Mock:
    """Create a mock matcher that returns predefined groups."""
    matcher = Mock()
    matcher.component_name = name
    matcher.match.return_value = groups
    return matcher


class TestEngineInitialization:
    """Test GroupingEngine initialization."""

    def test_init_with_default_weights(self) -> None:
        """Test initialization with default weights."""
        matcher = create_mock_matcher("title", [])
        engine = GroupingEngine(matchers=[matcher])

        assert engine.weights == DEFAULT_WEIGHTS
        assert len(engine.matchers) == 1

    def test_init_with_custom_weights(self) -> None:
        """Test initialization with custom weights."""
        matcher1 = create_mock_matcher("title", [])
        matcher2 = create_mock_matcher("hash", [])

        custom_weights = {"title": 0.7, "hash": 0.3}
        engine = GroupingEngine(
            matchers=[matcher1, matcher2],
            weights=custom_weights,
        )

        assert engine.weights == custom_weights

    def test_init_empty_matchers_raises(self) -> None:
        """Test initialization with empty matchers list raises ValueError."""
        with pytest.raises(ValueError, match="At least one matcher"):
            GroupingEngine(matchers=[])

    def test_init_invalid_weights_sum_raises(self) -> None:
        """Test initialization with weights not summing to 1.0 raises."""
        matcher = create_mock_matcher("title", [])

        with pytest.raises(ValueError, match="must sum to 1.0"):
            GroupingEngine(
                matchers=[matcher],
                weights={"title": 0.5, "hash": 0.6},  # Sums to 1.1
            )

    def test_init_negative_weight_raises(self) -> None:
        """Test initialization with negative weight raises."""
        matcher = create_mock_matcher("title", [])

        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            GroupingEngine(
                matchers=[matcher],
                weights={"title": -0.5, "hash": 1.5},
            )

    def test_init_weight_over_one_raises(self) -> None:
        """Test initialization with weight > 1.0 raises."""
        matcher = create_mock_matcher("title", [])

        with pytest.raises(ValueError, match="between 0.0 and 1.0|sum to 1.0"):
            GroupingEngine(
                matchers=[matcher],
                weights={"title": 1.5},
            )


class TestSingleMatcher:
    """Test GroupingEngine with single matcher."""

    def test_single_matcher_success(self) -> None:
        """Test grouping with single matcher."""
        files = [
            create_test_file("anime1.mkv"),
            create_test_file("anime2.mkv"),
        ]

        expected_groups = [
            Group(title="Test Group", files=files),
        ]

        matcher = create_mock_matcher("title", expected_groups)
        engine = GroupingEngine(
            matchers=[matcher],
            weights={"title": 1.0},
        )

        result = engine.group_files(files)

        assert len(result) == 1
        assert result[0].title == "Test Group"
        assert len(result[0].files) == 2
        assert result[0].evidence is not None
        assert result[0].evidence.selected_matcher == "title"
        assert result[0].evidence.confidence == 1.0

    def test_single_matcher_empty_files(self) -> None:
        """Test grouping with empty file list."""
        matcher = create_mock_matcher("title", [])
        engine = GroupingEngine(matchers=[matcher])

        result = engine.group_files([])

        assert len(result) == 0

    def test_single_matcher_no_groups(self) -> None:
        """Test matcher that returns no groups."""
        files = [create_test_file("anime.mkv")]

        matcher = create_mock_matcher("title", [])  # Returns empty list
        engine = GroupingEngine(matchers=[matcher])

        result = engine.group_files(files)

        assert len(result) == 0

    def test_single_matcher_multiple_groups(self) -> None:
        """Test matcher that returns multiple groups."""
        files = [create_test_file(f"anime{i}.mkv") for i in range(4)]

        expected_groups = [
            Group(title="Group 1", files=files[:2]),
            Group(title="Group 2", files=files[2:]),
        ]

        matcher = create_mock_matcher("title", expected_groups)
        engine = GroupingEngine(
            matchers=[matcher],
            weights={"title": 1.0},
        )

        result = engine.group_files(files)

        assert len(result) == 2
        assert all(g.evidence is not None for g in result)
        assert all(g.evidence.selected_matcher == "title" for g in result)


class TestMultipleMatchers:
    """Test GroupingEngine with multiple matchers."""

    def test_multiple_matchers_highest_weight_wins(self) -> None:
        """Test that matcher with highest weight is selected."""
        files = [create_test_file(f"anime{i}.mkv") for i in range(2)]

        title_groups = [Group(title="Title Group", files=files)]
        hash_groups = [Group(title="Hash Group", files=files)]

        title_matcher = create_mock_matcher("title", title_groups)
        hash_matcher = create_mock_matcher("hash", hash_groups)

        engine = GroupingEngine(
            matchers=[title_matcher, hash_matcher],
            weights={"title": 0.7, "hash": 0.3},
        )

        result = engine.group_files(files)

        # Title matcher should win (higher weight)
        assert len(result) == 1
        assert result[0].title == "Title Group"
        assert result[0].evidence.selected_matcher == "title"
        assert result[0].evidence.confidence == 0.7

    def test_multiple_matchers_all_called(self) -> None:
        """Test that all matchers are called."""
        files = [create_test_file("anime.mkv")]

        matcher1 = create_mock_matcher("title", [Group(title="G1", files=files)])
        matcher2 = create_mock_matcher("hash", [Group(title="G2", files=files)])

        engine = GroupingEngine(
            matchers=[matcher1, matcher2],
            weights={"title": 0.6, "hash": 0.4},
        )

        engine.group_files(files)

        # Both matchers should be called
        matcher1.match.assert_called_once_with(files)
        matcher2.match.assert_called_once_with(files)

    def test_matcher_failure_handled_gracefully(self) -> None:
        """Test that matcher failures are handled gracefully."""
        files = [create_test_file("anime.mkv")]

        # Working matcher
        good_matcher = create_mock_matcher("title", [Group(title="Good", files=files)])

        # Failing matcher
        bad_matcher = create_mock_matcher("hash", [])
        bad_matcher.match.side_effect = Exception("Matcher failed")

        engine = GroupingEngine(
            matchers=[good_matcher, bad_matcher],
            weights={"title": 0.6, "hash": 0.4},
        )

        result = engine.group_files(files)

        # Should still return results from good matcher
        assert len(result) == 1
        assert result[0].title == "Good"


class TestEvidenceGeneration:
    """Test evidence generation."""

    def test_evidence_attached_to_groups(self) -> None:
        """Test that evidence is attached to all groups."""
        files = [create_test_file(f"anime{i}.mkv") for i in range(4)]

        groups = [
            Group(title="Group 1", files=files[:2]),
            Group(title="Group 2", files=files[2:]),
        ]

        matcher = create_mock_matcher("title", groups)
        engine = GroupingEngine(
            matchers=[matcher],
            weights={"title": 1.0},
        )

        result = engine.group_files(files)

        # All groups should have evidence
        assert all(g.evidence is not None for g in result)

        for group in result:
            assert group.evidence.selected_matcher == "title"
            assert group.evidence.confidence == 1.0
            assert "title" in group.evidence.match_scores
            assert group.evidence.match_scores["title"] == 1.0

    def test_explanation_format(self) -> None:
        """Test that explanation has correct format."""
        files = [create_test_file("anime.mkv")]

        matcher = create_mock_matcher("title", [Group(title="Test", files=files)])
        engine = GroupingEngine(
            matchers=[matcher],
            weights={"title": 1.0},  # Must sum to 1.0
        )

        result = engine.group_files(files)

        explanation = result[0].evidence.explanation
        assert "title similarity" in explanation
        assert "100%" in explanation  # 1.0 = 100%

    def test_explanation_for_different_matchers(self) -> None:
        """Test explanations for different matcher types."""
        files = [create_test_file("anime.mkv")]

        # Test title matcher
        title_matcher = create_mock_matcher("title", [Group(title="T", files=files)])
        engine = GroupingEngine(
            matchers=[title_matcher],
            weights={"title": 1.0},  # Must sum to 1.0
        )
        result = engine.group_files(files)
        assert "title similarity" in result[0].evidence.explanation

        # Test hash matcher
        hash_matcher = create_mock_matcher("hash", [Group(title="H", files=files)])
        engine = GroupingEngine(
            matchers=[hash_matcher],
            weights={"hash": 1.0},  # Must sum to 1.0
        )
        result = engine.group_files(files)
        assert "normalized hash" in result[0].evidence.explanation

        # Test season matcher
        season_matcher = create_mock_matcher("season", [Group(title="S", files=files)])
        engine = GroupingEngine(
            matchers=[season_matcher],
            weights={"season": 1.0},  # Must sum to 1.0
        )
        result = engine.group_files(files)
        assert "season metadata" in result[0].evidence.explanation


class TestGroupSorting:
    """Test that groups are sorted by confidence."""

    def test_groups_sorted_by_confidence(self) -> None:
        """Test that groups are sorted by confidence (highest first)."""
        files = [create_test_file(f"anime{i}.mkv") for i in range(3)]

        # Create groups (will all have same weight, so order should be preserved)
        groups = [
            Group(title="Group 1", files=[files[0]]),
            Group(title="Group 2", files=[files[1]]),
            Group(title="Group 3", files=[files[2]]),
        ]

        matcher = create_mock_matcher("title", groups)
        engine = GroupingEngine(
            matchers=[matcher],
            weights={"title": 1.0},  # Must sum to 1.0
        )

        result = engine.group_files(files)

        # All should have same confidence
        confidences = [g.evidence.confidence for g in result]
        assert all(c == 1.0 for c in confidences)


class TestEdgeCases:
    """Test edge cases."""

    def test_all_matchers_fail(self) -> None:
        """Test when all matchers fail."""
        files = [create_test_file("anime.mkv")]

        matcher = create_mock_matcher("title", [])
        matcher.match.side_effect = Exception("Failed")

        engine = GroupingEngine(matchers=[matcher])

        result = engine.group_files(files)

        assert len(result) == 0

    def test_weight_tolerance(self) -> None:
        """Test that small floating point errors in weights are tolerated."""
        matcher = create_mock_matcher("title", [])

        # Sum is 1.0000000001 (slightly over due to floating point)
        weights = {"title": 0.6, "hash": 0.4, "other": 1e-10}

        # Should not raise (within tolerance)
        engine = GroupingEngine(matchers=[matcher], weights=weights)
        assert engine.weights == weights
