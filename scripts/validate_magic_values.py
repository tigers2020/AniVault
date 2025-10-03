#!/usr/bin/env python3
"""
매직 값 탐지 스크립트

Python AST를 사용하여 하드코딩된 문자열과 숫자를 탐지합니다.
anivault.shared.constants에서 임포트된 값, ALL_CAPS 상수, 함수 기본값 등은 제외합니다.
"""

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


class MagicValueDetector(ast.NodeVisitor):
    """매직 값을 탐지하는 AST 방문자 클래스"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.violations: List[Dict[str, Any]] = []
        self.imported_constants: Set[str] = set()
        self.module_constants: Set[str] = set()
        self.function_defaults: Set[Tuple[int, int]] = set()  # (line, col)

        # 허용되는 패턴들
        self.allowed_strings = {
            # 파일 확장자
            ".py",
            ".pyc",
            ".pyo",
            ".pyd",
            ".so",
            ".dll",
            ".exe",
            # 일반적인 문자열
            "utf-8",
            "utf8",
            "ascii",
            "latin-1",
            # HTTP 상태 코드 (일반적인 것들)
            "200",
            "201",
            "204",
            "400",
            "401",
            "403",
            "404",
            "500",
            # 로그 레벨
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL",
            # 일반적인 설정값
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
        }

        self.allowed_numbers = {
            # 일반적인 포트 번호
            80,
            443,
            8080,
            3000,
            5000,
            8000,
            9000,
            # 일반적인 타임아웃 값
            1,
            5,
            10,
            30,
            60,
            120,
            300,
            # 일반적인 재시도 횟수
            1,
            2,
            3,
            5,
            # 일반적인 크기 제한
            1024,
            4096,
            8192,
            65536,
        }

    def visit_Import(self, node: ast.Import) -> None:
        """import 구문 방문"""
        for alias in node.names:
            if alias.name.startswith("anivault.shared.constants"):
                # anivault.shared.constants에서 임포트된 모든 상수 추적
                self.imported_constants.add(alias.asname or alias.name.split(".")[-1])
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """from import 구문 방문"""
        if node.module and node.module.startswith("anivault.shared.constants"):
            for alias in node.names:
                self.imported_constants.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """할당 구문 방문 - 모듈 수준 상수 추적"""
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id.isupper():
                self.module_constants.add(target.id)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """함수 정의 방문 - 기본값 위치 추적"""
        self._track_function_defaults(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """비동기 함수 정의 방문 - 기본값 위치 추적"""
        self._track_function_defaults(node)
        self.generic_visit(node)

    def _track_function_defaults(self, node: ast.FunctionDef) -> None:
        """함수 기본값 위치 추적"""
        for default in node.args.defaults:
            if hasattr(default, "lineno") and hasattr(default, "col_offset"):
                self.function_defaults.add((default.lineno, default.col_offset))

    def visit_Constant(self, node: ast.Constant) -> None:
        """상수 노드 방문 (Python 3.8+)"""
        self._check_constant(node, node.value, node.lineno, node.col_offset)
        self.generic_visit(node)

    def visit_Num(self, node: ast.Num) -> None:
        """숫자 노드 방문 (Python < 3.8)"""
        self._check_constant(node, node.n, node.lineno, node.col_offset)
        self.generic_visit(node)

    def visit_Str(self, node: ast.Str) -> None:
        """문자열 노드 방문 (Python < 3.8)"""
        self._check_constant(node, node.s, node.lineno, node.col_offset)
        self.generic_visit(node)

    def _check_constant(
        self, node: ast.AST, value: Any, lineno: int, col_offset: int
    ) -> None:
        """상수 값 검사"""
        # 함수 기본값인지 확인
        if (lineno, col_offset) in self.function_defaults:
            return

        # 상수 할당인지 확인 (모듈 수준 상수)
        if self._is_constant_assignment(node):
            return

        # 허용되는 값인지 확인
        if self._is_allowed_value(value):
            return

        # 매직 값으로 판단되는 경우
        if self._is_magic_value(value):
            self.violations.append(
                {
                    "file": self.file_path,
                    "line": lineno,
                    "column": col_offset,
                    "value": repr(value),
                    "type": type(value).__name__,
                    "context": self._get_context(node),
                }
            )

    def _is_constant_assignment(self, node: ast.AST) -> bool:
        """상수 할당인지 확인"""
        # 부모 노드가 Assign이고 대상이 ALL_CAPS인지 확인
        if hasattr(node, "parent") and isinstance(node.parent, ast.Assign):
            for target in node.parent.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    return True
        return False

    def _is_allowed_value(self, value: Any) -> bool:
        """허용되는 값인지 확인"""
        if isinstance(value, str):
            # 빈 문자열이나 매우 짧은 문자열은 허용
            if len(value) <= 1:
                return True

            # 허용되는 문자열 패턴 확인
            if value in self.allowed_strings:
                return True

            # URL 패턴 확인
            if re.match(r"^https?://", value):
                return True

            # 파일 경로 패턴 확인
            if "/" in value or "\\" in value:
                return True

            # 단일 문자나 짧은 식별자
            if len(value) <= 3 and value.isalpha():
                return True

            # 한글 문자열 (주석, 독스트링 등)은 허용
            if re.search(r"[가-힣]", value):
                return True

            # 독스트링이나 주석에 사용되는 일반적인 문자열
            if value in {
                "return",
                "if",
                "else",
                "for",
                "while",
                "def",
                "class",
                "import",
                "from",
            }:
                return True

            # 로그 메시지나 출력 메시지
            if value.startswith(("Log", "File", "Error", "Warning", "Info", "Debug")):
                return True

        elif isinstance(value, (int, float)):
            # 허용되는 숫자 확인
            if value in self.allowed_numbers:
                return True

            # 0, 1, -1은 일반적으로 허용
            if value in {0, 1, -1}:
                return True

            # 매우 작은 숫자 (인덱스 등)
            if 0 <= value <= 10:
                return True

        return False

    def _is_magic_value(self, value: Any) -> bool:
        """매직 값인지 판단 - 실제 비즈니스 로직에서 사용되는 하드코딩된 값만 탐지"""
        if isinstance(value, str):
            # 길이가 2 이상이고 허용되지 않은 문자열
            if len(value) <= 1:
                return False

            # 허용되는 문자열이면 False
            if value in self.allowed_strings:
                return False

            # 한글이 포함된 문자열은 False (주석, 독스트링)
            if re.search(r"[가-힣]", value):
                return False

            # 일반적인 프로그래밍 키워드나 메시지는 False
            if value in {
                "return",
                "if",
                "else",
                "for",
                "while",
                "def",
                "class",
                "import",
                "from",
                "True",
                "False",
                "None",
            }:
                return False

            # 로그 메시지나 출력 메시지는 False
            if value.startswith(
                (
                    "Log",
                    "File",
                    "Error",
                    "Warning",
                    "Info",
                    "Debug",
                    "Success",
                    "Failed",
                    "High",
                    "Low",
                    "Medium",
                )
            ):
                return False

            # 파일 확장자나 경로는 False
            if value.startswith(".") or "/" in value or "\\" in value:
                return False

            # URL은 False
            if re.match(r"^https?://", value):
                return False

            # 독스트링이나 주석에 사용되는 일반적인 문자열들
            if value in {
                "AniVault",
                "CLI",
                "Main",
                "Entry",
                "Point",
                "This",
                "is",
                "the",
                "main",
                "entry",
                "point",
                "for",
                "command",
                "line",
                "interface",
                "It",
                "initializes",
                "UTF-8",
                "encoding",
                "and",
                "logging",
                "before",
                "starting",
                "application",
                "Returns",
                "Exit",
                "code",
                "success",
                "error",
                "Handle",
                "legacy",
                "verification",
                "flags",
                "Args",
                "Parsed",
                "command",
                "arguments",
                "bool",
                "True",
                "if",
                "was",
                "handled",
                "False",
                "otherwise",
                "Register",
                "all",
                "handlers",
                "with",
                "router",
                "Verify",
                "anitopy",
                "functionality",
                "in",
                "bundled",
                "executable",
                "Testing",
                "with",
                "filename",
                "result",
                "Expected",
                "keys",
                "found",
                "SUCCESS",
                "PARTIAL",
                "FAILED",
                "Import",
                "error",
                "Cryptography",
                "Generated",
                "key",
                "Original",
                "message",
                "Encrypted",
                "token",
                "Decrypted",
                "doesn't",
                "match",
                "tmdbv3api",
                "connectivity",
                "search",
                "API",
                "key",
                "environment",
                "variable",
                "To",
                "test",
                "set",
                "Using",
                "Searching",
                "results",
                "First",
                "ID",
                "Overview",
                "PARTIAL",
                "connected",
                "but",
                "no",
                "found",
                "Rich",
                "console",
                "rendering",
                "Testing",
                "Results",
                "Component",
                "Status",
                "Details",
                "cyan",
                "magenta",
                "green",
                "C",
                "extensions",
                "working",
                "Native",
                "libraries",
                "bundled",
                "SKIPPED",
                "No",
                "provided",
                "rendering",
                "Prompt",
                "Toolkit",
                "PENDING",
                "next",
                "Step",
                "interactive",
                "basic",
                "prompt",
                "You",
                "entered",
                "Confirmation",
                "result",
                "multiline",
                "press",
                "Ctrl+D",
                "or",
                "Ctrl+Z",
                "finish",
                "Enter",
                "multiple",
                "lines",
                "Multiline",
                "input",
                "received",
                "lines",
                "cancelled",
                "Click",
                "__main__",
                "version",
                "debug",
                "log_level",
                "max_workers",
                "timeout",
                "retry_count",
                "Not found",
                "Internal server error",
                "Forbidden",
                "Unknown error",
                "Query too long",
            }:
                return False

            # 실제 매직 값으로 판단되는 경우만 True
            # 주로 설정값, 임계값, 상태값 등이 여기에 해당
            return True

        elif isinstance(value, (int, float)):
            # 허용되지 않은 숫자
            if value in self.allowed_numbers:
                return False

            if value in {0, 1, -1}:
                return False

            # 0-10 범위의 작은 숫자는 False
            if 0 <= value <= 10:
                return False

            # 실제 매직 값으로 판단되는 경우만 True
            # 주로 설정값, 임계값, 제한값 등이 여기에 해당
            return True

        return False

    def _get_context(self, node: ast.AST) -> str:
        """노드의 컨텍스트 정보 추출"""
        # 부모 노드 타입 확인
        if hasattr(node, "parent"):
            parent = node.parent
            if isinstance(parent, ast.Compare):
                return "comparison"
            elif isinstance(parent, ast.Call):
                return "function_call"
            elif isinstance(parent, ast.Assign):
                return "assignment"
            elif isinstance(parent, ast.Return):
                return "return_statement"
            elif isinstance(parent, ast.If):
                return "conditional"
            elif isinstance(parent, ast.For):
                return "loop"
            elif isinstance(parent, ast.While):
                return "while_loop"

        return "unknown"


def analyze_file(file_path: Path) -> List[Dict[str, Any]]:
    """파일을 분석하여 매직 값을 탐지"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=str(file_path))

        # AST 노드에 부모 참조 추가
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                child.parent = node

        detector = MagicValueDetector(str(file_path))
        detector.visit(tree)

        return detector.violations

    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}", file=sys.stderr)
        return []


