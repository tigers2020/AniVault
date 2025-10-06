#!/usr/bin/env python3
"""
AI 보안 룰 우선순위 검증 스크립트

이 스크립트는 .cursor/rules/ 디렉토리의 모든 룰 파일들을 검사하여
우선순위가 올바르게 설정되어 있는지 확인합니다.

사용법:
    python scripts/validate_rule_priority.py

검증 항목:
1. 최상위 우선권 룰 (00_ai_security_priority.mdc) 존재
2. 우선순위 번호 중복 없음
3. 모든 룰에 우선순위 설정
4. 우선순위 순서가 올바름
"""

from __future__ import annotations

import sys
from pathlib import Path


def find_rule_files() -> list[Path]:
    """룰 파일들을 찾습니다."""
    rules_dir = Path(".cursor/rules")
    if not rules_dir.exists():
        print("❌ .cursor/rules 디렉토리가 존재하지 않습니다.")
        return []

    rule_files = list(rules_dir.rglob("*.mdc"))

    return sorted(rule_files)


def extract_rule_metadata(file_path: Path) -> dict[str, str | None]:
    """룰 파일에서 메타데이터를 추출합니다."""
    metadata = {
        "file": str(file_path),
        "name": file_path.stem,
        "priority": None,
        "description": None,
        "alwaysApply": None,
        "globs": None,
    }

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # YAML frontmatter 추출
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                yaml_content = parts[1]

                # 간단한 YAML 파싱
                for line in yaml_content.split("\n"):
                    line = line.strip()
                    if ":" in line and not line.startswith("#"):
                        key, value = line.split(":", 1)
                        key = key.strip()
                        value = value.strip().strip("\"'")

                        if key == "priority":
                            metadata["priority"] = value
                        elif key == "description":
                            metadata["description"] = value
                        elif key == "alwaysApply":
                            metadata["alwaysApply"] = value
                        elif key == "globs":
                            metadata["globs"] = value

    except Exception as e:
        print(f"⚠️ 파일 읽기 실패: {file_path} - {e}")

    return metadata


def validate_rule_priority() -> dict[str, list[str]]:
    """룰 우선순위를 검증합니다."""
    rule_files = find_rule_files()

    if not rule_files:
        return {"errors": ["룰 파일이 없습니다."], "warnings": [], "info": []}

    errors = []
    warnings = []
    info = []

    # 룰 메타데이터 수집
    rules = []
    for file_path in rule_files:
        metadata = extract_rule_metadata(file_path)
        rules.append(metadata)

    # 1. 최상위 우선권 룰 확인
    priority_rule = None
    for rule in rules:
        if rule["name"] == "00_ai_security_priority":
            priority_rule = rule
            break

    if not priority_rule:
        errors.append("최상위 우선권 룰 (00_ai_security_priority.mdc)이 없습니다.")
    else:
        info.append(f"✅ 최상위 우선권 룰 발견: {priority_rule['file']}")
        if priority_rule["priority"] != "1":
            warnings.append(
                f"최상위 우선권 룰의 우선순위가 1이 아닙니다: {priority_rule['priority']}",
            )

    # 2. 우선순위 중복 확인
    priorities: dict[str, str] = {}
    for rule in rules:
        if rule["priority"]:
            priority = rule["priority"]
            if priority in priorities:
                errors.append(
                    f"우선순위 {priority} 중복: {priorities[priority]}과 {rule['file']}",
                )
            else:
                priorities[priority] = rule["file"]

    # 3. 우선순위 누락 확인
    missing_priority = []
    for rule in rules:
        if not rule["priority"]:
            missing_priority.append(rule["file"])

    if missing_priority:
        warnings.append(f"우선순위가 설정되지 않은 룰들: {', '.join(missing_priority)}")

    # 4. 우선순위 순서 확인
    try:
        sorted_priorities = sorted([int(p) for p in priorities if p.isdigit()])
        expected_sequence = list(range(1, len(sorted_priorities) + 1))

        if sorted_priorities != expected_sequence:
            warnings.append(f"우선순위 순서가 연속적이지 않습니다: {sorted_priorities}")

        info.append(f"✅ 우선순위 순서: {sorted_priorities}")

    except ValueError:
        errors.append("우선순위에 숫자가 아닌 값이 있습니다.")

    # 5. 룰 상세 정보
    info.append(f"총 {len(rules)}개의 룰 파일 발견")
    for rule in sorted(
        rules,
        key=lambda x: (
            int(x["priority"]) if x["priority"] and x["priority"].isdigit() else 999
        ),
    ):
        priority_info = (
            f"우선순위 {rule['priority']}" if rule["priority"] else "우선순위 없음"
        )
        info.append(f"  - {rule['name']}: {priority_info}")

    return {"errors": errors, "warnings": warnings, "info": info}


def print_validation_results(results: dict[str, list[str]]) -> None:
    """검증 결과를 출력합니다."""
    print("🔍 AI 보안 룰 우선순위 검증 결과")
    print("=" * 50)

    if results["errors"]:
        print("\n❌ 오류:")
        for error in results["errors"]:
            print(f"  - {error}")

    if results["warnings"]:
        print("\n⚠️ 경고:")
        for warning in results["warnings"]:
            print(f"  - {warning}")

    if results["info"]:
        print("\nℹ️ 정보:")
        for info in results["info"]:
            print(f"  - {info}")

    print("\n" + "=" * 50)

    # 요약
    total_issues = len(results["errors"]) + len(results["warnings"])
    if total_issues == 0:
        print("🎉 모든 검증을 통과했습니다!")
        return True
    print(f"⚠️ 총 {total_issues}개의 이슈가 발견되었습니다.")
    return False


def main():
    """메인 함수."""
    print("🚨 AI 보안 룰 우선순위 검증 시작...")

    results = validate_rule_priority()
    success = print_validation_results(results)

    if not success:
        print("\n📋 권장사항:")
        print("1. 최상위 우선권 룰 (00_ai_security_priority.mdc) 확인")
        print("2. 모든 룰에 우선순위 설정")
        print("3. 우선순위 중복 제거")
        print("4. 우선순위 순서 정리")
        sys.exit(1)
    else:
        print("\n✅ AI 보안 룰 우선순위가 올바르게 설정되었습니다!")


if __name__ == "__main__":
    main()
