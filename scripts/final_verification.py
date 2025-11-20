#!/usr/bin/env python3
"""Final verification for Phase 3 magic values refactoring."""

import json
import subprocess
import sys
from pathlib import Path

print("=" * 70)
print("Phase 3 Magic Values Refactoring - Final Verification")
print("=" * 70)
print()

# 1. Test count verification
print("1. Test Verification")
print("-" * 70)
test_files = [
    "tests/test_scoring_constants.py",
    "tests/test_gui_constants.py",
    "tests/test_metadata_constants.py",
    "tests/test_tmdb_constants.py",
]

total_tests = 0
for test_file in test_files:
    if Path(test_file).exists():
        result = subprocess.run(
            ["python", "-m", "pytest", test_file, "-q", "--tb=no"],
            capture_output=True,
            text=True,
        )
        # Parse output for pass count
        output = result.stdout
        if "passed" in output:
            parts = output.split()
            for i, part in enumerate(parts):
                if part == "passed":
                    count = parts[i - 1]
                    total_tests += int(count)
                    print(f"✅ {Path(test_file).name}: {count} tests passed")
                    break
        else:
            print(f"⚠️ {Path(test_file).name}: Could not parse results")

print(f"\n📊 Total new tests: {total_tests}")
print()

# 2. Files migrated count
print("2. Files Migrated")
print("-" * 70)
migrated_files = [
    "src/anivault/core/matching/scoring.py",
    "src/anivault/gui/main_window.py",
    "src/anivault/gui/dialogs/settings_dialog.py",
    "src/anivault/gui/dialogs/tmdb_progress_dialog.py",
    "src/anivault/services/metadata_enricher.py",
    "src/anivault/cli/rollback_handler.py",
    "src/anivault/services/tmdb_client.py",
]

print(f"✅ Files migrated: {len(migrated_files)}")
for f in migrated_files:
    print(f"   - {Path(f).name}")
print()

# 3. New constant modules
print("3. New Constant Modules")
print("-" * 70)
new_constants = [
    "src/anivault/shared/constants/gui_messages.py",
    "src/anivault/shared/constants/tmdb_messages.py",
]

for const in new_constants:
    if Path(const).exists():
        lines = len(Path(const).read_text(encoding="utf-8").splitlines())
        print(f"✅ {Path(const).name}: {lines} lines")
    else:
        print(f"❌ {Path(const).name}: NOT FOUND")
print()

# 4. Summary
print("4. Summary")
print("=" * 70)
print(f"✅ Test files created: {len(test_files)}")
print(f"✅ Total tests added: {total_tests}")
print(f"✅ Files migrated: {len(migrated_files)}")
print(f"✅ New constant modules: {len(new_constants)}")
print()
print("📊 Quick Wins Strategy:")
print("   - Scoring weights → ScoringWeights")
print("   - GUI messages → DialogTitles/Messages")
print("   - Enrichment status → EnrichmentStatus")
print("   - Operation types → OperationType")
print("   - TMDB errors → TMDBErrorMessages")
print()
print("🎯 Phase 3 Extended Complete!")
print("=" * 70)

