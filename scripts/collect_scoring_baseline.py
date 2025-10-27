#!/usr/bin/env python3
"""
Scoring Baseline Collection Script

Collects current matching results before migrating to ScoringWeights constants.
This allows us to verify that the migration doesn't change matching behavior.
"""

import asyncio
import json
import logging

# Add src to path for imports
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from anivault.core.matching.normalizer import QueryNormalizer

from anivault.core.matching.engine import MatchingEngine
from anivault.services.tmdb_client import TMDBClient

logger = logging.getLogger(__name__)


class ScoringBaselineCollector:
    """Collects scoring baseline for verification."""

    def __init__(self, api_key: str):
        """Initialize baseline collector.

        Args:
            api_key: TMDB API key
        """
        self.tmdb_client = TMDBClient(api_key)
        self.normalizer = QueryNormalizer()
        self.engine = MatchingEngine(self.tmdb_client, self.normalizer)
        self.results = []

    async def collect_baseline(
        self, test_files: list[str]
    ) -> list[dict[str, any]]:
        """Collect baseline matching results.

        Args:
            test_files: List of test filenames to match

        Returns:
            List of baseline results with confidence scores
        """
        results = []

        for filename in test_files:
            try:
                # Parse filename
                parsed = self.normalizer.parse_filename(filename)
                if not parsed:
                    logger.warning("Failed to parse: %s", filename)
                    continue

                # Normalize query
                normalized = self.normalizer.normalize_query(parsed)

                # Search TMDB
                tmdb_results = await self.engine._search_tmdb(
                    normalized, media_type="tv"
                )

                if tmdb_results:
                    best_match = tmdb_results[0]
                    results.append(
                        {
                            "filename": filename,
                            "parsed_title": parsed.get("anime_title"),
                            "tmdb_id": best_match.get("id"),
                            "tmdb_title": best_match.get("title")
                            or best_match.get("name"),
                            "confidence": best_match.get("confidence", 0.0),
                            "media_type": best_match.get("media_type"),
                        }
                    )
                else:
                    results.append(
                        {
                            "filename": filename,
                            "parsed_title": parsed.get("anime_title"),
                            "tmdb_id": None,
                            "tmdb_title": None,
                            "confidence": 0.0,
                            "media_type": None,
                        }
                    )

                logger.info(
                    "Processed: %s -> %s (%.3f)",
                    filename,
                    results[-1]["tmdb_title"],
                    results[-1]["confidence"],
                )

            except Exception as e:
                logger.exception("Error processing %s: %s", filename, e)
                results.append(
                    {
                        "filename": filename,
                        "error": str(e),
                        "confidence": 0.0,
                    }
                )

        return results


def get_test_files() -> list[str]:
    """Get representative test filenames.

    Returns:
        List of anime filenames for baseline testing
    """
    return [
        "[SubsPlease] Shingeki no Kyojin - 01 (1080p) [12345678].mkv",
        "[HorribleSubs] Kimetsu no Yaiba - 01 [1080p].mkv",
        "[Erai-raws] Jujutsu Kaisen - 01 [1080p].mkv",
        "[SubsPlease] Spy x Family - 01 (1080p).mkv",
        "[HorribleSubs] One Piece - 1000 [720p].mkv",
        "[Erai-raws] Chainsaw Man - 01 [1080p].mkv",
        "[SubsPlease] Bleach - Sennen Kessen Hen - 01 (1080p).mkv",
        "[HorribleSubs] Boku no Hero Academia - S05E01 [1080p].mkv",
        "[Erai-raws] Tokyo Revengers - 01 [1080p].mkv",
        "[SubsPlease] Kaguya-sama wa Kokurasetai - 01 (1080p).mkv",
        "[HorribleSubs] Re Zero kara Hajimeru Isekai Seikatsu - 01 [720p].mkv",
        "[Erai-raws] Sono Bisque Doll wa Koi wo Suru - 01 [1080p].mkv",
        "[SubsPlease] Mob Psycho 100 - S03E01 (1080p).mkv",
        "[HorribleSubs] Dr. Stone - 01 [1080p].mkv",
        "[Erai-raws] Made in Abyss - 01 [1080p].mkv",
        "[SubsPlease] Vinland Saga - S02E01 (1080p).mkv",
        "[HorribleSubs] Yakusoku no Neverland - 01 [720p].mkv",
        "[Erai-raws] Lycoris Recoil - 01 [1080p].mkv",
        "[SubsPlease] Bocchi the Rock - 01 (1080p).mkv",
        "[HorribleSubs] Tensei shitara Slime Datta Ken - 01 [1080p].mkv",
    ]


async def main():
    """Main entry point."""
    # Get API key from environment
    import os

    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        print("ERROR: TMDB_API_KEY environment variable not set")
        print("Please set it: export TMDB_API_KEY=your_api_key")
        return 1

    # Setup logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Collect baseline
    collector = ScoringBaselineCollector(api_key)
    test_files = get_test_files()

    print(f"Collecting baseline for {len(test_files)} test files...")
    results = await collector.collect_baseline(test_files)

    # Save baseline
    baseline_file = Path("scripts/scoring_baseline.json")
    baseline_data = {
        "test_files_count": len(test_files),
        "successful_matches": len([r for r in results if r.get("tmdb_id")]),
        "results": results,
    }

    baseline_file.write_text(json.dumps(baseline_data, indent=2, ensure_ascii=False))

    print(f"\n✅ Baseline saved to {baseline_file}")
    print(f"   Total files: {len(test_files)}")
    print(
        f"   Successful matches: {baseline_data['successful_matches']}/{len(test_files)}"
    )
    print(
        f"   Average confidence: {sum(r['confidence'] for r in results) / len(results):.3f}"
    )

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
