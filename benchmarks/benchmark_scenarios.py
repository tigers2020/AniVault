"""Benchmark scenario test data generator.

This module generates dummy video and subtitle files for performance benchmarking.
Creates files in scenario-specific directories for different test cases.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import NamedTuple


class ScenarioConfig(NamedTuple):
    """Configuration for a benchmark scenario."""

    num_files: int
    num_subtitles: int
    scenario_name: str


def generate_dummy_video_file(
    output_path: Path,
    series_name: str,
    season: int,
    episode: int,
) -> None:
    """Generate a dummy video file.

    Args:
        output_path: Path where the file should be created
        series_name: Name of the series
        season: Season number
        episode: Episode number
    """
    # Create parent directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate filename in common anime naming format
    filename_parts = [
        series_name.replace(" ", "."),
        f"S{season:02d}E{episode:02d}",
    ]

    # Add quality and release group randomly
    if episode % 2 == 0:
        filename_parts.append("1080p")
    if episode % 3 == 0:
        filename_parts.append("BDRip")
    if episode % 4 == 0:
        filename_parts.append("SubsPlease")

    extensions = [".mkv", ".mp4", ".avi"]
    extension = extensions[episode % len(extensions)]
    filename = ".".join(filename_parts) + extension

    file_path = output_path.parent / filename

    # Write dummy content (small file for speed)
    # In real scenario, these would be large video files
    file_path.write_bytes(b"dummy video content" * 100)


def generate_dummy_subtitle_file(
    output_path: Path,
    series_name: str,
    season: int,
    episode: int,
) -> None:
    """Generate a dummy subtitle file.

    Args:
        output_path: Path where the file should be created
        series_name: Name of the series
        season: Season number
        episode: Episode number
    """
    # Create parent directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate filename matching video file
    filename_parts = [
        series_name.replace(" ", "."),
        f"S{season:02d}E{episode:02d}",
    ]

    # Subtitle extensions
    extensions = [".smi", ".srt", ".ass"]
    extension = extensions[episode % len(extensions)]
    filename = ".".join(filename_parts) + extension

    file_path = output_path.parent / filename

    # Write dummy subtitle content
    subtitle_content = f"[SUBTITLE]\n{series_name} S{season:02d}E{episode:02d}\n"
    file_path.write_text(subtitle_content, encoding="utf-8")


def generate_scenario_data(
    base_dir: Path,
    num_files: int,
    num_subtitles: int,
    scenario_name: str,
    seed: int | None = None,
) -> Path:
    """Generate test data for a benchmark scenario.

    Args:
        base_dir: Base directory for test data
        num_files: Number of video files to generate
        num_subtitles: Number of subtitle files to generate
        scenario_name: Name of the scenario (used for directory name)
        seed: Random seed for reproducibility

    Returns:
        Path to the scenario directory

    Example:
        >>> scenario_dir = generate_scenario_data(
        ...     Path("benchmarks/test_data"),
        ...     num_files=100,
        ...     num_subtitles=10,
        ...     scenario_name="100_files_10_subs"
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

    # Generate video files
    for i in range(num_files):
        # Select series (cycle through titles)
        series_name = base_titles[i % len(base_titles)]
        episode = (i % 24) + 1
        season = (i // 24) + 1

        # Generate dummy video file
        generate_dummy_video_file(
            output_path=scenario_dir / f"temp_{i}.mkv",
            series_name=series_name,
            season=season,
            episode=episode,
        )

    # Generate subtitle files
    for i in range(num_subtitles):
        # Match subtitles to first num_subtitles video files
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


def generate_all_scenarios(base_dir: Path | None = None) -> dict[str, Path]:
    """Generate all benchmark scenarios.

    Args:
        base_dir: Base directory for test data. Defaults to benchmarks/test_data

    Returns:
        Dictionary mapping scenario names to their directory paths

    Example:
        >>> scenarios = generate_all_scenarios()
        >>> "100_files_10_subs" in scenarios
        True
    """
    if base_dir is None:
        base_dir = Path(__file__).parent / "test_data"

    # Define all scenarios: (num_files, num_subtitles, scenario_name)
    scenarios = [
        ScenarioConfig(100, 10, "100_files_10_subs"),
        ScenarioConfig(100, 100, "100_files_100_subs"),
        ScenarioConfig(100, 1000, "100_files_1000_subs"),
        ScenarioConfig(1000, 10, "1000_files_10_subs"),
        ScenarioConfig(1000, 100, "1000_files_100_subs"),
        ScenarioConfig(1000, 1000, "1000_files_1000_subs"),
        ScenarioConfig(10000, 10, "10000_files_10_subs"),
        ScenarioConfig(10000, 100, "10000_files_100_subs"),
        ScenarioConfig(10000, 1000, "10000_files_1000_subs"),
    ]

    generated_scenarios: dict[str, Path] = {}

    for scenario in scenarios:
        print(f"Generating scenario: {scenario.scenario_name}...")
        scenario_dir = generate_scenario_data(
            base_dir=base_dir,
            num_files=scenario.num_files,
            num_subtitles=scenario.num_subtitles,
            scenario_name=scenario.scenario_name,
            seed=42,  # Fixed seed for reproducibility
        )
        generated_scenarios[scenario.scenario_name] = scenario_dir
        print(f"  ✓ Created {scenario.num_files} files and {scenario.num_subtitles} subtitles")

    return generated_scenarios


if __name__ == "__main__":
    """Generate all benchmark scenarios when run directly."""
    print("Generating benchmark test data scenarios...\n")

    scenarios = generate_all_scenarios()

    print(f"\n✓ Generated {len(scenarios)} scenarios:")
    for name, path in scenarios.items():
        file_count = len(list(path.glob("*.mkv"))) + len(list(path.glob("*.mp4"))) + len(list(path.glob("*.avi")))
        sub_count = len(list(path.glob("*.smi"))) + len(list(path.glob("*.srt"))) + len(list(path.glob("*.ass")))
        print(f"  - {name}: {file_count} files, {sub_count} subtitles")

