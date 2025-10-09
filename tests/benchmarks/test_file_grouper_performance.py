"""Performance tests for FileGrouper optimization.

Tests the O(n²) to O(n log n) optimization in file grouping.
"""

import time
from pathlib import Path
from typing import List

import pytest

from anivault.core.file_grouper import FileGrouper
from anivault.core.models import ScannedFile
from anivault.core.parser.models import ParsingResult


class TestFileGrouperPerformance:
    """Performance tests for FileGrouper optimization."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.grouper = FileGrouper(similarity_threshold=0.8)

    def _generate_test_files(
        self, count: int, title_variations: int = 5
    ) -> List[ScannedFile]:
        """Generate test files with similar titles for performance testing."""
        base_titles = [
            "Attack on Titan",
            "Demon Slayer",
            "One Piece",
            "Naruto Shippuden",
            "My Hero Academia",
        ]

        files = []
        for i in range(count):
            base_title = base_titles[i % len(base_titles)]
            variation = i // len(base_titles)

            # Create variations with different technical info
            if variation == 0:
                filename = f"{base_title} S01E{i+1:02d}.mkv"
            elif variation == 1:
                filename = f"[SubsPlease] {base_title} - S01E{i+1:02d} [1080p].mkv"
            elif variation == 2:
                filename = f"[Erai-raws] {base_title} S01E{i+1:02d} [x264] [AAC].mkv"
            elif variation == 3:
                filename = f"{base_title} Season 1 Episode {i+1} [WEB-DL].mkv"
            else:
                filename = f"{base_title} - Episode {i+1} [1080p] [x265].mkv"

            files.append(
                ScannedFile(
                    file_path=Path(filename),
                    metadata=ParsingResult(title=base_title),
                    file_size=1000 + i,
                    last_modified=1234567890.0 + i,
                )
            )

        return files

    def test_performance_small_dataset(self) -> None:
        """Test performance with small dataset (10 files)."""
        files = self._generate_test_files(10)

        start_time = time.time()
        result = self.grouper.group_files(files)
        end_time = time.time()

        execution_time = end_time - start_time

        # Should complete quickly for small dataset
        assert (
            execution_time < 1.0
        ), f"Small dataset took too long: {execution_time:.3f}s"
        assert len(result) <= 5, "Should group similar files together"

        print(f"Small dataset (10 files): {execution_time:.3f}s, {len(result)} groups")

    def test_performance_medium_dataset(self) -> None:
        """Test performance with medium dataset (100 files)."""
        files = self._generate_test_files(100)

        start_time = time.time()
        result = self.grouper.group_files(files)
        end_time = time.time()

        execution_time = end_time - start_time

        # Should complete reasonably quickly for medium dataset
        assert (
            execution_time < 5.0
        ), f"Medium dataset took too long: {execution_time:.3f}s"
        assert len(result) <= 25, "Should group similar files together"

        print(
            f"Medium dataset (100 files): {execution_time:.3f}s, {len(result)} groups"
        )

    def test_performance_large_dataset(self) -> None:
        """Test performance with large dataset (500 files)."""
        files = self._generate_test_files(500)

        start_time = time.time()
        result = self.grouper.group_files(files)
        end_time = time.time()

        execution_time = end_time - start_time

        # Should complete within reasonable time for large dataset
        assert (
            execution_time < 30.0
        ), f"Large dataset took too long: {execution_time:.3f}s"
        assert len(result) <= 125, "Should group similar files together"

        print(f"Large dataset (500 files): {execution_time:.3f}s, {len(result)} groups")

    def test_performance_scalability(self) -> None:
        """Test that performance scales better than O(n²)."""
        sizes = [50, 100, 200]
        times = []

        for size in sizes:
            files = self._generate_test_files(size)

            start_time = time.time()
            result = self.grouper.group_files(files)
            end_time = time.time()

            execution_time = end_time - start_time
            times.append(execution_time)

            print(f"Size {size}: {execution_time:.3f}s, {len(result)} groups")

        # Check that time doesn't grow quadratically
        # If it were O(n²), time would roughly quadruple when size doubles
        # With O(n log n), time should grow more slowly
        if len(times) >= 2:
            ratio_50_100 = times[1] / times[0] if times[0] > 0 else float("inf")
            ratio_100_200 = times[2] / times[1] if times[1] > 0 else float("inf")

            # For O(n log n), ratios should be less than 4 (quadratic)
            # Typical ratios for O(n log n): ~2.1 for 2x size increase
            assert ratio_50_100 < 4.0, f"Performance ratio too high: {ratio_50_100:.2f}"
            assert (
                ratio_100_200 < 4.0
            ), f"Performance ratio too high: {ratio_100_200:.2f}"

            print(
                f"Performance ratios: 50->100: {ratio_50_100:.2f}, 100->200: {ratio_100_200:.2f}"
            )

    def test_hash_based_grouping_efficiency(self) -> None:
        """Test that hash-based pre-grouping reduces similarity calculations."""
        files = self._generate_test_files(100)

        # Count similarity calculations in the optimized version
        original_calculate_similarity = self.grouper._calculate_similarity
        similarity_call_count = 0

        def counting_calculate_similarity(title1: str, title2: str) -> float:
            nonlocal similarity_call_count
            similarity_call_count += 1
            return original_calculate_similarity(title1, title2)

        self.grouper._calculate_similarity = counting_calculate_similarity

        try:
            result = self.grouper.group_files(files)

            # With 100 files, O(n²) would be 10,000 comparisons
            # With hash-based pre-filtering, should be much fewer
            total_possible_comparisons = 100 * 99 // 2  # n*(n-1)/2
            reduction_ratio = similarity_call_count / total_possible_comparisons

            assert (
                similarity_call_count < total_possible_comparisons
            ), f"Hash pre-filtering not working: {similarity_call_count} vs {total_possible_comparisons}"

            assert (
                reduction_ratio < 0.5
            ), f"Hash pre-filtering should reduce comparisons by at least 50%: {reduction_ratio:.2f}"

            print(
                f"Similarity calculations: {similarity_call_count}/{total_possible_comparisons} ({reduction_ratio:.2%})"
            )

        finally:
            # Restore original method
            self.grouper._calculate_similarity = original_calculate_similarity

    def test_union_find_efficiency(self) -> None:
        """Test that Union-Find algorithm works correctly."""
        # Create files with known similarities
        files = [
            ScannedFile(
                file_path=Path("Attack on Titan S01E01.mkv"),
                metadata=ParsingResult(title="Attack on Titan"),
                file_size=1000,
                last_modified=1234567890.0,
            ),
            ScannedFile(
                file_path=Path("Attack on Titan S01E02.mkv"),
                metadata=ParsingResult(title="Attack on Titan"),
                file_size=1000,
                last_modified=1234567890.0,
            ),
            ScannedFile(
                file_path=Path("Attack on Titan S01E03.mkv"),
                metadata=ParsingResult(title="Attack on Titan"),
                file_size=1000,
                last_modified=1234567890.0,
            ),
            ScannedFile(
                file_path=Path("Demon Slayer S01E01.mkv"),
                metadata=ParsingResult(title="Demon Slayer"),
                file_size=1000,
                last_modified=1234567890.0,
            ),
            ScannedFile(
                file_path=Path("Demon Slayer S01E02.mkv"),
                metadata=ParsingResult(title="Demon Slayer"),
                file_size=1000,
                last_modified=1234567890.0,
            ),
        ]

        result = self.grouper.group_files(files)

        # Should group similar titles together
        assert len(result) == 2, f"Expected 2 groups, got {len(result)}"

        # Check that Attack on Titan files are grouped together
        aot_files = None
        ds_files = None

        for group_name, group_files in result.items():
            if "Attack on Titan" in group_name:
                aot_files = group_files
            elif "Demon Slayer" in group_name:
                ds_files = group_files

        assert aot_files is not None, "Attack on Titan group not found"
        assert ds_files is not None, "Demon Slayer group not found"
        assert (
            len(aot_files) == 3
        ), f"Expected 3 Attack on Titan files, got {len(aot_files)}"
        assert len(ds_files) == 2, f"Expected 2 Demon Slayer files, got {len(ds_files)}"

    def test_memory_usage(self) -> None:
        """Test that memory usage doesn't grow excessively."""
        try:
            import os

            import psutil

            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB

            # Process large dataset
            files = self._generate_test_files(500)
            result = self.grouper.group_files(files)

            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory

            # Memory increase should be reasonable (less than 100MB for 500 files)
            assert (
                memory_increase < 100
            ), f"Memory usage increased too much: {memory_increase:.2f}MB"

            print(f"Memory usage: {memory_increase:.2f}MB increase for 500 files")
        except ImportError:
            pytest.skip("psutil not available for memory testing")
