"""Subtitle-only benchmark scenario generator.

This module generates subtitle-only test data for performance benchmarking.
Creates subtitle files in scenario-specific directories.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import NamedTuple

from benchmarks.benchmark_scenarios import generate_dummy_subtitle_file


class SubtitleScenarioConfig(NamedTuple):
    """Configuration for a subtitle-only benchmark scenario."""

    num_subtitles: int
    scenario_name: str


def generate_subtitle_only_scenario(
    base_dir: Path,
    num_subtitles: int,
    scenario_name: str,
    seed: int | None = None,
) -> Path:
    """Generate subtitle-only test data for a benchmark scenario.

    Args:
        base_dir: Base directory for test data
        num_subtitles: Number of subtitle files to generate
        scenario_name: Name of the scenario (used for directory name)
        seed: Random seed for reproducibility

    Returns:
        Path to the scenario directory

    Example:
        >>> scenario_dir = generate_subtitle_only_scenario(
        ...     Path("benchmarks/test_data"),
        ...     num_subtitles=100,
        ...     scenario_name="100_subs_only"
        ... )
        >>> scenario_dir.exists()
        True
    """
    if seed is not None:
        random.seed(seed)

    # Create scenario directory
    scenario_dir = base_dir / scenario_name
    scenario_dir.mkdir(parents=True, exist_ok=True)

    # Base anime titles for variety
    base_titles = [
        "Attack on Titan",
        "Demon Slayer",
        "My Hero Academia",
        "One Piece",
        "Naruto Shippuden",
        "Sword Art Online",
        "Fullmetal Alchemist Brotherhood",
        "Death Note",
        "Tokyo Ghoul",
        "Hunter x Hunter",
    ]

    # Generate subtitle files only
    for i in range(num_subtitles):
        # Select series (cycle through titles)
        series_name = base_titles[i % len(base_titles)]
        episode = (i % 24) + 1
        season = (i // 24) + 1

        # Generate dummy subtitle file
        generate_dummy_subtitle_file(
            output_path=scenario_dir / f"temp_{i}.smi",
            series_name=series_name,
            season=season,
            episode=episode,
        )

    return scenario_dir


def generate_all_subtitle_scenarios(base_dir: Path | None = None) -> dict[str, Path]:
    """Generate all subtitle-only benchmark scenarios.

    Args:
        base_dir: Base directory for test data. Defaults to benchmarks/test_data

    Returns:
        Dictionary mapping scenario names to their directory paths

    Example:
        >>> scenarios = generate_all_subtitle_scenarios()
        >>> "10_subs_only" in scenarios
        True
    """
    if base_dir is None:
        base_dir = Path(__file__).parent / "test_data"

    # Define subtitle-only scenarios: (num_subtitles, scenario_name)
    scenarios = [
        SubtitleScenarioConfig(10, "10_subs_only"),
        SubtitleScenarioConfig(100, "100_subs_only"),
        SubtitleScenarioConfig(1000, "1000_subs_only"),
    ]

    generated_scenarios: dict[str, Path] = {}

    for scenario in scenarios:
        print(f"Generating subtitle scenario: {scenario.scenario_name}...")
        scenario_dir = generate_subtitle_only_scenario(
            base_dir=base_dir,
            num_subtitles=scenario.num_subtitles,
            scenario_name=scenario.scenario_name,
            seed=42,  # Fixed seed for reproducibility
        )
        generated_scenarios[scenario.scenario_name] = scenario_dir
        print(f"  ✓ Created {scenario.num_subtitles} subtitle files")

    return generated_scenarios


if __name__ == "__main__":
    """Generate all subtitle-only scenarios when run directly."""
    print("Generating subtitle-only benchmark test data scenarios...\n")

    scenarios = generate_all_subtitle_scenarios()

    print(f"\n✓ Generated {len(scenarios)} subtitle-only scenarios:")
    for name, path in scenarios.items():
        sub_count = len(list(path.glob("*.smi"))) + len(list(path.glob("*.srt"))) + len(list(path.glob("*.ass")))
        print(f"  - {name}: {sub_count} subtitles")

