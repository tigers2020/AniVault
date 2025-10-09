#!/usr/bin/env python3
"""
통합 코드 품질 검증 시스템

앞서 개발한 세 개의 검증 스크립트를 통합하여 종합적인 코드 품질 검증을 수행합니다:
- 매직 값 탐지 (validate_magic_values.py)
- 함수 길이 및 복잡도 검증 (validate_function_length.py)
- 에러 처리 패턴 검증 (validate_error_handling.py)
"""

from __future__ import annotations

import argparse
import json
import subprocess  # nosec B404 - Safe usage in validation scripts
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


class CodeQualityValidator:
    """통합 코드 품질 검증기"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.scripts_dir = self.project_root / "scripts"

        # 검증 스크립트 경로들
        self.magic_values_script = self.scripts_dir / "validate_magic_values.py"
        self.function_length_script = self.scripts_dir / "validate_function_length.py"
        self.error_handling_script = self.scripts_dir / "validate_error_handling.py"

        # 결과 저장
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "validations": {
                "magic_values": {"violations": [], "status": "pending"},
                "function_length": {"violations": [], "status": "pending"},
                "error_handling": {"violations": [], "status": "pending"},
            },
            "summary": {
                "total_files_analyzed": 0,
                "total_violations": 0,
                "violations_by_type": {},
                "violations_by_severity": {},
                "overall_status": "pending",
            },
        }

    def run_validation(
        self,
        paths: list[str],
        exclude_patterns: list[str] | None = None,
    ) -> dict[str, Any]:
        """통합 검증 실행"""
        if exclude_patterns is None:
            exclude_patterns = []

        print("🔍 Starting comprehensive code quality validation...")
        print(f"📁 Project root: {self.project_root}")
        print(f"📂 Analyzing paths: {', '.join(paths)}")
        if exclude_patterns:
            print(f"🚫 Excluding patterns: {', '.join(exclude_patterns)}")
        print()

        # 1. 매직 값 검증
        print("1️⃣ Validating magic values...")
        self._run_magic_values_validation(paths, exclude_patterns)

        # 2. 함수 길이 및 복잡도 검증
        print("2️⃣ Validating function length and complexity...")
        self._run_function_length_validation(paths, exclude_patterns)

        # 3. 에러 처리 패턴 검증
        print("3️⃣ Validating error handling patterns...")
        self._run_error_handling_validation(paths, exclude_patterns)

        # 4. 결과 분석 및 요약
        print("4️⃣ Analyzing results and generating summary...")
        self._analyze_results()

        return self.results

    def _run_magic_values_validation(
        self,
        paths: list[str],
        exclude_patterns: list[str],  # noqa: ARG002
    ) -> None:
        """매직 값 검증 실행"""
        try:
            cmd = [sys.executable, str(self.magic_values_script), *paths]
            result = subprocess.run(  # nosec B603 - Trusted internal validation script
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=self.project_root,
                check=False,
            )

            if result.returncode == 0:
                self.results["validations"]["magic_values"]["status"] = "passed"
                print("   ✅ No magic values found")
            else:
                self.results["validations"]["magic_values"]["status"] = "failed"
                self.results["validations"]["magic_values"]["output"] = result.stdout
                self.results["validations"]["magic_values"]["error"] = result.stderr
                print("   ❌ Magic values found")
                print(f"   📝 Output: {result.stdout.strip()}")
        except (OSError, subprocess.SubprocessError) as e:
            self.results["validations"]["magic_values"]["status"] = "error"
            self.results["validations"]["magic_values"]["error"] = str(e)
            print(f"   ⚠️ Error running magic values validation: {e}")

    def _run_function_length_validation(
        self,
        paths: list[str],
        exclude_patterns: list[str],
    ) -> None:
        """함수 길이 및 복잡도 검증 실행"""
        try:
            cmd = [sys.executable, str(self.function_length_script), *paths]
            if exclude_patterns:
                cmd.extend(["--exclude", *exclude_patterns])
            result = subprocess.run(  # nosec B603 - Trusted internal validation script
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=self.project_root,
                check=False,
            )

            if result.returncode == 0:
                self.results["validations"]["function_length"]["status"] = "passed"
                print("   ✅ No function length/complexity violations found")
            else:
                self.results["validations"]["function_length"]["status"] = "failed"
                self.results["validations"]["function_length"]["output"] = result.stdout
                self.results["validations"]["function_length"]["error"] = result.stderr
                print("   ❌ Function length/complexity violations found")
                print(f"   📝 Output: {result.stdout.strip()}")
        except (OSError, subprocess.SubprocessError) as e:
            self.results["validations"]["function_length"]["status"] = "error"
            self.results["validations"]["function_length"]["error"] = str(e)
            print(f"   ⚠️ Error running function length validation: {e}")

    def _run_error_handling_validation(
        self,
        paths: list[str],
        exclude_patterns: list[str],
    ) -> None:
        """에러 처리 패턴 검증 실행"""
        try:
            cmd = [sys.executable, str(self.error_handling_script), *paths]
            if exclude_patterns:
                cmd.extend(["--exclude", *exclude_patterns])
            result = subprocess.run(  # nosec B603 - Trusted internal validation script
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=self.project_root,
                check=False,
            )

            if result.returncode == 0:
                self.results["validations"]["error_handling"]["status"] = "passed"
                print("   ✅ No error handling violations found")
            else:
                self.results["validations"]["error_handling"]["status"] = "failed"
                self.results["validations"]["error_handling"]["output"] = result.stdout
                self.results["validations"]["error_handling"]["error"] = result.stderr
                print("   ❌ Error handling violations found")
                print(f"   📝 Output: {result.stdout.strip()}")
        except (OSError, subprocess.SubprocessError) as e:
            self.results["validations"]["error_handling"]["status"] = "error"
            self.results["validations"]["error_handling"]["error"] = str(e)
            print(f"   ⚠️ Error running error handling validation: {e}")

    def _analyze_results(self) -> None:
        """결과 분석 및 요약 생성"""
        # 전체 상태 결정
        all_passed = all(
            validation["status"] == "passed"
            for validation in self.results["validations"].values()
        )

        any_errors = any(
            validation["status"] == "error"
            for validation in self.results["validations"].values()
        )

        if any_errors:
            self.results["summary"]["overall_status"] = "error"
        elif all_passed:
            self.results["summary"]["overall_status"] = "passed"
        else:
            self.results["summary"]["overall_status"] = "failed"

        # 위반 사항 통계
        total_violations = 0
        violations_by_type = {}

        for validation_name, validation in self.results["validations"].items():
            if validation["status"] == "failed":
                # 출력에서 위반 사항 수 파싱 (간단한 휴리스틱)
                output = validation.get("output", "")
                if "Found" in output and "violation" in output:
                    try:
                        # "Found X violation(s):" 패턴에서 숫자 추출
                        import re

                        match = re.search(r"Found (\d+) violation", output)
                        if match:
                            count = int(match.group(1))
                            total_violations += count
                            violations_by_type[validation_name] = count
                    except (ValueError, AttributeError):
                        pass

        self.results["summary"]["total_violations"] = total_violations
        self.results["summary"]["violations_by_type"] = violations_by_type

        # 파일 수 계산 (대략적)
        analyzed_files = 0
        for validation in self.results["validations"].values():
            if "output" in validation and "Analyzed" in validation["output"]:
                try:
                    import re

                    match = re.search(r"Analyzed (\d+) files", validation["output"])
                    if match:
                        analyzed_files = max(analyzed_files, int(match.group(1)))
                except (ValueError, AttributeError):
                    pass

        self.results["summary"]["total_files_analyzed"] = analyzed_files

    def generate_report(
        self,
        output_format: str = "text",
        output_file: str | None = None,
    ) -> str:
        """검증 결과 리포트 생성"""
        if output_format == "json":
            report = json.dumps(self.results, indent=2, ensure_ascii=False)
        else:
            report = self._generate_text_report()

        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"📄 Report saved to: {output_path}")

        return report

    def _generate_text_report(self) -> str:
        """텍스트 리포트 생성"""
        lines = []
        lines.append("=" * 80)
        lines.append("🔍 CODE QUALITY VALIDATION REPORT")
        lines.append("=" * 80)
        lines.append(f"📅 Timestamp: {self.results['timestamp']}")
        lines.append(f"📁 Project: {self.results['project_root']}")
        lines.append(
            f"📊 Overall Status: {self.results['summary']['overall_status'].upper()}",
        )
        lines.append("")

        # 요약 정보
        lines.append("📈 SUMMARY")
        lines.append("-" * 40)
        lines.append(
            f"Files Analyzed: {self.results['summary']['total_files_analyzed']}",
        )
        lines.append(f"Total Violations: {self.results['summary']['total_violations']}")
        lines.append("")

        # 각 검증 결과
        lines.append("🔍 VALIDATION RESULTS")
        lines.append("-" * 40)

        for validation_name, validation in self.results["validations"].items():
            status_emoji = {
                "passed": "✅",
                "failed": "❌",
                "error": "⚠️",
                "pending": "⏳",
            }.get(validation["status"], "❓")

            lines.append(
                f"{status_emoji} {validation_name.replace('_', ' ').title()}: {validation['status'].upper()}",
            )

            if validation["status"] == "failed" and "output" in validation:
                # 주요 위반 사항만 표시
                output_lines = validation["output"].split("\n")
                for line in output_lines[:10]:  # 처음 10줄만
                    if line.strip():
                        lines.append(f"    {line}")
                if len(output_lines) > 10:
                    lines.append(f"    ... and {len(output_lines) - 10} more lines")
                lines.append("")

            elif validation["status"] == "error" and "error" in validation:
                lines.append(f"    Error: {validation['error']}")
                lines.append("")

        # 권장사항
        lines.append("💡 RECOMMENDATIONS")
        lines.append("-" * 40)

        if self.results["summary"]["overall_status"] == "passed":
            lines.append("🎉 Congratulations! All code quality checks passed.")
            lines.append("   Your code follows best practices for:")
            lines.append("   • Magic value elimination")
            lines.append("   • Function length and complexity")
            lines.append("   • Error handling patterns")
        else:
            lines.append("🔧 Code quality improvements needed:")

            for validation_name, validation in self.results["validations"].items():
                if validation["status"] == "failed":
                    if validation_name == "magic_values":
                        lines.append(
                            "   • Replace hardcoded strings/numbers with constants",
                        )
                    elif validation_name == "function_length":
                        lines.append(
                            "   • Break down long functions into smaller units",
                        )
                        lines.append("   • Reduce function complexity")
                    elif validation_name == "error_handling":
                        lines.append("   • Improve error handling patterns")
                        lines.append("   • Use structured logging instead of print")
                        lines.append(
                            "   • Add proper error context and user-friendly messages",
                        )

        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="Comprehensive code quality validation system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/validate_code_quality.py src/
  python scripts/validate_code_quality.py --exclude tests/ src/
  python scripts/validate_code_quality.py --format json --output report.json src/
  python scripts/validate_code_quality.py --format text --output report.txt src/
        """,
    )

    parser.add_argument("paths", nargs="+", help="File or directory paths to analyze")

    parser.add_argument(
        "--exclude",
        nargs="*",
        default=[],
        help="Patterns to exclude from analysis",
    )

    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    parser.add_argument("--output", help="Output file path (optional)")

    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root directory (default: current directory)",
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    # 검증기 초기화
    validator = CodeQualityValidator(args.project_root)

    # 검증 실행
    results = validator.run_validation(args.paths, args.exclude)

    # 리포트 생성
    report = validator.generate_report(args.format, args.output)

    # 출력
    if not args.output:
        print("\n" + "=" * 80)
        print("📄 VALIDATION REPORT")
        print("=" * 80)
        print(report)

    # 종료 코드 결정
    if results["summary"]["overall_status"] == "passed":
        return 0
    if results["summary"]["overall_status"] == "error":
        return 2
    return 1


if __name__ == "__main__":
    sys.exit(main())
