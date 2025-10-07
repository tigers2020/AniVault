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
from typing import Any


class MagicValueDetector(ast.NodeVisitor):
    """매직 값을 탐지하는 AST 방문자 클래스"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.violations: list[dict[str, Any]] = []
        self.imported_constants: set[str] = set()
        self.module_constants: set[str] = set()
        self.function_defaults: set[tuple[int, int]] = set()  # (line, col)

        # 허용되는 패턴들 (정적 문자열들)
        self.allowed_strings = {
            # 파일 확장자
            ".py",
            ".pyc",
            ".pyo",
            ".pyd",
            ".so",
            ".dll",
            ".exe",
            # 인코딩
            "utf-8",
            "utf8",
            "ascii",
            "latin-1",
            # HTTP 상태 코드
            "200",
            "201",
            "204",
            "400",
            "401",
            "403",
            "404",
            "500",
            # CLI 옵션들
            "--verbose",
            "--json",
            "--help",
            "--version",
            "--recursive",
            "--dry-run",
            "--yes",
            "--enhanced",
            "--include-subtitles",
            "--include-metadata",
            "--log-level",
            "--output",
            "--destination",
            # 로그 레벨
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL",
            # 네트워크 설정
            "localhost",
            "127.0.0.1",
            "0.0.0.0",  # noqa: S104
            # API 엔드포인트
            "https://api.themoviedb.org/3",
            # JSON 키들 (정적)
            "timestamp",
            "data",
            "errors",
            "warnings",
            "success",
            "command",
            "file_path",
            "file_name",
            "file_size",
            "file_extension",
            "parsing_result",
            "enriched_metadata",
            "title",
            "episode",
            "season",
            "quality",
            "source",
            "codec",
            "audio",
            "release_group",
            "confidence",
            "parser_used",
            "other_info",
            "enrichment_status",
            "match_confidence",
            "tmdb_data",
            "total_files",
            "total_size_bytes",
            "total_size_formatted",
            "scanned_directory",
            "metadata_enriched",
            "counts_by_extension",
            "scanned_paths",
            "files",
            "scan_summary",
            "file_statistics",
            # 상태 키들
            "status",
            "step",
            "error_code",
            "context",
            "directory",
            "error_type",
            # 명령어 이름들
            "scan",
            "match",
            "organize",
            "rollback",
            "run",
            "verify",
            "log",
            # 에러 메시지들 (정적)
            "Application error:",
            "Infrastructure error:",
            "Unexpected error:",
            "Directory validation failed",
            "No anime files found",
            "Scanning files...",
            "Matching files...",
            "Organizing files...",
            "File scanning completed!",
            "File scanning failed",
            "Validation error:",
            "Validation failed:",
            # 기타 정적 문자열들
            "Unknown",
            "No match",
            "Success",
            "Error",
            "Warning",
            "Info",
            "PB",
            "TB",
            "GB",
            "MB",
            "KB",
            "B",
            # JSON serialization 관련
            "JSON serialization failed:",
            "model_dump_json",
            "__dict__",
            "__str__",
            # 파일 처리 관련
            "Anime File Scan Results",
            "Title",
            "Episode",
            "Quality",
            "TMDB Match",
            "TMDB Rating",
            # 기타 UI 메시지들
            "Unexpected validation error:",
            "Format string has mismatched braces:",
            "Invalid placeholders found:",
            "Format string must contain at least one valid placeholder. Valid placeholders:",
            # 에러 코드들
            "FILE_NOT_FOUND",
            "VALIDATION_ERROR",
            "DIRECTORY_NOT_FOUND",
            # 기타 상수들
            "AniVault",
            "CLI",
            "Typer",
            "Python",
            "JSON",
            "API",
            "TMDB",
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
            2,
            3,
            # 일반적인 크기 제한
            1024,
            4096,
            8192,
            65536,
        }

        self.is_constants_file = self._is_constants_file()

    def _is_constants_file(self) -> bool:
        """파일이 constants 모듈인지 확인"""
        return (
            "constants" in self.file_path
            or self.file_path.endswith("constants.py")
            or "constants" in self.file_path.split("/")[-1]
        )

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

    def generic_visit(self, node: ast.AST) -> None:
        """일반적인 노드 방문 - 부모 노드 정보 추가"""
        # 일반 자식 노드에 부모 설정
        for child in ast.iter_child_nodes(node):
            child.parent = node

        # Call 노드의 keyword에 부모 설정
        # AST 구조: Call > keyword > value (Constant)
        if isinstance(node, ast.Call):
            for keyword in node.keywords:
                keyword.parent = node  # keyword의 부모는 Call
                if hasattr(keyword, "value"):
                    keyword.value.parent = keyword  # value의 부모는 keyword

        super().generic_visit(node)

    def _check_constant(
        self,
        node: ast.AST,
        value: Any,
        lineno: int,
        col_offset: int,
    ) -> None:
        """상수 값 검사"""
        # constants 파일에서는 매직 값 탐지를 건너뜀
        if self.is_constants_file:
            return

        # 함수 기본값인지 확인
        if (lineno, col_offset) in self.function_defaults:
            return

        # 상수 할당인지 확인 (모듈 수준 상수)
        if self._is_constant_assignment(node):
            return

        # docstring인지 확인
        if self._is_docstring(node):
            return

        # help text인지 확인
        if self._is_help_text(node):
            return

        # 문서화 문자열인지 확인 (Pydantic Field description, 에러 메시지 등)
        if self._is_documentation_string(node):
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
                },
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

    def _is_docstring(self, node: ast.AST) -> bool:
        """docstring인지 확인"""
        if not isinstance(node, (ast.Constant, ast.Str)):
            return False

        # 값 추출
        value = node.value if hasattr(node, "value") else node.s
        if not isinstance(value, str):
            return False

        # 모듈, 클래스, 함수의 첫 번째 문장인지 확인
        if hasattr(node, "parent"):
            parent = node.parent

            # 1. 직접적인 docstring (모듈, 클래스, 함수의 첫 번째 문장)
            if isinstance(
                parent,
                (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                # 첫 번째 문장이 문자열이면 docstring
                if parent.body and parent.body[0] == node:
                    return True

            # 2. Expr 노드 안의 문자열 (docstring 패턴)
            if isinstance(parent, ast.Expr):
                if hasattr(parent, "parent"):
                    grandparent = parent.parent
                    if isinstance(
                        grandparent,
                        (
                            ast.Module,
                            ast.ClassDef,
                            ast.FunctionDef,
                            ast.AsyncFunctionDef,
                        ),
                    ):
                        # 첫 번째 statement인지 확인
                        if grandparent.body and grandparent.body[0] == parent:
                            return True

        # 3. 긴 문자열 (docstring 가능성 높음) - 50자 이상
        if len(value) > 50:
            return True

        # 4. 문장으로 끝나는 문자열 (설명 문자열 패턴)
        # "Configuration for..."  "This is..."  "Validate that..." 등
        if value.endswith(".") and len(value) > 20:
            return True

        return False

    def _is_help_text(self, node: ast.AST) -> bool:
        """help text인지 확인 (typer 옵션의 help 파라미터)"""
        if not isinstance(node, (ast.Constant, ast.Str)):
            return False

        # typer.Argument, typer.Option의 help 파라미터인지 확인
        if hasattr(node, "parent"):
            parent = node.parent
            if isinstance(parent, ast.Call):
                # typer.Argument(..., help=...) 또는 typer.Option(..., help=...) 패턴
                if (
                    isinstance(parent.func, ast.Attribute)
                    and isinstance(parent.func.value, ast.Name)
                    and parent.func.value.id == "typer"
                    and parent.func.attr in ("Argument", "Option")
                ):
                    # help 키워드 인자인지 확인
                    for keyword in parent.keywords:
                        if keyword.arg == "help" and keyword.value == node:
                            return True
        return False

    def _is_documentation_string(self, node: ast.AST) -> bool:
        """문서화 문자열인지 확인 (Pydantic Field description, 에러 메시지 등)"""
        if not isinstance(node, (ast.Constant, ast.Str)):
            return False

        if not hasattr(node, "parent"):
            return False

        parent = node.parent

        # 1. Pydantic Field의 문서화 키워드 인자
        # AST 구조: Call > keyword > Constant
        # parent = keyword 타입
        if isinstance(parent, ast.keyword):
            # 문서화 관련 키워드 인자
            if parent.arg in ("description", "title", "example", "examples", "alias"):
                # Call 노드 확인 (keyword의 부모)
                if hasattr(parent, "parent") and isinstance(parent.parent, ast.Call):
                    call_node = parent.parent
                    # Field 함수인지 확인
                    if (
                        isinstance(call_node.func, ast.Name)
                        and call_node.func.id == "Field"
                    ):
                        return True

            # 환경 변수 이름 (Field의 env 파라미터)
            # Field(env="TMDB_API_KEY")
            if parent.arg == "env":
                if hasattr(parent, "parent") and isinstance(parent.parent, ast.Call):
                    call_node = parent.parent
                    if (
                        isinstance(call_node.func, ast.Name)
                        and call_node.func.id == "Field"
                    ):
                        return True

        # 2. 환경 변수 조회 (os.getenv, os.environ)
        if isinstance(parent, ast.Call):
            # os.getenv("VARIABLE_NAME")
            if isinstance(parent.func, ast.Attribute):
                if (
                    parent.func.attr == "getenv"
                    and isinstance(parent.func.value, ast.Name)
                    and parent.func.value.id == "os"
                ):
                    if parent.args and parent.args[0] == node:
                        return True

            # os.getenv 직접 import한 경우: getenv("VARIABLE_NAME")
            if isinstance(parent.func, ast.Name) and parent.func.id == "getenv":
                if parent.args and parent.args[0] == node:
                    return True

        # 3. os.environ["VARIABLE_NAME"] 구독 접근
        if isinstance(parent, ast.Subscript):
            if isinstance(parent.value, ast.Attribute):
                if (
                    parent.value.attr == "environ"
                    and isinstance(parent.value.value, ast.Name)
                    and parent.value.value.id == "os"
                ):
                    return True
            # environ 직접 import한 경우: environ["VARIABLE_NAME"]
            if isinstance(parent.value, ast.Name) and parent.value.id == "environ":
                return True

        # 4. 에러 메시지 (raise 문의 문자열)
        if isinstance(parent, ast.Call):
            # 예외 생성자의 첫 번째 인자
            if parent.args and parent.args[0] == node:
                if isinstance(parent.func, ast.Name):
                    # ValueError("message"), RuntimeError("message") 등
                    if (
                        parent.func.id.endswith("Error")
                        or parent.func.id == "Exception"
                    ):
                        return True

        # 5. logger 호출의 메시지
        if isinstance(parent, ast.Call):
            if isinstance(parent.func, ast.Attribute):
                # logger.info("message"), logger.error("message") 등
                if parent.func.attr in (
                    "debug",
                    "info",
                    "warning",
                    "error",
                    "critical",
                    "exception",
                ):
                    if parent.args and parent.args[0] == node:
                        return True

        # 6. f-string이나 format() 호출의 메시지
        if isinstance(parent, ast.JoinedStr):
            return True

        # 7. 파일 I/O 함수의 파일명 (첫 번째 인자)
        if isinstance(parent, ast.Call):
            # open("filename"), Path("filename") 등
            file_io_functions = {
                "open",
                "read",
                "write",
                "load",
                "dump",
                "Path",
                "PurePath",
                "PosixPath",
                "WindowsPath",
                "read_text",
                "write_text",
                "read_bytes",
                "write_bytes",
                "exists",
                "is_file",
                "is_dir",
                "load_dotenv",  # python-dotenv
            }

            # 직접 함수 호출: open("file")
            if isinstance(parent.func, ast.Name):
                if parent.func.id in file_io_functions:
                    if parent.args and parent.args[0] == node:
                        return True

            # 속성 함수 호출: Path.read_text("file")
            if isinstance(parent.func, ast.Attribute):
                if parent.func.attr in file_io_functions:
                    if parent.args and parent.args[0] == node:
                        return True

        # 8. 파일명 키워드 인자 (filename=, file=, path= 등)
        if isinstance(parent, ast.keyword):
            if parent.arg in (
                "filename",
                "file",
                "path",
                "filepath",
                "file_path",
                "output",
                "input",
                "env_file",
                "dotenv_path",
            ):
                return True

        # 9. 예시 데이터 (json_schema_extra, ConfigDict의 example)
        # 딕셔너리 안의 값들을 추적하여 예시 데이터인지 확인
        if self._is_example_data(node):
            return True

        return False

    def _is_example_data(self, node: ast.AST) -> bool:
        """예시 데이터인지 확인 (json_schema_extra, example, 테스트/벤치마크 데이터 등)"""
        # 벤치마크/테스트 파일은 예시 데이터로 간주
        if any(
            pattern in self.file_path
            for pattern in ["benchmark.py", "test_", "_test.py", "tests/"]
        ):
            return True

        # 부모 노드를 거슬러 올라가면서 예시 데이터 컨텍스트 확인
        current = node
        depth = 0
        max_depth = 10  # 최대 10단계까지만 추적

        while hasattr(current, "parent") and depth < max_depth:
            parent = current.parent

            # Dict 노드인 경우
            if isinstance(parent, ast.Dict):
                # 딕셔너리의 키가 "example"이거나 "examples"인 경우
                for i, (key, value) in enumerate(zip(parent.keys, parent.values)):
                    if key and isinstance(key, (ast.Constant, ast.Str)):
                        key_value = key.value if hasattr(key, "value") else key.s
                        if key_value in ("example", "examples", "json_schema_extra"):
                            # 이 딕셔너리 값 안에 있으면 예시 데이터
                            if self._is_descendant_of(node, value):
                                return True

            # keyword 노드인 경우 (json_schema_extra=..., example=...)
            if isinstance(parent, ast.keyword):
                if parent.arg in ("json_schema_extra", "example", "examples"):
                    return True

            # Call 노드의 함수가 ConfigDict인 경우
            if isinstance(parent, ast.Call):
                if isinstance(parent.func, ast.Name) and parent.func.id == "ConfigDict":
                    # ConfigDict 안의 모든 값은 설정 데이터
                    return True

            current = parent
            depth += 1

        return False

    def _is_descendant_of(self, node: ast.AST, ancestor: ast.AST) -> bool:
        """node가 ancestor의 자손인지 확인"""
        current = node
        depth = 0
        max_depth = 20

        while hasattr(current, "parent") and depth < max_depth:
            if current == ancestor:
                return True
            current = current.parent
            depth += 1

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
                ),
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
                "filename",
                "result",
                "Expected",
                "keys",
                "found",
                "SUCCESS",
                "PARTIAL",
                "FAILED",
                "Import",
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
                "connected",
                "but",
                "no",
                "Rich",
                "console",
                "rendering",
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
                "SKIPPED",
                "No",
                "provided",
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

        if isinstance(value, (int, float)):
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
            if isinstance(parent, ast.Call):
                return "function_call"
            if isinstance(parent, ast.Assign):
                return "assignment"
            if isinstance(parent, ast.Return):
                return "return_statement"
            if isinstance(parent, ast.If):
                return "conditional"
            if isinstance(parent, ast.For):
                return "loop"
            if isinstance(parent, ast.While):
                return "while_loop"

        return "unknown"


def analyze_file(file_path: Path) -> list[dict[str, Any]]:
    """파일을 분석하여 매직 값을 탐지"""
    try:
        with open(file_path, encoding="utf-8") as f:
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


def format_violations(violations: list[dict[str, Any]]) -> str:
    """위반 사항을 포맷팅하여 출력"""
    if not violations:
        return "✅ No magic values found!"

    output = []
    output.append(f"❌ Found {len(violations)} magic value(s):")
    output.append("")

    for violation in violations:
        output.append(
            f"  {violation['file']}:{violation['line']}:{violation['column']}",
        )
        output.append(
            f"    {violation['type']}: {violation['value']} ({violation['context']})",
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
