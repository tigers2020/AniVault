"""Analyze function violations to identify real issues."""

import json
from pathlib import Path


def analyze_violations():
    """Analyze function violations and categorize them."""

    # Load violations
    violations_file = Path("function_violations_current.json")
    with violations_file.open(encoding="utf-8") as f:
        data = json.load(f)

    violations = data["violations"]

    # Categorize by type
    by_type = {}
    for v in violations:
        vtype = v["type"]
        if vtype not in by_type:
            by_type[vtype] = []
        by_type[vtype].append(v)

    # Print summary
    print("=" * 80)
    print("FUNCTION VIOLATIONS ANALYSIS")
    print("=" * 80)
    print(f"\nTotal violations: {len(violations)}")
    print(f"Files analyzed: {data['files_analyzed']}")

    print("\n" + "=" * 80)
    print("BY TYPE")
    print("=" * 80)
    for vtype, items in sorted(by_type.items()):
        print(f"\n{vtype}: {len(items)} violations")

        if vtype == "complexity":
            # Sort by complexity value
            sorted_items = sorted(items, key=lambda x: x["value"], reverse=True)
            print("\nTop 10 complexity violations:")
            for i, v in enumerate(sorted_items[:10], 1):
                print(f"  {i:2}. {v['file']}:{v['line']}")
                print(f"      {v['function']}() - CC={v['value']}")

        elif vtype == "length":
            # Sort by length
            sorted_items = sorted(items, key=lambda x: x["value"], reverse=True)
            print("\nTop 10 length violations:")
            for i, v in enumerate(sorted_items[:10], 1):
                print(f"  {i:2}. {v['file']}:{v['line']}")
                print(f"      {v['function']}() - {v['value']} lines")

        elif vtype == "mixed_responsibilities":
            # Group by file
            by_file = {}
            for v in items:
                file = v["file"]
                if file not in by_file:
                    by_file[file] = []
                by_file[file].append(v)

            print(f"\nFiles with mixed responsibilities ({len(by_file)} files):")
            for file, items in sorted(
                by_file.items(), key=lambda x: len(x[1]), reverse=True
            )[:10]:
                print(f"  - {file}: {len(items)} violations")

    # Real issues (complexity > 10 or length > 150)
    print("\n" + "=" * 80)
    print("REAL ISSUES (CC > 10 or Length > 150)")
    print("=" * 80)

    real_issues = [
        v
        for v in violations
        if (v["type"] == "complexity" and v["value"] > 10)
        or (v["type"] == "length" and v["value"] > 150)
    ]

    print(f"\nTotal real issues: {len(real_issues)}")

    if real_issues:
        print("\nDetailed list:")
        for i, v in enumerate(real_issues, 1):
            print(f"\n{i}. {v['file']}:{v['line']}")
            print(f"   Function: {v['function']}()")
            print(f"   Type: {v['type']}")
            print(f"   Value: {v['value']}")
            if "context" in v:
                print(f"   Context: {v['context']}")


if __name__ == "__main__":
    analyze_violations()
