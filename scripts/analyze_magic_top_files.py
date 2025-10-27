#!/usr/bin/env python3
"""Analyze magic violations to find top files."""

import json
from pathlib import Path

violations_file = Path("magic_violations.json")
data = json.loads(violations_file.read_text(encoding="utf-8"))

print(f"Total violations: {data['violations_count']}")
print(f"Files analyzed: {data['files_analyzed']}")
print()

# Count by file
files = {}
for v in data["violations"]:
    file = v["file"]
    files[file] = files.get(file, 0) + 1

# Sort by count
top_files = sorted(files.items(), key=lambda x: x[1], reverse=True)[:15]

print("Top 15 files with most magic values:")
print("-" * 60)
for i, (file, count) in enumerate(top_files, 1):
    # Extract just filename for display
    filename = Path(file).name
    print(f"{i:2}. {filename:40} {count:4} violations")

# Analyze violation types
types = {}
for v in data["violations"]:
    vtype = v["type"]
    types[vtype] = types.get(vtype, 0) + 1

print()
print("Violation types:")
print("-" * 60)
for vtype, count in sorted(types.items(), key=lambda x: x[1], reverse=True):
    pct = (count / data["violations_count"]) * 100
    print(f"{vtype:10} {count:5} ({pct:5.1f}%)")
