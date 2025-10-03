#!/usr/bin/env python3
"""Duplicate Definition Check Script for Pre-commit Hook.

Ensures One Source of Truth principle - no duplicate type/constant definitions.
"""

import ast
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


class DuplicateChecker:
    """Checks for duplicate definitions across files."""

    def __init__(self):
        self.definitions: Dict[
            str, List[Tuple[str, int]]
        ] = {}  # name -> [(file, line)]
        self.violations = []

    def check_file(self, file_path: str) -> None:
        """Check a file for definitions."""
        if not file_path.endswith(".py"):
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    self._record_definition(node.name, file_path, node.lineno, "class")
                elif isinstance(node, ast.FunctionDef):
                    self._record_definition(
                        node.name, file_path, node.lineno, "function"
                    )
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            # Only check uppercase constants
                            if target.id.isupper():
                                self._record_definition(
                                    target.id, file_path, node.lineno, "constant"
                                )

        except SyntaxError:
            # Skip files with syntax errors
            pass
        except Exception as e:
            print(f"Error checking {file_path}: {e}")

    def _record_definition(
        self, name: str, file_path: str, line: int, kind: str
    ) -> None:
        """Record a definition."""
        if name not in self.definitions:
            self.definitions[name] = []

        self.definitions[name].append((file_path, line, kind))

    def find_duplicates(self) -> List[Tuple[str, List[Tuple[str, int, str]]]]:
        """Find duplicate definitions."""
        duplicates = []

        for name, locations in self.definitions.items():
            if len(locations) > 1:
                # Check if they're in different files
                files = set(loc[0] for loc in locations)
                if len(files) > 1:
                    duplicates.append((name, locations))

        return duplicates

    def check_duplicates(self, file_paths: List[str]) -> List[str]:
        """Check files for duplicate definitions."""
        # Clear previous results
        self.definitions.clear()
        self.violations = []

        # Check all files
        for file_path in file_paths:
            self.check_file(file_path)

        # Find duplicates
        duplicates = self.find_duplicates()

        violations = []
        for name, locations in duplicates:
            violation_msg = f"Duplicate definition '{name}' found in:"
            for file_path, line, kind in locations:
                violation_msg += f"\n  - {file_path}:{line} ({kind})"
            violations.append(violation_msg)

        return violations


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: check_duplicates.py <file1> [file2] ...")
        sys.exit(1)

    file_paths = sys.argv[1:]
    checker = DuplicateChecker()

    violations = checker.check_duplicates(file_paths)

    if violations:
        print("🚨 Duplicate definitions found:")
        for violation in violations:
            print(f"\n{violation}")

        print("\n💡 Solution:")
        print(
            "   Move definitions to anivault.shared.constants or anivault.shared.types"
        )
        print("   Import from the centralized location instead of redefining")

        sys.exit(1)

    print("✅ No duplicate definitions found")


if __name__ == "__main__":
    main()
