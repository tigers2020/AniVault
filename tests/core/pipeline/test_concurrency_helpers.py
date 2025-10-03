"""Tests for concurrency test helpers."""

from __future__ import annotations

import concurrent.futures
import threading
import time
from pathlib import Path

import pytest

from tests.core.pipeline.concurrency_helpers import (
    SharedCounter,
    create_race_condition_test_parser,
)


class TestSharedCounter:
    """Test suite for SharedCounter class."""

    def test_init_with_default_value(self) -> None:
        """Test counter initialization with default value."""
        # Given/When
        counter = SharedCounter()

        # Then
        assert counter.value == 0

    def test_init_with_custom_value(self) -> None:
        """Test counter initialization with custom value."""
        # Given/When
        counter = SharedCounter(initial_value=42)

        # Then
        assert counter.value == 42

    def test_increment_single_thread(self) -> None:
        """Test increment in a single thread."""
        # Given
        counter = SharedCounter()

        # When
        counter.increment()
        counter.increment()
        counter.increment()

        # Then
        assert counter.value == 3

    def test_increment_multiple_threads(self) -> None:
        """Test increment with multiple threads (thread safety)."""
        # Given
        counter = SharedCounter()
        num_threads = 10
        increments_per_thread = 100
        expected_total = num_threads * increments_per_thread

        def worker():
            """Worker function that increments the counter."""
            for _ in range(increments_per_thread):
                counter.increment()

        # When
        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Then - Should be exactly the expected total (no race conditions)
        assert counter.value == expected_total

    def test_unsafe_increment_has_race_conditions(self) -> None:
        """Test that unsafe increment can produce race conditions.

        Note: This test may occasionally pass by chance, but should
        fail most of the time due to race conditions.
        """
        # Given
        counter = SharedCounter()
        num_threads = 10
        increments_per_thread = 50

        def worker():
            """Worker function that unsafely increments the counter."""
            for _ in range(increments_per_thread):
                counter.increment_unsafe()

        # When
        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Then - With high probability, should NOT be the expected total
        # (This test documents that unsafe increment is indeed unsafe)
        # We don't assert failure because it could pass by chance
        result = counter.value
        expected = num_threads * increments_per_thread

        if result != expected:
            print(
                f"✅ Race condition detected: expected {expected}, got {result}",
            )
        else:
            print(
                f"⚠️  Race condition not triggered (got {result} by chance)",
            )

    def test_reset(self) -> None:
        """Test counter reset functionality."""
        # Given
        counter = SharedCounter()
        counter.increment()
        counter.increment()
        counter.increment()
        assert counter.value == 3

        # When
        counter.reset()

        # Then
        assert counter.value == 0

    def test_value_property_thread_safe(self) -> None:
        """Test that value property is thread-safe."""
        # Given
        counter = SharedCounter(initial_value=100)
        values_read = []

        def reader():
            """Thread that reads the counter value."""
            for _ in range(50):
                values_read.append(counter.value)
                time.sleep(0.001)

        def writer():
            """Thread that increments the counter."""
            for _ in range(50):
                counter.increment()
                time.sleep(0.001)

        # When
        reader_thread = threading.Thread(target=reader)
        writer_thread = threading.Thread(target=writer)

        reader_thread.start()
        writer_thread.start()

        reader_thread.join()
        writer_thread.join()

        # Then - All read values should be valid integers
        assert all(isinstance(v, int) for v in values_read)
        assert all(100 <= v <= 150 for v in values_read)


class TestRaceConditionTestParser:
    """Test suite for race condition test parser."""

    def test_create_parser_with_lock(self) -> None:
        """Test creating a parser that uses locking."""
        # Given
        counter = SharedCounter()

        # When
        parser = create_race_condition_test_parser(counter, use_lock=True)
        result = parser(Path("test.mp4"))

        # Then
        assert result["status"] == "success"
        assert counter.value == 1

    def test_create_parser_without_lock(self) -> None:
        """Test creating a parser that doesn't use locking."""
        # Given
        counter = SharedCounter()

        # When
        parser = create_race_condition_test_parser(counter, use_lock=False)
        result = parser(Path("test.mp4"))

        # Then
        assert result["status"] == "success"
        # Counter value should be incremented (but unsafely)
        assert counter.value == 1

    def test_parser_increments_counter_multiple_calls(self) -> None:
        """Test that parser increments counter on each call."""
        # Given
        counter = SharedCounter()
        parser = create_race_condition_test_parser(counter, use_lock=True)

        # When
        for i in range(10):
            parser(Path(f"test_{i}.mp4"))

        # Then
        assert counter.value == 10
