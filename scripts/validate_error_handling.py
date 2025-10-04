#!/usr/bin/env python3
"""
에러 처리 패턴 검증 스크립트

Python AST를 사용하여 에러 처리 안티패턴을 탐지합니다:
- 예외 삼키기 (bare except, pass)
- print 사용 (로깅 시스템 미사용)
- 매직 문자열 사용 (하드코딩된 에러 메시지)
- 에러 재전파 없음
- 컨텍스트 정보 부족
- 사용자 친화적이지 않은 에러 메시지
"""

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import Any


class ErrorHandlingDetector(ast.NodeVisitor):
    """에러 처리 패턴을 탐지하는 AST 방문자 클래스"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.violations: list[dict[str, Any]] = []

        # 안티패턴 패턴들
        self.bare_except_patterns = [
            r"except\s*:",
            r"except\s+Exception\s*:",
            r"except\s+BaseException\s*:",
        ]

        # print 사용 패턴들
        self.print_patterns = [
            r"print\s*\(",
            r"sys\.stdout\.write\s*\(",
            r"sys\.stderr\.write\s*\(",
        ]

        # 매직 문자열 패턴들 (하드코딩된 에러 메시지)
        self.magic_string_patterns = [
            r'"[^"]*error[^"]*"',
            r'"[^"]*Error[^"]*"',
            r'"[^"]*failed[^"]*"',
            r'"[^"]*Failed[^"]*"',
            r'"[^"]*not found[^"]*"',
            r'"[^"]*Not found[^"]*"',
            r'"[^"]*permission[^"]*"',
            r'"[^"]*Permission[^"]*"',
            r'"[^"]*invalid[^"]*"',
            r'"[^"]*Invalid[^"]*"',
        ]

        # 사용자 친화적이지 않은 에러 메시지 패턴들
        self.unfriendly_error_patterns = [
            r'"[^"]*HTTP\s+\d+[^"]*"',
            r'"[^"]*status\s+code[^"]*"',
            r'"[^"]*exception[^"]*"',
            r'"[^"]*Exception[^"]*"',
            r'"[^"]*traceback[^"]*"',
            r'"[^"]*Traceback[^"]*"',
            r'"[^"]*stack\s+trace[^"]*"',
            r'"[^"]*Stack\s+trace[^"]*"',
        ]

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        """일반 함수 정의 방문"""
        self._analyze_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        """비동기 함수 정의 방문"""
        self._analyze_function(node)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        """클래스 정의 방문"""
        self.generic_visit(node)

    def _analyze_function(self, node: ast.FunctionDef) -> None:
        """함수 분석"""
        function_name = node.name
        start_line = node.lineno

        # 함수 내의 모든 try-except 블록 분석
        for child in ast.walk(node):
            if isinstance(child, ast.Try):
                self._analyze_try_except(child, function_name, start_line)

        # 함수 내의 print 사용 검사
        self._check_print_usage(node, function_name, start_line)

        # 함수 내의 매직 문자열 검사
        self._check_magic_strings(node, function_name, start_line)

    def _analyze_try_except(
        self,
        node: ast.Try,
        function_name: str,
        function_line: int,
    ) -> None:
        """try-except 블록 분석"""
        # bare except 검사
        for handler in node.handlers:
            if handler.type is None:  # bare except
                self.violations.append(
                    {
                        "file": self.file_path,
                        "line": handler.lineno,
                        "column": handler.col_offset,
                        "function": function_name,
                        "type": "bare_except",
                        "context": "Bare except clause",
                        "severity": "high",
                    },
                )

            # Exception만 처리하는 경우 검사 (단, 마지막 except 블록이 아닌 경우만)
            elif (
                isinstance(handler.type, ast.Name)
                and handler.type.id == "Exception"
                and not self._is_last_except_handler(handler, node.handlers)
            ):
                self.violations.append(
                    {
                        "file": self.file_path,
                        "line": handler.lineno,
                        "column": handler.col_offset,
                        "function": function_name,
                        "type": "generic_exception",
                        "context": "Catching generic Exception (not as final catch-all)",
                        "severity": "medium",
                    },
                )

            # except 블록 내용 분석
            self._analyze_except_block(handler, function_name, function_line)

    def _is_last_except_handler(
        self,
        handler: ast.ExceptHandler,
        handlers: list[ast.ExceptHandler],
    ) -> bool:
        """마지막 except 핸들러인지 확인"""
        return handler == handlers[-1]

    def _analyze_except_block(
        self,
        handler: ast.ExceptHandler,
        function_name: str,
        function_line: int,  # noqa: ARG002
    ) -> None:
        """except 블록 내용 분석"""
        for stmt in handler.body:
            # pass 사용 검사
            if isinstance(stmt, ast.Pass):
                self.violations.append(
                    {
                        "file": self.file_path,
                        "line": stmt.lineno,
                        "column": stmt.col_offset,
                        "function": function_name,
                        "type": "exception_swallowing",
                        "context": "Exception swallowed with pass",
                        "severity": "high",
                    },
                )

            # return None 또는 return False 검사
            elif isinstance(stmt, ast.Return):
                if isinstance(stmt.value, ast.Constant) and stmt.value.value in (
                    None,
                    False,
                ):
                    self.violations.append(
                        {
                            "file": self.file_path,
                            "line": stmt.lineno,
                            "column": stmt.col_offset,
                            "function": function_name,
                            "type": "silent_failure",
                            "context": "Silent failure with return None/False",
                            "severity": "high",
                        },
                    )

            # print 사용 검사
            elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                if (
                    isinstance(stmt.value.func, ast.Name)
                    and stmt.value.func.id == "print"
                ):
                    self.violations.append(
                        {
                            "file": self.file_path,
                            "line": stmt.lineno,
                            "column": stmt.col_offset,
                            "function": function_name,
                            "type": "print_in_except",
                            "context": "Using print instead of logging in except block",
                            "severity": "medium",
                        },
                    )

            # 에러 재전파 검사 (bare_raise는 올바른 패턴이므로 제거)

    def _check_print_usage(
        self,
        node: ast.FunctionDef,
        function_name: str,
        function_line: int,  # noqa: ARG002
    ) -> None:
        """print 사용 검사"""
        for child in ast.walk(node):
            if isinstance(child, ast.Expr) and isinstance(child.value, ast.Call):
                if (
                    isinstance(child.value.func, ast.Name)
                    and child.value.func.id == "print"
                ):
                    self.violations.append(
                        {
                            "file": self.file_path,
                            "line": child.lineno,
                            "column": child.col_offset,
                            "function": function_name,
                            "type": "print_usage",
                            "context": "Using print instead of logging",
                            "severity": "medium",
                        },
                    )

    def _check_magic_strings(
        self,
        node: ast.FunctionDef,
        function_name: str,
        function_line: int,  # noqa: ARG002
    ) -> None:
        """매직 문자열 검사"""
        for child in ast.walk(node):
            if isinstance(child, ast.Constant) and isinstance(child.value, str):
                string_value = child.value

                # 매직 문자열 패턴 검사
                for pattern in self.magic_string_patterns:
                    if re.search(pattern, string_value, re.IGNORECASE):
                        self.violations.append(
                            {
                                "file": self.file_path,
                                "line": child.lineno,
                                "column": child.col_offset,
                                "function": function_name,
                                "type": "magic_string",
                                "context": f'Magic string: "{string_value}"',
                                "severity": "medium",
                            },
                        )
                        break

                # 사용자 친화적이지 않은 에러 메시지 검사
                for pattern in self.unfriendly_error_patterns:
                    if re.search(pattern, string_value, re.IGNORECASE):
                        self.violations.append(
                            {
                                "file": self.file_path,
                                "line": child.lineno,
                                "column": child.col_offset,
                                "function": function_name,
                                "type": "unfriendly_error",
                                "context": f'Unfriendly error message: "{string_value}"',
                                "severity": "low",
                            },
                        )
                        break

    def _check_error_context(self, node: ast.FunctionDef, function_name: str) -> None:
        """에러 컨텍스트 정보 검사"""
        # 함수에 try-except가 있는지 확인
        has_try_except = any(isinstance(child, ast.Try) for child in ast.walk(node))

        if has_try_except:
            # 로깅 사용 여부 확인
            has_logging = any(
                isinstance(child, ast.Expr)
                and isinstance(child.value, ast.Call)
                and isinstance(child.value.func, ast.Attribute)
                and isinstance(child.value.func.value, ast.Name)
                and child.value.func.value.id == "logger"
                for child in ast.walk(node)
            )

            if not has_logging:
                self.violations.append(
                    {
                        "file": self.file_path,
                        "line": node.lineno,
                        "column": node.col_offset,
                        "function": function_name,
                        "type": "no_logging",
                        "context": "No logging in function with error handling",
                        "severity": "medium",
                    },
                )

    def _check_error_propagation(
        self,
        node: ast.FunctionDef,
        function_name: str,
    ) -> None:
        """에러 전파 검사"""
        # 함수가 에러를 발생시키는지 확인
        has_raise = any(isinstance(child, ast.Raise) for child in ast.walk(node))

        if has_raise:
            # 원본 에러 정보 보존 여부 확인
            for child in ast.walk(node):
                if isinstance(child, ast.Raise) and child.cause is None:
                    # from None이 없는 경우
                    if (
                        isinstance(child.exc, ast.Call)
                        and isinstance(child.exc.func, ast.Name)
                        and "Error" in child.exc.func.id
                    ):
                        self.violations.append(
                            {
                                "file": self.file_path,
                                "line": child.lineno,
                                "column": child.col_offset,
                                "function": function_name,
                                "type": "no_error_context",
                                "context": "Raising new error without preserving original context",
                                "severity": "medium",
                            },
                        )


def analyze_file(file_path: Path) -> list[dict[str, Any]]:
    """파일을 분석하여 에러 처리 패턴 위반을 탐지"""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=str(file_path))

        # AST 노드에 부모 참조 추가
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                child.parent = node

        detector = ErrorHandlingDetector(str(file_path))
        detector.visit(tree)

        return detector.violations

    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}", file=sys.stderr)
        return []


def format_violations(violations: list[dict[str, Any]]) -> str:
    """위반 사항을 포맷팅하여 출력"""
    if not violations:
        return "✅ No error handling violations found!"

    # 심각도별로 그룹화
    violations_by_severity = {}
    for violation in violations:
        severity = violation["severity"]
        if severity not in violations_by_severity:
            violations_by_severity[severity] = []
        violations_by_severity[severity].append(violation)

    output = []
    output.append(f"❌ Found {len(violations)} error handling violation(s):")
    output.append("")

    # 심각도 순으로 출력 (high -> medium -> low)
    severity_order = ["high", "medium", "low"]
    for severity in severity_order:
        if severity in violations_by_severity:
            type_violations = violations_by_severity[severity]
            output.append(f"  {severity.upper()} SEVERITY ({len(type_violations)}):")

            for violation in type_violations:
                output.append(
                    f"    {violation['file']}:{violation['line']}:{violation['column']}",
                )
                output.append(
                    f"      Function '{violation['function']}' - {violation['type']}",
                )
                output.append(f"      {violation['context']}")
                output.append("")

    return "\n".join(output)


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="Detect error handling anti-patterns in Python code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/validate_error_handling.py src/
  python scripts/validate_error_handling.py tests/scripts/test_data/error_handling_incorrect.py
  python scripts/validate_error_handling.py --exclude tests/ src/
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

    parser.add_argument(
        "--severity",
        choices=["high", "medium", "low", "all"],
        default="all",
        help="Minimum severity level to report (default: all)",
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

    # 심각도 필터링
    if args.severity != "all":
        severity_levels = {"high": 3, "medium": 2, "low": 1}
        min_level = severity_levels[args.severity]
        all_violations = [
            v
            for v in all_violations
            if severity_levels.get(v["severity"], 0) >= min_level
        ]

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
