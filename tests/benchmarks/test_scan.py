"""Benchmark tests for directory scanning."""

from __future__ import annotations

import os
import pytest
from pathlib import Path


@pytest.fixture
def scanner():  # type: ignore[no-untyped-def]
    """Create scanner function (simple implementation)."""
    def scan_directory(path: Path) -> list[Path]:
        """Recursively scan directory for video files."""
        video_exts = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"}
        files = []
        for root, dirs, filenames in os.walk(path):
            for filename in filenames:
                if Path(filename).suffix.lower() in video_exts:
                    files.append(Path(root) / filename)
        return files
    return scan_directory


@pytest.fixture
def test_directory(tmp_path: Path) -> Path:
    """Create test directory with anime files."""
    # Create 100 test files
    for i in range(100):
        (tmp_path / f"[SubGroup] Anime Title - {i:02d} [1080p].mkv").touch()
    return tmp_path


def test_benchmark_scan_directory(benchmark, scanner, test_directory) -> None:  # type: ignore[no-untyped-def]
    """Benchmark directory scanning speed."""
    result = benchmark(scanner, test_directory)
    
    # Verify results
    assert len(result) == 100
    assert all(f.suffix == ".mkv" for f in result)


def test_benchmark_scan_large_directory(benchmark, scanner, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    """Benchmark scanning directory with 1000 files."""
    # Create 1000 test files
    for i in range(1000):
        (tmp_path / f"[SubGroup] Anime Title - {i:03d} [1080p].mkv").touch()
    
    result = benchmark(scanner, tmp_path)
    assert len(result) == 1000

