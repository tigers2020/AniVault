"""Count lines in SQLite cache module."""

from pathlib import Path


def count_lines():
    """Count lines in all Python files in sqlite_cache module."""
    base_path = Path("src/anivault/services/sqlite_cache")
    files = list(base_path.rglob("*.py"))

    total = 0
    for file in files:
        lines = len(file.read_text(encoding="utf-8").splitlines())
        print(f"{file.name}: {lines} lines")
        total += lines

    print(f"\nTotal: {total} lines")


if __name__ == "__main__":
    count_lines()
