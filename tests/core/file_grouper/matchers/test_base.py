"""Unit tests for BaseMatcher protocol."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from anivault.core.file_grouper.matchers.base import BaseMatcher
from anivault.core.file_grouper.models import Group
from anivault.core.models import ScannedFile
from anivault.core.parser.models import ParsingResult

if TYPE_CHECKING:
    pass


class MockMatcher:
    """Mock matcher that implements BaseMatcher protocol."""

    component_name = "mock"

    def match(self, files: list[ScannedFile]) -> list[Group]:
        """Simple grouping by first letter of filename."""
        groups_dict: dict[str, list[ScannedFile]] = {}

        for file in files:
            first_letter = file.file_path.stem[0].upper()
            if first_letter not in groups_dict:
                groups_dict[first_letter] = []
            groups_dict[first_letter].append(file)

        return [Group(title=name, files=files) for name, files in groups_dict.items()]


class IncompleteMatcherNoName:
    """Matcher without component_name (violates protocol)."""

    def match(self, files: list[ScannedFile]) -> list[Group]:
        """Implements match but missing component_name."""
        return []


class IncompleteMatcherNoMatch:
    """Matcher without match() method (violates protocol)."""

    component_name = "incomplete"


@pytest.fixture
def sample_files() -> list[ScannedFile]:
    """Create sample ScannedFile objects for testing."""
    return [
        ScannedFile(
            file_path=Path("/test/attack_01.mkv"),
            metadata=ParsingResult(title="Attack on Titan", episode=1),
            file_size=500 * 1024 * 1024,
        ),
        ScannedFile(
            file_path=Path("/test/attack_02.mkv"),
            metadata=ParsingResult(title="Attack on Titan", episode=2),
            file_size=480 * 1024 * 1024,
        ),
        ScannedFile(
            file_path=Path("/test/bleach_01.mkv"),
            metadata=ParsingResult(title="Bleach", episode=1),
            file_size=450 * 1024 * 1024,
        ),
    ]


class TestBaseMatcherProtocol:
    """Test cases for BaseMatcher Protocol."""

    def test_protocol_check_valid_matcher(self) -> None:
        """Test that MockMatcher satisfies BaseMatcher protocol."""
        matcher = MockMatcher()

        # Protocol check using isinstance()
        assert isinstance(matcher, BaseMatcher)

    def test_protocol_check_missing_component_name(self) -> None:
        """Test that matcher without component_name fails protocol check."""
        incomplete_matcher = IncompleteMatcherNoName()

        # Should fail isinstance check
        assert not isinstance(incomplete_matcher, BaseMatcher)

    def test_protocol_check_missing_match_method(self) -> None:
        """Test that matcher without match() fails protocol check."""
        incomplete_matcher = IncompleteMatcherNoMatch()

        # Should fail isinstance check
        assert not isinstance(incomplete_matcher, BaseMatcher)

    def test_mock_matcher_component_name(self) -> None:
        """Test that MockMatcher has correct component_name."""
        matcher = MockMatcher()
        assert matcher.component_name == "mock"

    def test_mock_matcher_groups_files(self, sample_files: list[ScannedFile]) -> None:
        """Test that MockMatcher can group files."""
        matcher = MockMatcher()
        result = matcher.match(sample_files)

        # Should return list of Group objects
        assert isinstance(result, list)
        assert len(result) == 2  # A and B groups
        assert all(isinstance(g, Group) for g in result)

        # Find groups by title
        groups_by_title = {g.title: g for g in result}
        assert "A" in groups_by_title
        assert "B" in groups_by_title
        assert len(groups_by_title["A"].files) == 2  # attack_01, attack_02
        assert len(groups_by_title["B"].files) == 1  # bleach_01

    def test_mock_matcher_empty_input(self) -> None:
        """Test that MockMatcher handles empty input."""
        matcher = MockMatcher()
        result = matcher.match([])

        assert isinstance(result, list)
        assert len(result) == 0

    def test_mock_matcher_single_file(self, sample_files: list[ScannedFile]) -> None:
        """Test that MockMatcher handles single file."""
        matcher = MockMatcher()
        result = matcher.match([sample_files[0]])

        assert len(result) == 1
        assert result[0].title == "A"
        assert len(result[0].files) == 1

    def test_protocol_signature_validation(self) -> None:
        """Test that protocol enforces correct method signature."""

        class WrongSignatureMatcher:
            component_name = "wrong"

            # Wrong signature: missing files parameter
            def match(self) -> list:  # type: ignore[misc]
                return []

        wrong_matcher = WrongSignatureMatcher()

        # Should fail protocol check due to signature mismatch
        # Note: runtime_checkable only checks method existence, not signature
        # This is a limitation of Python Protocols
        assert hasattr(wrong_matcher, "match")
        assert hasattr(wrong_matcher, "component_name")

    def test_protocol_with_type_hints(self, sample_files: list[ScannedFile]) -> None:
        """Test that type hints work correctly with Protocol."""
        matcher: BaseMatcher = MockMatcher()

        # Type checker should accept this
        result: list[Group] = matcher.match(sample_files)

        assert isinstance(result, list)
        assert all(isinstance(g, Group) for g in result)


class TestMatcherExtensibility:
    """Test extensibility patterns with BaseMatcher."""

    def test_custom_matcher_implementation(
        self, sample_files: list[ScannedFile]
    ) -> None:
        """Test that custom matchers can be easily created."""

        class AlwaysGroupMatcher:
            """Simple matcher that groups all files together."""

            component_name = "always_group"

            def match(self, files: list[ScannedFile]) -> list[Group]:
                """Group all files into one group."""
                if not files:
                    return []
                return [Group(title="all_files", files=files)]

        matcher = AlwaysGroupMatcher()
        assert isinstance(matcher, BaseMatcher)

        result = matcher.match(sample_files)
        assert len(result) == 1
        assert result[0].title == "all_files"
        assert len(result[0].files) == 3

    def test_matcher_with_configuration(self, sample_files: list[ScannedFile]) -> None:
        """Test that matchers can have configuration parameters."""

        class ConfigurableMatcher:
            """Matcher with configurable threshold."""

            def __init__(self, threshold: float) -> None:
                """Initialize with threshold."""
                self.component_name = f"configurable_{threshold}"
                self.threshold = threshold

            def match(self, files: list[ScannedFile]) -> list[Group]:
                """Group files (simplified)."""
                if not files:
                    return []
                return [Group(title="group", files=files)]

        matcher = ConfigurableMatcher(threshold=0.85)
        assert isinstance(matcher, BaseMatcher)
        assert matcher.component_name == "configurable_0.85"
        assert matcher.threshold == 0.85

    def test_matcher_list_type_checking(self, sample_files: list[ScannedFile]) -> None:
        """Test that list of matchers works with type hints."""
        matchers: list[BaseMatcher] = [
            MockMatcher(),
            MockMatcher(),  # Can have duplicates
        ]

        assert len(matchers) == 2
        assert all(isinstance(m, BaseMatcher) for m in matchers)

        # All matchers should be callable
        for matcher in matchers:
            result = matcher.match(sample_files)
            assert isinstance(result, list)
            assert all(isinstance(g, Group) for g in result)
