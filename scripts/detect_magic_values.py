#!/usr/bin/env python3
"""Magic Value Detection Script for Pre-commit Hook.

Detects hardcoded magic values that should be replaced with constants.
"""

import re
import sys
from typing import ClassVar


class MagicValueDetector:
    """Detects magic values in Python code."""

    # Patterns for magic values that should be constants
    MAGIC_PATTERNS: ClassVar[list] = [
        # Status strings
        (
            r'["\'](?:pending|processing|completed|failed|error|success|approved|rejected)["\']',
            "Status string",
        ),
        (r'["\'](?:true|false|null|undefined|none)["\']', "Boolean/Null string"),
        # File extensions
        (
            r'["\']\.(?:py|js|ts|json|yaml|yml|md|txt|log|ini|cfg|conf)["\']',
            "File extension",
        ),
        (r'["\']\.(?:mkv|mp4|avi|mov|wmv|flv|webm|m4v)["\']', "Media file extension"),
        # HTTP status codes
        (
            r"\b(?:200|201|204|400|401|403|404|422|500|502|503|504)\b",
            "HTTP status code",
        ),
        # Time values (seconds)
        (r"\b(?:30|60|300|600|3600|86400)\b", "Time value (seconds)"),
        # File sizes (bytes)
        (r"\b(?:1024|1048576|1073741824|10485760)\b", "File size (bytes)"),
        # API limits
        (r"\b(?:10|20|50|100|1000)\b", "API limit value"),
        # Default ports
        (r"\b(?:80|443|8080|3000|5000|8000|9000)\b", "Default port"),
        # Common error codes
        (r"\b(?:0|1|-1)\b", "Error code"),
    ]

    def __init__(self):
        self.violations = []

    def check_file(self, file_path: str) -> list[tuple[int, str, str]]:
        """Check a file for magic values."""
        violations = []

        if not file_path.endswith(".py"):
            return violations

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                lines = content.splitlines()

            for line_num, line in enumerate(lines, 1):
                for pattern, description in self.MAGIC_PATTERNS:
                    matches = list(re.finditer(pattern, line, re.IGNORECASE))

                    for match in matches:
                        # Skip if it's in a comment or string literal
                        if self._is_in_comment_or_string(line, match.start()):
                            continue

                        # Skip if it's in a test file and not critical
                        if file_path.startswith("test") and description in [
                            "API limit value",
                            "Time value",
                        ]:
                            continue

                        violations.append((line_num, description, match.group()))

        except Exception as e:
            print(f"Error checking {file_path}: {e}")

        return violations

    def _is_in_comment_or_string(self, line: str, pos: int) -> bool:
        """Check if position is in a comment or string literal."""
        # Simple heuristic - look for quotes or # before the position
        before_pos = line[:pos]

        # Count unescaped quotes
        in_string = False
        escape_next = False

        for i, char in enumerate(before_pos):  # noqa: B007
            if escape_next:
                escape_next = False
                continue

            if char == "\\":
                escape_next = True
                continue

            if char in ['"', "'"]:
                in_string = not in_string

        # Check for comment
        if "#" in before_pos and not in_string:
            return True

        return in_string


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: detect_magic_values.py <file1> [file2] ...")
        sys.exit(1)

    file_paths = sys.argv[1:]
    detector = MagicValueDetector()

    total_violations = 0

    for file_path in file_paths:
        violations = detector.check_file(file_path)

        if violations:
            print(f"\n📋 {file_path}:")
            for line_num, description, value in violations:
                print(f"   Line {line_num}: {description} - '{value}'")
                total_violations += 1

    if total_violations > 0:
        print(f"\n⚠️  Found {total_violations} magic values")
        print("   Consider replacing with constants from anivault.shared.constants")
        sys.exit(1)

    print("✅ No magic values detected")


if __name__ == "__main__":
    main()
