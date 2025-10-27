#!/usr/bin/env python3
"""
Scoring Baseline Verification Script

Verifies that scoring changes don't affect matching behavior by comparing
new results against the baseline collected before migration.
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


class ScoringVerifier:
    """Verifies scoring changes against baseline."""

    def __init__(self, api_key: str, baseline_file: Path):
        """Initialize verifier.

        Args:
            api_key: TMDB API key
            baseline_file: Path to baseline JSON file
        """
        self.tmdb_client = TMDBClient(api_key)
        self.normalizer = QueryNormalizer()
        self.engine = MatchingEngine(self.tmdb_client, self.normalizer)
        self.baseline = self._load_baseline(baseline_file)

    def _load_baseline(self, baseline_file: Path) -> dict:
        """Load baseline data.

        Args:
            baseline_file: Path to baseline JSON

        Returns:
            Baseline data dictionary
        """
        if not baseline_file.exists():
            raise FileNotFoundError(f"Baseline file not found: {baseline_file}")

        return json.loads(baseline_file.read_text(encoding="utf-8"))

    async def verify(self) -> tuple[bool, list[dict]]:
        """Verify current results against baseline.

        Returns:
            Tuple of (all_passed, differences)
        """
        baseline_results = {r["filename"]: r for r in self.baseline["results"]}
        differences = []
        all_passed = True

        for filename, baseline_result in baseline_results.items():
            try:
                # Get current result
                parsed = self.normalizer.parse_filename(filename)
                if not parsed:
                    logger.warning("Failed to parse: %s", filename)
                    continue

                normalized = self.normalizer.normalize_query(parsed)
                current_results = await self.engine._search_tmdb(
                    normalized, media_type="tv"
                )

                # Compare with baseline
                if current_results:
                    current_best = current_results[0]
                    current_tmdb_id = current_best.get("id")
                    current_confidence = current_best.get("confidence", 0.0)
                else:
                    current_tmdb_id = None
                    current_confidence = 0.0

                baseline_tmdb_id = baseline_result.get("tmdb_id")
                baseline_confidence = baseline_result.get("confidence", 0.0)

                # Check for differences
                tmdb_id_match = current_tmdb_id == baseline_tmdb_id
                confidence_diff = abs(current_confidence - baseline_confidence)
                confidence_match = confidence_diff < 0.05  # Allow ±0.05 variation

                if not tmdb_id_match or not confidence_match:
                    all_passed = False
                    differences.append(
                        {
                            "filename": filename,
                            "baseline_tmdb_id": baseline_tmdb_id,
                            "current_tmdb_id": current_tmdb_id,
                            "baseline_confidence": baseline_confidence,
                            "current_confidence": current_confidence,
                            "confidence_diff": confidence_diff,
                            "tmdb_id_match": tmdb_id_match,
                            "confidence_match": confidence_match,
                        }
                    )

                status = "✅" if tmdb_id_match and confidence_match else "❌"
                logger.info(
                    "%s %s: TMDB=%s (%.3f vs %.3f)",
                    status,
                    filename[:50],
                    "MATCH" if tmdb_id_match else "DIFF",
                    baseline_confidence,
                    current_confidence,
                )

            except Exception as e:
                logger.exception("Error verifying %s: %s", filename, e)
                all_passed = False
                differences.append(
                    {"filename": filename, "error": str(e)}
                )

        return all_passed, differences


async def main():
    """Main entry point."""
    # Get API key from environment
    import os

    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        print("ERROR: TMDB_API_KEY environment variable not set")
        return 1

    # Setup logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Load baseline
    baseline_file = Path("scripts/scoring_baseline.json")
    if not baseline_file.exists():
        print(f"ERROR: Baseline file not found: {baseline_file}")
        print("Please run collect_scoring_baseline.py first")
        return 1

    # Verify
    verifier = ScoringVerifier(api_key, baseline_file)
    print(f"Verifying against baseline: {baseline_file}")
    print(f"Test files: {verifier.baseline['test_files_count']}")
    print()

    all_passed, differences = await verifier.verify()

    # Report results
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ VERIFICATION PASSED!")
        print("All matching results are consistent with baseline.")
    else:
        print("❌ VERIFICATION FAILED!")
        print(f"Found {len(differences)} differences:")
        print()
        for diff in differences:
            print(f"  File: {diff['filename']}")
            if "error" in diff:
                print(f"    Error: {diff['error']}")
            else:
                if not diff["tmdb_id_match"]:
                    print(
                        f"    TMDB ID: {diff['baseline_tmdb_id']} -> {diff['current_tmdb_id']}"
                    )
                if not diff["confidence_match"]:
                    print(
                        f"    Confidence: {diff['baseline_confidence']:.3f} -> {diff['current_confidence']:.3f} (diff: {diff['confidence_diff']:.3f})"
                    )
            print()

    # Save verification results
    verify_file = Path("scripts/scoring_verification_results.json")
    verify_data = {
        "all_passed": all_passed,
        "differences_count": len(differences),
        "differences": differences,
    }
    verify_file.write_text(json.dumps(verify_data, indent=2, ensure_ascii=False))
    print(f"Results saved to {verify_file}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
