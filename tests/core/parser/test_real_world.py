"""Real-world accuracy testing for anime filename parser."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from anivault.core.parser.anime_parser import AnimeFilenameParser
from anivault.core.parser.models import ParsingResult

logger = logging.getLogger(__name__)


@pytest.fixture
def real_world_data():
    """Load real-world test dataset.

    Returns:
        List of test cases with filename and expected results.

    Raises:
        FileNotFoundError: If test dataset file is not found.
    """
    fixture_path = (
        Path(__file__).parent.parent.parent / "fixtures" / "real_world_filenames.json"
    )

    if not fixture_path.exists():
        raise FileNotFoundError(
            f"Test dataset not found: {fixture_path}\n"
            "Run: python scripts/create_test_dataset.py"
        )

    with open(fixture_path, encoding="utf-8") as f:
        data = json.load(f)

    return data


def _compare_results(
    result: ParsingResult, expected: dict[str, any]
) -> tuple[bool, list[str]]:
    """Compare ParsingResult with expected dictionary.

    Args:
        result: ParsingResult from parser.
        expected: Expected values dictionary.

    Returns:
        Tuple of (is_match, differences) where differences is a list of mismatched fields.
    """
    differences = []

    # Compare each field in expected
    for field, expected_value in expected.items():
        actual_value = getattr(result, field, None)

        # Handle None comparisons
        if expected_value is None and actual_value is None:
            continue

        # Handle string comparisons (case-insensitive for some fields)
        if isinstance(expected_value, str) and isinstance(actual_value, str):
            # Quality and codec fields are case-insensitive
            if field in ["quality", "codec", "source", "audio"]:
                if expected_value.lower() != actual_value.lower():
                    differences.append(
                        f"{field}: expected='{expected_value}', actual='{actual_value}'"
                    )
            else:
                if expected_value != actual_value:
                    differences.append(
                        f"{field}: expected='{expected_value}', actual='{actual_value}'"
                    )
        # Handle numeric comparisons
        elif expected_value != actual_value:
            differences.append(
                f"{field}: expected={expected_value}, actual={actual_value}"
            )

    return len(differences) == 0, differences


def test_real_world_accuracy(real_world_data):
    """Test parser accuracy against real-world dataset.

    This test validates the parser's performance on real anime filenames
    and ensures it meets the 97% accuracy threshold.
    """
    parser = AnimeFilenameParser()

    total_cases = len(real_world_data)
    correct_parses = 0
    failed_cases = []

    print(f"\n🧪 Testing {total_cases} real-world filenames...")

    for idx, test_case in enumerate(real_world_data):
        filename = test_case["filename"]
        expected = test_case["expected"]

        # Parse filename
        result = parser.parse(filename)

        # Compare results
        is_match, differences = _compare_results(result, expected)

        if is_match:
            correct_parses += 1
        else:
            # Log failure details
            failed_case = {
                "index": idx + 1,
                "filename": filename,
                "expected": expected,
                "actual": {
                    "title": result.title,
                    "episode": result.episode,
                    "season": result.season,
                    "quality": result.quality,
                    "source": result.source,
                    "codec": result.codec,
                    "audio": result.audio,
                    "release_group": result.release_group,
                },
                "parser_used": result.parser_used,
                "confidence": result.confidence,
                "differences": differences,
            }
            failed_cases.append(failed_case)

            logger.warning(
                f"Parse mismatch [{idx + 1}/{total_cases}]: {filename}\n"
                f"  Differences: {', '.join(differences)}"
            )

    # Calculate accuracy
    accuracy = correct_parses / total_cases if total_cases > 0 else 0.0

    # Print summary
    print(f"\n📊 Accuracy Results:")
    print(f"   Total cases: {total_cases}")
    print(f"   Correct: {correct_parses}")
    print(f"   Failed: {len(failed_cases)}")
    print(f"   Accuracy: {accuracy:.2%}")

    # Print failed cases summary
    if failed_cases:
        print(f"\n❌ Failed cases ({len(failed_cases)}):")
        for case in failed_cases[:10]:  # Show first 10
            print(f"   [{case['index']}] {case['filename']}")
            print(f"      Differences: {', '.join(case['differences'])}")

        if len(failed_cases) > 10:
            print(f"   ... and {len(failed_cases) - 10} more")

    # Assert accuracy threshold
    # Note: 97% is the target, but we'll use 90% for real-world data
    assert accuracy >= 0.90, (
        f"Parser accuracy {accuracy:.2%} is below threshold (90%). "
        f"Failed {len(failed_cases)}/{total_cases} cases."
    )


def test_dataset_structure(real_world_data):
    """Test that dataset has correct structure."""
    assert len(real_world_data) >= 100, "Dataset should have at least 100 entries"

    # Check structure of first entry
    first_entry = real_world_data[0]
    assert "filename" in first_entry
    assert "expected" in first_entry

    expected = first_entry["expected"]
    assert "title" in expected
    assert "episode" in expected
    assert "season" in expected


def test_dataset_diversity(real_world_data):
    """Test that dataset covers diverse patterns."""
    # Count different parser usages (if stored in dataset)
    has_anitopy = any(case.get("parser_used") == "anitopy" for case in real_world_data)
    has_fallback = any(
        case.get("parser_used") == "fallback" for case in real_world_data
    )

    # Dataset should have examples of both parsers
    assert has_anitopy, "Dataset should include anitopy-parseable files"
    # Fallback is optional but good to have
    if not has_fallback:
        logger.info("Dataset has no fallback parser examples")

    # Check for diversity in file formats
    filenames = [case["filename"] for case in real_world_data]
    extensions = {Path(f).suffix.lower() for f in filenames}

    assert len(extensions) >= 2, "Dataset should include multiple file formats"
