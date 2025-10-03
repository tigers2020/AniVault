#!/usr/bin/env python3
"""Secret Exposure Check Script for Pre-commit Hook.

Detects potential secret exposure in configuration files and documentation.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


class SecretChecker:
    """Checks for potential secret exposure."""

    # Patterns for potential secrets
    SECRET_PATTERNS = [
        # API keys
        (r'(?:api[_-]?key|apikey)\s*[:=]\s*["\']?([^"\'\s\n]{20,})["\']?', "API Key"),
        (
            r'(?:secret|secret[_-]?key)\s*[:=]\s*["\']?([^"\'\s\n]{16,})["\']?',
            "Secret Key",
        ),
        (
            r'(?:token|access[_-]?token)\s*[:=]\s*["\']?([^"\'\s\n]{20,})["\']?',
            "Access Token",
        ),
        # Common API key patterns
        (r"(?:sk-|pk_|AKIA|AIza|ya29)[a-zA-Z0-9_-]{20,}", "API Key Pattern"),
        (r"[a-zA-Z0-9+/]{40,}={0,2}", "Base64 Encoded Secret"),
        # Passwords
        (r'(?:password|passwd|pwd)\s*[:=]\s*["\']([^"\'\s\n]{8,})["\']', "Password"),
        # Database credentials
        (
            r'(?:db[_-]?password|database[_-]?password)\s*[:=]\s*["\']([^"\'\s\n]{8,})["\']',
            "Database Password",
        ),
        # JWT tokens
        (r"eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+", "JWT Token"),
        # Private keys
        (r"-----BEGIN (?:RSA )?PRIVATE KEY-----", "Private Key"),
        # OAuth secrets
        (
            r'(?:client[_-]?secret|oauth[_-]?secret)\s*[:=]\s*["\']([^"\'\s\n]{16,})["\']',
            "OAuth Secret",
        ),
    ]

    # Allowed patterns (false positives)
    ALLOWED_PATTERNS = [
        r"test[_-]?key",
        r"example[_-]?key",
        r"sample[_-]?key",
        r"dummy[_-]?key",
        r"placeholder[_-]?key",
        r"your[_-]?.*[_-]?key",
        r"your[_-]?.*[_-]?secret",
        r"your[_-]?.*[_-]?token",
        r"YOUR_.*_HERE",
        r"<.*>",  # Template placeholders
        r"\[.*\]",  # Template placeholders
    ]

    def __init__(self):
        self.violations = []

    def check_file(self, file_path: str) -> List[Tuple[int, str, str]]:
        """Check a file for potential secret exposure."""
        violations = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.splitlines()

            for line_num, line in enumerate(lines, 1):
                for pattern, secret_type in self.SECRET_PATTERNS:
                    matches = list(re.finditer(pattern, line, re.IGNORECASE))

                    for match in matches:
                        secret_value = (
                            match.group(1) if match.groups() else match.group(0)
                        )

                        # Check if it's an allowed pattern
                        if self._is_allowed_pattern(secret_value, line):
                            continue

                        # Check if it's in a comment or documentation
                        if self._is_in_documentation(line, match.start()):
                            continue

                        violations.append((line_num, secret_type, secret_value))

        except Exception as e:
            print(f"Error checking {file_path}: {e}")

        return violations

    def _is_allowed_pattern(self, value: str, line: str) -> bool:
        """Check if the value matches allowed patterns."""
        value_lower = value.lower()
        line_lower = line.lower()

        for pattern in self.ALLOWED_PATTERNS:
            if re.search(pattern, value_lower) or re.search(pattern, line_lower):
                return True

        return False

    def _is_in_documentation(self, line: str, pos: int) -> bool:
        """Check if position is in documentation/comment."""
        before_pos = line[:pos]

        # Check for comment markers
        if "#" in before_pos or "//" in before_pos:
            return True

        # Check for documentation markers
        if any(marker in before_pos for marker in ["<!--", "```", '"""', "'''"]):
            return True

        return False

    def check_files(
        self, file_paths: List[str]
    ) -> List[Tuple[str, List[Tuple[int, str, str]]]]:
        """Check multiple files for secret exposure."""
        all_violations = []

        for file_path in file_paths:
            violations = self.check_file(file_path)
            if violations:
                all_violations.append((file_path, violations))

        return all_violations


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: check_secrets.py <file1> [file2] ...")
        sys.exit(1)

    file_paths = sys.argv[1:]
    checker = SecretChecker()

    violations = checker.check_files(file_paths)

    if violations:
        print("🚨 Potential secret exposure detected:")

        for file_path, file_violations in violations:
            print(f"\n📋 {file_path}:")
            for line_num, secret_type, value in file_violations:
                masked_value = value[:8] + "..." if len(value) > 8 else value
                print(f"   Line {line_num}: {secret_type} - '{masked_value}'")

        print("\n💡 Solutions:")
        print("   1. Use environment variables: os.getenv('SECRET_NAME')")
        print("   2. Use configuration files with proper .gitignore")
        print("   3. Use placeholder values: 'your_secret_here'")
        print("   4. Add to .secrets.baseline if it's a false positive")

        sys.exit(1)

    print("✅ No secret exposure detected")


if __name__ == "__main__":
    main()
