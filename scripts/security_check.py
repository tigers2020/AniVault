#!/usr/bin/env python3
"""AI Security Validation Script for Pre-commit Hook.

This script performs security checks to prevent AI-generated vulnerabilities:
- Prompt injection patterns
- Unsafe code patterns
- Magic values and hardcoded secrets
- Unsafe imports and dependencies
"""

import ast
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


class SecurityViolation:
    """Represents a security violation found in code."""

    def __init__(
        self, file_path: str, line: int, severity: str, message: str, pattern: str = ""
    ):
        self.file_path = file_path
        self.line = line
        self.severity = severity
        self.message = message
        self.pattern = pattern

    def __str__(self) -> str:
        return f"{self.file_path}:{self.line} [{self.severity}] {self.message}"


class AISecurityChecker:
    """AI Security Checker for detecting vulnerable patterns."""

    # Dangerous patterns that could be exploited via prompt injection
    DANGEROUS_PATTERNS = [
        # Code execution patterns
        (
            r"\beval\s*\(",
            "CRITICAL",
            "eval() usage detected - potential code injection",
        ),
        (
            r"\bexec\s*\(",
            "CRITICAL",
            "exec() usage detected - potential code injection",
        ),
        (
            r"__import__\s*\(",
            "CRITICAL",
            "__import__() usage detected - dynamic import risk",
        ),
        (r"compile\s*\(", "HIGH", "compile() usage detected - code compilation risk"),
        # Subprocess patterns
        (
            r"subprocess\.run\s*\(",
            "HIGH",
            "subprocess.run() usage - review for shell injection",
        ),
        (
            r"subprocess\.call\s*\(",
            "HIGH",
            "subprocess.call() usage - review for shell injection",
        ),
        (
            r"os\.system\s*\(",
            "CRITICAL",
            "os.system() usage detected - shell injection risk",
        ),
        (r"os\.popen\s*\(", "HIGH", "os.popen() usage detected - shell injection risk"),
        # File system patterns
        (r"os\.remove\s*\(", "MEDIUM", "os.remove() usage - use safe file operations"),
        (r"os\.unlink\s*\(", "MEDIUM", "os.unlink() usage - use safe file operations"),
        (
            r"shutil\.rmtree\s*\(",
            "HIGH",
            "shutil.rmtree() usage - destructive operation",
        ),
        # Pickle/Marshal patterns
        (
            r"pickle\.loads?\s*\(",
            "CRITICAL",
            "pickle usage detected - deserialization risk",
        ),
        (
            r"marshal\.loads?\s*\(",
            "CRITICAL",
            "marshal usage detected - deserialization risk",
        ),
        (r"\.loads?\s*\(", "MEDIUM", "Potential deserialization - review for safety"),
        # Network patterns
        (
            r"requests\.get\s*\(",
            "MEDIUM",
            "requests.get() usage - review for SSRF protection",
        ),
        (
            r"requests\.post\s*\(",
            "MEDIUM",
            "requests.post() usage - review for SSRF protection",
        ),
        (
            r"urllib\.request\.urlopen\s*\(",
            "MEDIUM",
            "urllib usage - review for SSRF protection",
        ),
        # SQL patterns
        (
            r"execute\s*\(.*%",
            "HIGH",
            "SQL query with string formatting - potential SQL injection",
        ),
        (
            r"execute\s*\(.*\+",
            "HIGH",
            "SQL query with string concatenation - potential SQL injection",
        ),
    ]

    # Magic value patterns (hardcoded strings/numbers)
    MAGIC_PATTERNS = [
        # Status strings
        (
            r'["\'](?:pending|processing|completed|failed|error|success)["\']',
            "MEDIUM",
            "Magic status string - use constants",
        ),
        (
            r'["\'](?:true|false|null|undefined)["\']',
            "LOW",
            "Magic boolean/null string - use constants",
        ),
        # File extensions
        (
            r'["\']\.(?:py|js|ts|json|yaml|yml|md|txt)["\']',
            "LOW",
            "Magic file extension - use constants",
        ),
        # HTTP status codes
        (
            r"\b(?:200|201|400|401|403|404|500|502|503)\b",
            "LOW",
            "Magic HTTP status code - use constants",
        ),
        # Time values
        (r"\b(?:60|300|3600|86400)\b", "LOW", "Magic time value - use constants"),
        # File sizes
        (r"\b(?:1024|1048576|1073741824)\b", "LOW", "Magic file size - use constants"),
    ]

    # Secret patterns
    SECRET_PATTERNS = [
        (
            r'(?:api[_-]?key|secret|token|password|passwd|pwd)\s*[:=]\s*["\'][^"\']+["\']',
            "CRITICAL",
            "Potential hardcoded secret",
        ),
        (
            r"(?:sk-|pk_|AKIA|AIza)[a-zA-Z0-9]{20,}",
            "CRITICAL",
            "Potential API key pattern",
        ),
        (r'["\'][a-zA-Z0-9+/]{40,}["\']', "HIGH", "Potential base64 encoded secret"),
        (
            r'(?:password|passwd|pwd)\s*=\s*["\'][^"\']{8,}["\']',
            "HIGH",
            "Potential hardcoded password",
        ),
    ]

    def __init__(self):
        self.violations: List[SecurityViolation] = []

    def check_file(self, file_path: str) -> List[SecurityViolation]:
        """Check a single file for security violations."""
        violations = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.splitlines()

            # Check dangerous patterns
            violations.extend(self._check_dangerous_patterns(file_path, content, lines))

            # Check magic values
            violations.extend(self._check_magic_values(file_path, content, lines))

            # Check secrets
            violations.extend(self._check_secrets(file_path, content, lines))

            # Check AST for unsafe constructs
            violations.extend(self._check_ast(file_path, content))

        except Exception as e:
            violations.append(
                SecurityViolation(file_path, 0, "ERROR", f"Failed to analyze file: {e}")
            )

        return violations

    def _check_dangerous_patterns(
        self, file_path: str, content: str, lines: List[str]
    ) -> List[SecurityViolation]:
        """Check for dangerous code patterns."""
        violations = []

        for pattern, severity, message in self.DANGEROUS_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[: match.start()].count("\n") + 1
                violations.append(
                    SecurityViolation(file_path, line_num, severity, message, pattern)
                )

        return violations

    def _check_magic_values(
        self, file_path: str, content: str, lines: List[str]
    ) -> List[SecurityViolation]:
        """Check for magic values that should be constants."""
        violations = []

        for pattern, severity, message in self.MAGIC_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[: match.start()].count("\n") + 1
                violations.append(
                    SecurityViolation(file_path, line_num, severity, message, pattern)
                )

        return violations

    def _check_secrets(
        self, file_path: str, content: str, lines: List[str]
    ) -> List[SecurityViolation]:
        """Check for potential hardcoded secrets."""
        violations = []

        for pattern, severity, message in self.SECRET_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[: match.start()].count("\n") + 1
                violations.append(
                    SecurityViolation(file_path, line_num, severity, message, pattern)
                )

        return violations

    def _check_ast(self, file_path: str, content: str) -> List[SecurityViolation]:
        """Check AST for unsafe constructs."""
        violations = []

        if not file_path.endswith(".py"):
            return violations

        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                # Check for unsafe function calls
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id

                        if func_name in ["eval", "exec", "compile", "__import__"]:
                            violations.append(
                                SecurityViolation(
                                    file_path,
                                    node.lineno,
                                    "CRITICAL",
                                    f"Unsafe function call: {func_name}()",
                                )
                            )

                        elif func_name in ["system", "popen"]:
                            violations.append(
                                SecurityViolation(
                                    file_path,
                                    node.lineno,
                                    "HIGH",
                                    f"Unsafe os function: os.{func_name}()",
                                )
                            )

                # Check for bare except clauses
                elif isinstance(node, ast.ExceptHandler) and node.type is None:
                    violations.append(
                        SecurityViolation(
                            file_path,
                            node.lineno,
                            "MEDIUM",
                            "Bare except clause - specify exception types",
                        )
                    )

        except SyntaxError:
            # Skip files with syntax errors - they'll be caught by other tools
            pass

        return violations

    def check_files(self, file_paths: List[str]) -> List[SecurityViolation]:
        """Check multiple files for security violations."""
        all_violations = []

        for file_path in file_paths:
            violations = self.check_file(file_path)
            all_violations.extend(violations)

        return all_violations


