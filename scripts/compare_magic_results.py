#!/usr/bin/env python3
"""Phase 2와 리팩토링 후 매직 값 비교 스크립트."""

import json


def compare_results():
    """리팩토링 전후 비교."""
    # Before
    with open("magic_violations_phase2.json", encoding="utf-8") as f:
        before = json.load(f)

    # After
    with open("magic_violations_post_refactor.json", encoding="utf-8") as f:
        after = json.load(f)

    print("=" * 80)
    print("📊 **매직 값 리팩토링 결과 비교**\n")

    print(f"Before: {before['violations_count']:,}개")
    print(f"After:  {after['violations_count']:,}개")

    reduced = before["violations_count"] - after["violations_count"]
    if before["violations_count"] > 0:
        reduction_pct = (reduced / before["violations_count"]) * 100
        print(f"\n감소: {reduced:,}개 ({reduction_pct:.1f}%)")

    # 파일별 비교
    before_files = {}
    after_files = {}

    for v in before["violations"]:
        before_files[v["file"]] = before_files.get(v["file"], 0) + 1

    for v in after["violations"]:
        after_files[v["file"]] = after_files.get(v["file"], 0) + 1

    print("\n" + "=" * 80)
    print("📁 **파일별 개선 Top 10**\n")

    improvements = {}
    for file in before_files:
        before_count = before_files[file]
        after_count = after_files.get(file, 0)
        if before_count > after_count:
            improvements[file] = before_count - after_count

    sorted_improvements = sorted(improvements.items(), key=lambda x: x[1], reverse=True)

    for file, reduced_count in sorted_improvements[:10]:
        file_short = file.replace("src\\anivault\\", "").replace("src/", "")
        before_count = before_files[file]
        after_count = after_files.get(file, 0)
        pct = (reduced_count / before_count) * 100 if before_count > 0 else 0
        print(
            f"  -{reduced_count:3d} ({pct:5.1f}%)  {file_short:50s}  ({before_count} → {after_count})",
        )


if __name__ == "__main__":
    compare_results()
