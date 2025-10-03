#!/usr/bin/env python3
"""
함수 길이 및 복잡도 검증 스크립트

Python AST를 사용하여 80줄을 초과하는 함수와 높은 복잡도를 가진 함수를 탐지합니다.
"""

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


class FunctionComplexityDetector(ast.NodeVisitor):
    """함수 길이 및 복잡도를 탐지하는 AST 방문자 클래스"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.violations: List[Dict[str, Any]] = []

        # 설정값
        self.max_function_length = 80
        self.max_complexity = 10
        self.max_parameters = 5

        # 복잡도 계산을 위한 노드 타입들
        self.complexity_nodes = {
            ast.If,
            ast.For,
            ast.While,
            ast.With,
            ast.BoolOp,
            ast.ListComp,
            ast.DictComp,
            ast.SetComp,
            ast.GeneratorExp,
            ast.Lambda,
            ast.ExceptHandler,
            ast.Assert,
        }

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """일반 함수 정의 방문"""
        self._analyze_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """비동기 함수 정의 방문"""
        self._analyze_function(node)
        self.generic_visit(node)

    def _analyze_function(self, node: ast.FunctionDef) -> None:
        """함수 분석"""
        function_name = node.name
        start_line = node.lineno
        end_line = getattr(node, "end_lineno", start_line)
        function_length = end_line - start_line + 1

        # 함수 길이 검사
        if function_length > self.max_function_length:
            self.violations.append(
                {
                    "file": self.file_path,
                    "line": start_line,
                    "column": node.col_offset,
                    "function": function_name,
                    "type": "length",
                    "value": function_length,
                    "threshold": self.max_function_length,
                    "context": self._get_function_context(node),
                }
            )

        # 매개변수 개수 검사
        param_count = len(node.args.args) + len(node.args.kwonlyargs)
        if param_count > self.max_parameters:
            self.violations.append(
                {
                    "file": self.file_path,
                    "line": start_line,
                    "column": node.col_offset,
                    "function": function_name,
                    "type": "parameters",
                    "value": param_count,
                    "threshold": self.max_parameters,
                    "context": self._get_function_context(node),
                }
            )

        # 복잡도 계산
        complexity = self._calculate_complexity(node)
        if complexity > self.max_complexity:
            self.violations.append(
                {
                    "file": self.file_path,
                    "line": start_line,
                    "column": node.col_offset,
                    "function": function_name,
                    "type": "complexity",
                    "value": complexity,
                    "threshold": self.max_complexity,
                    "context": self._get_function_context(node),
                }
            )

        # 혼재 책임 탐지
        responsibilities = self._detect_mixed_responsibilities(node)
        if len(responsibilities) > 1:
            self.violations.append(
                {
                    "file": self.file_path,
                    "line": start_line,
                    "column": node.col_offset,
                    "function": function_name,
                    "type": "mixed_responsibilities",
                    "value": responsibilities,
                    "threshold": 1,
                    "context": self._get_function_context(node),
                }
            )

    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """함수 복잡도 계산 (순환 복잡도)"""
        complexity = 1  # 기본 복잡도

        for child in ast.walk(node):
            if type(child) in self.complexity_nodes:
                complexity += 1

                # BoolOp의 경우 각 피연산자마다 +1
                if isinstance(child, ast.BoolOp):
                    complexity += len(child.values) - 1

        return complexity

    def _detect_mixed_responsibilities(self, node: ast.FunctionDef) -> Set[str]:
        """혼재된 책임 탐지"""
        responsibilities = set()

        for child in ast.walk(node):
            # UI 관련 코드 탐지
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    func_name = child.func.id.lower()
                    if any(
                        ui_keyword in func_name
                        for ui_keyword in [
                            "print",
                            "display",
                            "show",
                            "render",
                            "draw",
                            "paint",
                            "settext",
                            "setenabled",
                            "setvisible",
                            "setcolor",
                            "update",
                            "refresh",
                            "repaint",
                            "redraw",
                        ]
                    ):
                        responsibilities.add("UI")

            # 비즈니스 로직 관련 코드 탐지
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    func_name = child.func.id.lower()
                    if any(
                        business_keyword in func_name
                        for business_keyword in [
                            "calculate",
                            "compute",
                            "process",
                            "validate",
                            "verify",
                            "transform",
                            "convert",
                            "parse",
                            "format",
                            "normalize",
                            "filter",
                            "sort",
                            "search",
                            "find",
                            "match",
                        ]
                    ):
                        responsibilities.add("Business Logic")

            # I/O 관련 코드 탐지
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    if isinstance(child.func.value, ast.Name):
                        if child.func.value.id in ["open", "file", "os", "pathlib"]:
                            responsibilities.add("I/O")
                elif isinstance(child.func, ast.Name):
                    func_name = child.func.id.lower()
                    if any(
                        io_keyword in func_name
                        for io_keyword in [
                            "open",
                            "read",
                            "write",
                            "save",
                            "load",
                            "fetch",
                            "download",
                            "upload",
                            "send",
                            "receive",
                            "connect",
                        ]
                    ):
                        responsibilities.add("I/O")

            # 데이터베이스 관련 코드 탐지
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    if isinstance(child.func.value, ast.Name):
                        if child.func.value.id in ["db", "database", "sql", "query"]:
                            responsibilities.add("Database")
                elif isinstance(child.func, ast.Name):
                    func_name = child.func.id.lower()
                    if any(
                        db_keyword in func_name
                        for db_keyword in [
                            "insert",
                            "update",
                            "delete",
                            "select",
                            "query",
                            "execute",
                            "commit",
                            "rollback",
                            "transaction",
                        ]
                    ):
                        responsibilities.add("Database")

            # 네트워크 관련 코드 탐지
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    if isinstance(child.func.value, ast.Name):
                        if child.func.value.id in ["requests", "http", "url", "api"]:
                            responsibilities.add("Network")
                elif isinstance(child.func, ast.Name):
                    func_name = child.func.id.lower()
                    if any(
                        network_keyword in func_name
                        for network_keyword in [
                            "get",
                            "post",
                            "put",
                            "delete",
                            "patch",
                            "head",
                            "request",
                            "response",
                            "url",
                            "api",
                            "endpoint",
                        ]
                    ):
                        responsibilities.add("Network")

        return responsibilities

    def _get_function_context(self, node: ast.FunctionDef) -> str:
        """함수 컨텍스트 정보 추출"""
        # 함수가 클래스 내부에 있는지 확인
        if hasattr(node, "parent") and isinstance(node.parent, ast.ClassDef):
            return f"Method in class {node.parent.name}"

        # 함수의 독스트링 확인
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            docstring = node.body[0].value.value
            if len(docstring) > 50:
                return f"Function with long docstring ({len(docstring)} chars)"

        return "Function"

    def _get_function_signature(self, node: ast.FunctionDef) -> str:
        """함수 시그니처 추출"""
        args = []

        # 위치 인수
        for arg in node.args.args:
            args.append(arg.arg)

        # 키워드 전용 인수
        if node.args.kwonlyargs:
            for arg in node.args.kwonlyargs:
                args.append(f"*{arg.arg}")

        # 가변 인수
        if node.args.vararg:
            args.append(f"*{node.args.vararg.arg}")

        # 가변 키워드 인수
        if node.args.kwarg:
            args.append(f"**{node.args.kwarg.arg}")

        return f"{node.name}({', '.join(args)})"


def analyze_file(file_path: Path) -> List[Dict[str, Any]]:
    """파일을 분석하여 함수 길이 및 복잡도 위반을 탐지"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=str(file_path))

        # AST 노드에 부모 참조 추가
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                child.parent = node

        detector = FunctionComplexityDetector(str(file_path))
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
        return "✅ No function length/complexity violations found!"

    # 위반 유형별로 그룹화
    violations_by_type = {}
    for violation in violations:
        violation_type = violation["type"]
        if violation_type not in violations_by_type:
            violations_by_type[violation_type] = []
        violations_by_type[violation_type].append(violation)

    output = []
    output.append(f"❌ Found {len(violations)} function violation(s):")
    output.append("")

    for violation_type, type_violations in violations_by_type.items():
        output.append(
            f"  {violation_type.upper()} VIOLATIONS ({len(type_violations)}):"
        )

        for violation in type_violations:
            if violation_type == "length":
                output.append(
                    f"    {violation['file']}:{violation['line']}:{violation['column']}"
                )
                output.append(
                    f"      Function '{violation['function']}' is {violation['value']} lines long (max: {violation['threshold']})"
                )
            elif violation_type == "complexity":
                output.append(
                    f"    {violation['file']}:{violation['line']}:{violation['column']}"
                )
                output.append(
                    f"      Function '{violation['function']}' has complexity {violation['value']} (max: {violation['threshold']})"
                )
            elif violation_type == "parameters":
                output.append(
                    f"    {violation['file']}:{violation['line']}:{violation['column']}"
                )
                output.append(
                    f"      Function '{violation['function']}' has {violation['value']} parameters (max: {violation['threshold']})"
                )
            elif violation_type == "mixed_responsibilities":
                output.append(
                    f"    {violation['file']}:{violation['line']}:{violation['column']}"
                )
                output.append(
                    f"      Function '{violation['function']}' mixes responsibilities: {', '.join(violation['value'])}"
                )

            output.append(f"      Context: {violation['context']}")
            output.append("")

    return "\n".join(output)


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="Detect function length and complexity violations in Python code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/validate_function_length.py src/
  python scripts/validate_function_length.py tests/scripts/test_data/functions_long_complex.py
  python scripts/validate_function_length.py --max-length 100 --max-complexity 15 src/
        """,
    )

    parser.add_argument("paths", nargs="+", help="File or directory paths to analyze")

    parser.add_argument(
        "--exclude", nargs="*", default=[], help="Patterns to exclude from analysis"
    )

    parser.add_argument(
        "--max-length",
        type=int,
        default=80,
        help="Maximum function length (default: 80)",
    )

    parser.add_argument(
        "--max-complexity",
        type=int,
        default=10,
        help="Maximum function complexity (default: 10)",
    )

    parser.add_argument(
        "--max-parameters",
        type=int,
        default=5,
        help="Maximum number of parameters (default: 5)",
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
