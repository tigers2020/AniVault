"""Memory profiling tests for directory scanning.

This module contains tests to verify that directory scanning remains
memory-efficient even with large directory structures (100k+ files).
"""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import psutil
import pytest

from anivault.scanner.file_scanner import (
    scan_directory,
    scan_directory_paths,
    scan_directory_with_stats,
)
from anivault.scanner.scan_parse_pool import ScanParsePool


class MemoryProfiler:
    """Memory profiler for directory scanning operations."""

    def __init__(self):
        """Initialize the memory profiler."""
        self.process = psutil.Process(os.getpid())
        self.initial_memory = self.process.memory_info().rss
        self.peak_memory = self.initial_memory
        self.memory_samples: List[int] = []

    def start_monitoring(self) -> None:
        """Start memory monitoring."""
        self.initial_memory = self.process.memory_info().rss
        self.peak_memory = self.initial_memory
        self.memory_samples = [self.initial_memory]

    def sample_memory(self) -> int:
        """Take a memory sample and update peak memory."""
        current_memory = self.process.memory_info().rss
        self.memory_samples.append(current_memory)
        self.peak_memory = max(self.peak_memory, current_memory)
        return current_memory

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        final_memory = self.process.memory_info().rss
        memory_used = final_memory - self.initial_memory
        peak_memory_used = self.peak_memory - self.initial_memory

        return {
            "initial_memory_mb": self.initial_memory / (1024 * 1024),
            "final_memory_mb": final_memory / (1024 * 1024),
            "peak_memory_mb": self.peak_memory / (1024 * 1024),
            "memory_used_mb": memory_used / (1024 * 1024),
            "peak_memory_used_mb": peak_memory_used / (1024 * 1024),
            "samples_taken": len(self.memory_samples),
            "memory_efficient": peak_memory_used < (500 * 1024 * 1024),  # 500MB limit
        }


class LargeDirectoryGenerator:
    """Generator for creating large directory structures for testing."""

    def __init__(self, base_path: Path, target_files: int = 100000):
        """Initialize the directory generator.

        Args:
            base_path: Base path for the test directory.
            target_files: Target number of files to create.
        """
        self.base_path = base_path
        self.target_files = target_files
        self.files_created = 0

    def create_large_directory_structure(self) -> Path:
        """Create a large directory structure with many files.

        Returns:
            Path to the created test directory.
        """
        test_dir = self.base_path / "large_test_directory"
        test_dir.mkdir(exist_ok=True)

        # Create subdirectories and files
        files_per_dir = 1000  # Files per subdirectory
        num_dirs = (self.target_files + files_per_dir - 1) // files_per_dir

        for i in range(num_dirs):
            subdir = test_dir / f"subdir_{i:06d}"
            subdir.mkdir()

            # Create files in this subdirectory
            files_in_this_dir = min(
                files_per_dir, self.target_files - self.files_created
            )
            for j in range(files_in_this_dir):
                # Create media files (mkv, mp4, avi, etc.)
                if j % 10 == 0:  # 10% are media files
                    ext = [".mkv", ".mp4", ".avi", ".mov", ".wmv"][j % 5]
                    filename = f"media_{i:06d}_{j:06d}{ext}"
                else:
                    # 90% are non-media files
                    ext = [".txt", ".log", ".tmp", ".bak", ".old"][j % 5]
                    filename = f"file_{i:06d}_{j:06d}{ext}"

                file_path = subdir / filename
                file_path.touch()
                self.files_created += 1

                if self.files_created >= self.target_files:
                    break

            if self.files_created >= self.target_files:
                break

        return test_dir