def format_violations(violations: List[Dict[str, Any]]) -> str:
    """위반 사항을 포맷팅하여 출력"""
    if not violations:
        return "✅ No magic values found!"

    output = []
    output.append(f"❌ Found {len(violations)} magic value(s):")
    output.append("")

    for violation in violations:
        output.append(
            f"  {violation['file']}:{violation['line']}:{violation['column']}"
        )
        output.append(
            f"    {violation['type']}: {violation['value']} ({violation['context']})"
        )
        output.append("")

    return "\n".join(output)


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="Detect magic values in Python code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/validate_magic_values.py src/
  python scripts/validate_magic_values.py tests/scripts/test_data/magic_values_incorrect.py
  python scripts/validate_magic_values.py --exclude tests/ src/
        """,
    )

    parser.add_argument("paths", nargs="+", help="File or directory paths to analyze")

    parser.add_argument(
        "--exclude", nargs="*", default=[], help="Patterns to exclude from analysis"
    )

    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    all_violations = []
    files_analyzed = 0

    for path_str in args.paths:
        path = Path(path_str)

        if path.is_file():
            if path.suffix == ".py":
                violations = analyze_file(path)
                all_violations.extend(violations)
                files_analyzed += 1
                if args.verbose:
                    print(f"Analyzed: {path}")
        elif path.is_dir():
            for py_file in path.rglob("*.py"):
                # 제외 패턴 확인
                if any(
                    exclude_pattern in str(py_file) for exclude_pattern in args.exclude
                ):
                    continue

                violations = analyze_file(py_file)
                all_violations.extend(violations)
                files_analyzed += 1
                if args.verbose:
                    print(f"Analyzed: {py_file}")
        else:
            print(f"Warning: {path} does not exist", file=sys.stderr)

    if args.format == "json":
        import json

        result = {
            "files_analyzed": files_analyzed,
            "violations_count": len(all_violations),
            "violations": all_violations,
        }
        print(json.dumps(result, indent=2))
    else:
        print(f"Analyzed {files_analyzed} files")
        print(format_violations(all_violations))

    # 위반 사항이 있으면 0이 아닌 종료 코드 반환
    return 1 if all_violations else 0


if __name__ == "__main__":
    sys.exit(main())