def main():
    """Main function for pre-commit hook."""
    if len(sys.argv) < 2:
        print("Usage: security_check.py <file1> [file2] ...")
        sys.exit(1)

    file_paths = sys.argv[1:]
    checker = AISecurityChecker()

    # Filter out non-source files
    source_files = [
        f
        for f in file_paths
        if f.endswith((".py", ".js", ".ts", ".json", ".yaml", ".yml", ".md"))
    ]

    violations = checker.check_files(source_files)

    # Filter out violations in test files (different severity)
    critical_violations = [
        v
        for v in violations
        if v.severity == "CRITICAL" and not v.file_path.startswith("test")
    ]

    high_violations = [
        v
        for v in violations
        if v.severity == "HIGH" and not v.file_path.startswith("test")
    ]

    # Print violations
    for violation in sorted(
        violations, key=lambda v: (v.severity, v.file_path, v.line)
    ):
        print(violation)

    # Exit with error code if critical violations found
    if critical_violations or high_violations:
        print(f"\n🚨 Security violations found:")
        print(f"   Critical: {len(critical_violations)}")
        print(f"   High: {len(high_violations)}")
        print(f"   Total: {len(violations)}")
        sys.exit(1)

    print("✅ Security check passed")


if __name__ == "__main__":
    main()