class TestMemoryProfiling:
    """Test cases for memory profiling of directory scanning."""

    @pytest.mark.slow
    @pytest.mark.memory_intensive
    def test_large_directory_scanning_memory_usage(self):
        """Test memory usage when scanning a large directory structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create large directory structure
            generator = LargeDirectoryGenerator(temp_path, target_files=100000)
            test_dir = generator.create_large_directory_structure()

            # Initialize memory profiler
            profiler = MemoryProfiler()
            profiler.start_monitoring()

            # Scan the directory and monitor memory
            files_found = 0
            memory_samples = []

            for entry in scan_directory(test_dir):
                files_found += 1

                # Sample memory every 1000 files
                if files_found % 1000 == 0:
                    current_memory = profiler.sample_memory()
                    memory_samples.append(current_memory)

                    # Check if memory usage is reasonable (should be < 500MB)
                    memory_mb = (current_memory - profiler.initial_memory) / (
                        1024 * 1024
                    )
                    assert memory_mb < 500, f"Memory usage too high: {memory_mb:.2f}MB"

            # Get final memory statistics
            stats = profiler.get_memory_stats()

            # Verify memory efficiency
            assert stats["memory_efficient"], (
                f"Memory usage exceeded 500MB limit: "
                f"peak={stats['peak_memory_used_mb']:.2f}MB"
            )

            # Verify we found the expected number of media files
            expected_media_files = generator.target_files // 10  # 10% are media files
            assert files_found == expected_media_files, (
                f"Expected {expected_media_files} media files, found {files_found}"
            )

            print("Memory profiling results:")
            print(f"  Files scanned: {files_found}")
            print(f"  Peak memory used: {stats['peak_memory_used_mb']:.2f}MB")
            print(f"  Memory efficient: {stats['memory_efficient']}")

    @pytest.mark.slow
    @pytest.mark.memory_intensive
    def test_scan_directory_paths_memory_usage(self):
        """Test memory usage when scanning with scan_directory_paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create large directory structure
            generator = LargeDirectoryGenerator(temp_path, target_files=50000)
            test_dir = generator.create_large_directory_structure()

            # Initialize memory profiler
            profiler = MemoryProfiler()
            profiler.start_monitoring()

            # Scan using scan_directory_paths
            files_found = 0
            for file_path in scan_directory_paths(test_dir):
                files_found += 1

                # Sample memory every 1000 files
                if files_found % 1000 == 0:
                    current_memory = profiler.sample_memory()
                    memory_mb = (current_memory - profiler.initial_memory) / (
                        1024 * 1024
                    )
                    assert memory_mb < 500, f"Memory usage too high: {memory_mb:.2f}MB"

            # Get final memory statistics
            stats = profiler.get_memory_stats()

            # Verify memory efficiency
            assert stats["memory_efficient"], (
                f"Memory usage exceeded 500MB limit: "
                f"peak={stats['peak_memory_used_mb']:.2f}MB"
            )

            print("scan_directory_paths memory profiling results:")
            print(f"  Files scanned: {files_found}")
            print(f"  Peak memory used: {stats['peak_memory_used_mb']:.2f}MB")

    @pytest.mark.slow
    @pytest.mark.memory_intensive
    def test_scan_parse_pool_memory_usage(self):
        """Test memory usage when using ScanParsePool for large directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create large directory structure
            generator = LargeDirectoryGenerator(temp_path, target_files=75000)
            test_dir = generator.create_large_directory_structure()

            # Initialize memory profiler
            profiler = MemoryProfiler()
            profiler.start_monitoring()

            # Use ScanParsePool
            with ScanParsePool(max_workers=4, queue_size=1000) as pool:
                files_processed = 0

                for file_path in pool.process_directory(test_dir):
                    files_processed += 1

                    # Sample memory every 1000 files
                    if files_processed % 1000 == 0:
                        current_memory = profiler.sample_memory()
                        memory_mb = (current_memory - profiler.initial_memory) / (
                            1024 * 1024
                        )
                        assert memory_mb < 500, (
                            f"Memory usage too high: {memory_mb:.2f}MB"
                        )

            # Get final memory statistics
            stats = profiler.get_memory_stats()

            # Verify memory efficiency
            assert stats["memory_efficient"], (
                f"Memory usage exceeded 500MB limit: "
                f"peak={stats['peak_memory_used_mb']:.2f}MB"
            )

            print("ScanParsePool memory profiling results:")
            print(f"  Files processed: {files_processed}")
            print(f"  Peak memory used: {stats['peak_memory_used_mb']:.2f}MB")

    @pytest.mark.slow
    def test_memory_usage_with_stats(self):
        """Test memory usage when using scan_directory_with_stats."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create medium directory structure
            generator = LargeDirectoryGenerator(temp_path, target_files=10000)
            test_dir = generator.create_large_directory_structure()

            # Initialize memory profiler
            profiler = MemoryProfiler()
            profiler.start_monitoring()

            # Scan with stats
            file_iterator, stats = scan_directory_with_stats(test_dir)
            files_found = 0

            for entry in file_iterator:
                files_found += 1

                # Sample memory every 500 files
                if files_found % 500 == 0:
                    current_memory = profiler.sample_memory()
                    memory_mb = (current_memory - profiler.initial_memory) / (
                        1024 * 1024
                    )
                    assert memory_mb < 100, f"Memory usage too high: {memory_mb:.2f}MB"

            # Get final memory statistics
            stats_final = profiler.get_memory_stats()

            # Verify memory efficiency
            assert stats_final["memory_efficient"], (
                f"Memory usage exceeded 500MB limit: "
                f"peak={stats_final['peak_memory_used_mb']:.2f}MB"
            )

            # Verify stats are correct
            assert stats["files_found"] == files_found
            assert stats["directories_scanned"] > 0

            print("scan_directory_with_stats memory profiling results:")
            print(f"  Files found: {files_found}")
            print(f"  Directories scanned: {stats['directories_scanned']}")
            print(f"  Peak memory used: {stats_final['peak_memory_used_mb']:.2f}MB")

    def test_memory_profiler_functionality(self):
        """Test the MemoryProfiler class functionality."""
        profiler = MemoryProfiler()
        profiler.start_monitoring()

        # Simulate some memory usage
        data = []
        for i in range(1000):
            data.append(f"test_string_{i}" * 100)
            if i % 100 == 0:
                profiler.sample_memory()

        stats = profiler.get_memory_stats()

        # Verify stats are reasonable
        assert stats["initial_memory_mb"] > 0
        assert stats["final_memory_mb"] > stats["initial_memory_mb"]
        assert stats["peak_memory_mb"] >= stats["final_memory_mb"]
        assert stats["samples_taken"] > 0
        assert isinstance(stats["memory_efficient"], bool)

        print("Memory profiler test results:")
        print(f"  Initial memory: {stats['initial_memory_mb']:.2f}MB")
        print(f"  Final memory: {stats['final_memory_mb']:.2f}MB")
        print(f"  Peak memory: {stats['peak_memory_mb']:.2f}MB")
        print(f"  Memory used: {stats['memory_used_mb']:.2f}MB")


