"""Script to create real-world test dataset from filenames.txt."""

from __future__ import annotations

import json
import random
from pathlib import Path

from anivault.core.parser.anime_parser import AnimeFilenameParser


def load_filenames(filepath: str) -> list[str]:
    """Load filenames from file.

    Args:
        filepath: Path to filenames.txt

    Returns:
        List of filenames (excluding first line)
    """
    with open(filepath, encoding="utf-8") as f:
        lines = f.readlines()

    # Skip first line (script name) and filter video files only
    filenames = []
    video_exts = {".avi", ".mp4", ".mkv", ".wmv", ".flv", ".webm", ".mov"}

    for line in lines[1:]:
        line = line.strip()
        if line and any(line.lower().endswith(ext) for ext in video_exts):
            filenames.append(line)

    return filenames


def select_diverse_samples(filenames: list[str], count: int = 120) -> list[str]:
    """Select diverse samples covering different patterns.

    Args:
        filenames: List of all filenames
        count: Number of samples to select

    Returns:
        List of selected filenames
    """
    random.seed(42)  # For reproducibility

    # Categorize filenames
    categories = {
        "korean_titles": [],
        "japanese_titles": [],
        "english_titles": [],
        "high_quality": [],
        "release_groups": [],
        "season_episode": [],
        "simple_format": [],
    }

    for filename in filenames:
        # Korean characters
        if any("\uac00" <= c <= "\ud7a3" for c in filename):
            categories["korean_titles"].append(filename)

        # Release groups
        if filename.startswith("["):
            categories["release_groups"].append(filename)

        # High quality markers
        if any(q in filename for q in ["1280x720", "1920x1080", "BD", "BluRay"]):
            categories["high_quality"].append(filename)

        # Season/episode patterns
        if "S0" in filename or "EP" in filename.upper():
            categories["season_episode"].append(filename)

    # Select samples from each category
    samples = []
    target_per_category = count // len(categories)

    for files in categories.values():
        if files:
            n = min(target_per_category, len(files))
            samples.extend(random.sample(files, n))

    # Fill remaining with random samples
    remaining = count - len(samples)
    if remaining > 0:
        remaining_files = [f for f in filenames if f not in samples]
        if remaining_files:
            samples.extend(
                random.sample(remaining_files, min(remaining, len(remaining_files))),
            )

    return samples[:count]


def create_dataset(filenames: list[str], output_path: str) -> None:
    """Create test dataset with parser results.

    Args:
        filenames: List of filenames to process
        output_path: Path to output JSON file
    """
    parser = AnimeFilenameParser()
    dataset = []

    print(f"Processing {len(filenames)} filenames...")

    for i, filename in enumerate(filenames):
        result = parser.parse(filename)

        entry = {
            "filename": filename,
            "expected": {
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
            "confidence": round(result.confidence, 2),
        }

        dataset.append(entry)

        if (i + 1) % 20 == 0:
            print(f"  Processed {i + 1}/{len(filenames)}")

    # Save to JSON
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Dataset created: {output_path}")
    print(f"   Total entries: {len(dataset)}")

    # Print statistics
    parser_stats = {}
    for entry in dataset:
        parser_used = entry["parser_used"]
        parser_stats[parser_used] = parser_stats.get(parser_used, 0) + 1

    print("\n📊 Parser usage:")
    for parser, count in sorted(parser_stats.items()):
        percentage = (count / len(dataset)) * 100
        print(f"   {parser}: {count} ({percentage:.1f}%)")

    avg_confidence = sum(e["confidence"] for e in dataset) / len(dataset)
    print(f"\n📈 Average confidence: {avg_confidence:.2f}")


def main():
    """Main function."""
    print("🎬 Creating real-world test dataset...\n")

    # Load filenames
    filenames = load_filenames("filenames.txt")
    print(f"📁 Loaded {len(filenames)} video filenames\n")

    # Select diverse samples
    samples = select_diverse_samples(filenames, count=120)
    print(f"✨ Selected {len(samples)} diverse samples\n")

    # Create dataset
    create_dataset(samples, "tests/fixtures/real_world_filenames.json")

    print("\n✅ Done!")


if __name__ == "__main__":
    main()
