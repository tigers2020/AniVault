#!/usr/bin/env python3
"""Compare magic violations before and after refactoring."""

import json
from pathlib import Path

old_file = Path("magic_violations.json")
new_file = Path("magic_violations_updated.json")

if not new_file.exists():
    print("ERROR: magic_violations_updated.json not found")
    print("Run: python scripts/validate_magic_values.py src/anivault --format json > magic_violations_updated.json")
    exit(1)

old_data = json.loads(old_file.read_text(encoding="utf-8"))
new_data = json.loads(new_file.read_text(encoding="utf-8"))

old_count = old_data["violations_count"]
new_count = new_data["violations_count"]
reduced = old_count - new_count
reduction_pct = (reduced / old_count * 100) if old_count > 0 else 0

print("=" * 60)
print("Magic Values Reduction Analysis")
print("=" * 60)
print(f"Before: {old_count:,} violations")
print(f"After:  {new_count:,} violations")
print(f"Reduced: {reduced:,} ({reduction_pct:.1f}%)")
print()

# Analyze by file
old_files = {}
new_files = {}

for v in old_data["violations"]:
    file = Path(v["file"]).name
    old_files[file] = old_files.get(file, 0) + 1

for v in new_data["violations"]:
    file = Path(v["file"]).name
    new_files[file] = new_files.get(file, 0) + 1

# Find files with reductions
print("Files with most reductions:")
print("-" * 60)
reductions = {}
for file in old_files:
    old_c = old_files[file]
    new_c = new_files.get(file, 0)
    if old_c > new_c:
        reductions[file] = old_c - new_c

top_reductions = sorted(reductions.items(), key=lambda x: x[1], reverse=True)[:10]
for file, reduction in top_reductions:
    old_c = old_files[file]
    new_c = new_files.get(file, 0)
    print(f"{file:40} {old_c:4} → {new_c:4} (-{reduction:3})")