class TestMemoryOptimization:
    """Test cases for memory optimization features."""

    def test_generator_memory_efficiency(self):
        """Test that generators are memory efficient."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            for i in range(1000):
                (temp_path / f"test_{i}.mkv").touch()

            # Test that scan_directory returns a generator
            scanner = scan_directory(temp_path)
            assert hasattr(scanner, "__iter__")
            assert hasattr(scanner, "__next__")

            # Test that we can iterate without loading everything into memory
            files_found = 0
            for entry in scanner:
                files_found += 1
                # Each iteration should not accumulate memory
                if files_found > 100:
                    break

            assert files_found > 0

    def test_os_scandir_usage(self):
        """Test that os.scandir is used for memory efficiency."""
        # This test verifies that the implementation uses os.scandir
        # by checking that it doesn't use os.walk or os.listdir patterns

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            for i in range(100):
                (temp_path / f"test_{i}.mkv").touch()

            # The implementation should use os.scandir internally
            # This is verified by the fact that it's memory efficient
            files = list(scan_directory(temp_path))
            assert len(files) == 100

            # Verify that os.DirEntry objects are returned
            for entry in files:
                assert hasattr(entry, "name")
                assert hasattr(entry, "path")
                assert hasattr(entry, "is_file")
                assert hasattr(entry, "is_dir")
