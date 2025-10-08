#!/usr/bin/env python3
"""Phase 2 매직 값 분석 스크립트."""

import json
from collections import defaultdict


def analyze_violations(json_file: str):
    """매직 값 위반 사항 분석."""
    with open(json_file, encoding="utf-8") as f:
        data = json.load(f)

    print("📊 **매직 값 검증 결과 (Phase 2)**\n")
    print(f"총 분석 파일: {data['files_analyzed']}개")
    print(f"총 매직 값: {data['violations_count']}개\n")

    # 파일별 위반 건수
    file_violations = defaultdict(int)
    context_violations = defaultdict(int)
    type_violations = defaultdict(int)

    for v in data["violations"]:
        file_violations[v["file"]] += 1
        context_violations[v["context"]] += 1
        type_violations[v["type"]] += 1

    # 파일별 Top 15
    print("=" * 80)
    print("📁 **파일별 매직 값 Top 15**\n")
    sorted_files = sorted(file_violations.items(), key=lambda x: x[1], reverse=True)
    for file, count in sorted_files[:15]:
        file_short = file.replace("src\\anivault\\", "").replace("src/", "")
        print(f"  {count:3d}개  {file_short}")

    # 컨텍스트별 분포
    print("\n" + "=" * 80)
    print("🎯 **컨텍스트별 분포**\n")
    for context, count in sorted(
        context_violations.items(),
        key=lambda x: x[1],
        reverse=True,
    ):
        print(f"  {count:3d}개  {context}")

    # 타입별 분포
    print("\n" + "=" * 80)
    print("🔢 **타입별 분포**\n")
    for vtype, count in sorted(
        type_violations.items(),
        key=lambda x: x[1],
        reverse=True,
    ):
        print(f"  {count:3d}개  {vtype}")

    # 핫스팟 파일 상세 분석
    print("\n" + "=" * 80)
    print("🔥 **핫스팟 파일 상세 분석 (Top 3)**\n")

    for file, count in sorted_files[:3]:
        file_violations_detail = [v for v in data["violations"] if v["file"] == file]
        file_short = file.replace("src\\anivault\\", "").replace("src/", "")

        print(f"\n📄 **{file_short}** ({count}개)")
        print(f"{'='*60}")

        # 값 종류별 분류
        value_types = defaultdict(list)
        for v in file_violations_detail[:10]:  # 처음 10개만
            value_types[v["context"]].append(
                {"line": v["line"], "value": v["value"], "type": v["type"]},
            )

        for ctx, items in value_types.items():
            print(f"\n  [{ctx}]")
            for item in items:
                print(f"    L{item['line']:3d}: {item['value']}")


if __name__ == "__main__":
    analyze_violations("magic_violations_phase2.json")
