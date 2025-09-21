"""Tests for TMDB client optimization and performance monitoring.

This module contains tests to verify that the TMDB client optimization
effectively reduces object creation overhead and improves performance
in parallel processing scenarios.
"""

import os
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import MagicMock, patch

import psutil

from src.core.tmdb_client import TMDBClient, TMDBConfig
from src.core.tmdb_client_pool import (
    TMDBClientPool,
    ThreadLocalTMDBClient,
    get_tmdb_client_pool,
    get_tmdb_thread_local_client,
    reset_tmdb_client_managers,
)


class TestTMDBClientOptimization(unittest.TestCase):
    """Test cases for TMDB client optimization."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset global managers
        reset_tmdb_client_managers()

        # Mock TMDB API key for testing
        self.test_api_key = "test_api_key_12345"
        self.test_config = TMDBConfig(
            api_key=self.test_api_key,
            language="ko-KR",
            timeout=5,
        )

    def tearDown(self):
        """Clean up after tests."""
        reset_tmdb_client_managers()

    def test_tmdb_client_pool_creation(self):
        """Test TMDB client pool creation and basic functionality."""
        pool = TMDBClientPool(self.test_config, initial_size=2, max_size=4)

        # Test pool statistics
        stats = pool.get_pool_stats()
        self.assertEqual(stats["pool_size"], 2)
        self.assertEqual(stats["max_pool_size"], 4)
        self.assertEqual(stats["created_clients"], 2)
        self.assertEqual(stats["active_clients"], 0)

    def test_tmdb_client_pool_acquire_release(self):
        """Test acquiring and releasing clients from the pool."""
        pool = TMDBClientPool(self.test_config, initial_size=2, max_size=4)

        # Acquire a client
        with patch.object(TMDBClient, '__init__', return_value=None):
            client = pool.acquire()
            self.assertIsNotNone(client)

            stats = pool.get_pool_stats()
            self.assertEqual(stats["active_clients"], 1)
            self.assertEqual(stats["pool_size"], 1)

            # Release the client
            pool.release(client)

            stats = pool.get_pool_stats()
            self.assertEqual(stats["active_clients"], 0)
            self.assertEqual(stats["pool_size"], 2)

    def test_tmdb_client_pool_context_manager(self):
        """Test using the pool as a context manager."""
        pool = TMDBClientPool(self.test_config, initial_size=1, max_size=2)

        with patch.object(TMDBClient, '__init__', return_value=None):
            with pool.get_client() as client:
                self.assertIsNotNone(client)
                stats = pool.get_pool_stats()
                self.assertEqual(stats["active_clients"], 1)

            # Client should be released automatically
            stats = pool.get_pool_stats()
            self.assertEqual(stats["active_clients"], 0)

    def test_thread_local_tmdb_client(self):
        """Test thread-local TMDB client manager."""
        thread_local_manager = ThreadLocalTMDBClient(self.test_config)

        with patch.object(TMDBClient, '__init__', return_value=None):
            # Get client in main thread
            client1 = thread_local_manager.get_client()
            self.assertIsNotNone(client1)

            # Get client again in same thread (should be same instance)
            client2 = thread_local_manager.get_client()
            self.assertIs(client1, client2)

            # Get client in different thread (should be different instance)
            client3 = None

            def get_client_in_thread():
                nonlocal client3
                client3 = thread_local_manager.get_client()

            thread = threading.Thread(target=get_client_in_thread)
            thread.start()
            thread.join()

            self.assertIsNotNone(client3)
            self.assertIsNot(client1, client3)

    def test_parallel_client_usage_performance(self):
        """Test performance of parallel client usage."""
        num_threads = 4
        operations_per_thread = 10

        # Test with traditional approach (creating new clients)
        start_time = time.time()
        memory_before = psutil.Process().memory_info().rss

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for _ in range(num_threads):
                future = executor.submit(self._traditional_client_usage, operations_per_thread)
                futures.append(future)

            for future in as_completed(futures):
                future.result()

        traditional_time = time.time() - start_time
        memory_after_traditional = psutil.Process().memory_info().rss
        traditional_memory_usage = memory_after_traditional - memory_before

        # Reset for next test
        reset_tmdb_client_managers()

        # Test with thread-local approach
        start_time = time.time()
        memory_before = psutil.Process().memory_info().rss

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for _ in range(num_threads):
                future = executor.submit(self._optimized_client_usage, operations_per_thread)
                futures.append(future)

            for future in as_completed(futures):
                future.result()

        optimized_time = time.time() - start_time
        memory_after_optimized = psutil.Process().memory_info().rss
        optimized_memory_usage = memory_after_optimized - memory_before

        # Performance assertions
        print(f"Traditional approach: {traditional_time:.3f}s, Memory: {traditional_memory_usage} bytes")
        print(f"Optimized approach: {optimized_time:.3f}s, Memory: {optimized_memory_usage} bytes")

        # Optimized approach should be faster and use less memory
        self.assertLess(optimized_time, traditional_time * 1.2)  # Allow 20% tolerance
        self.assertLess(optimized_memory_usage, traditional_memory_usage)

    def _traditional_client_usage(self, operations: int):
        """Traditional approach: create new client for each operation."""
        for _ in range(operations):
            with patch.object(TMDBClient, '__init__', return_value=None):
                config = TMDBConfig(api_key=self.test_api_key)
                client = TMDBClient(config)
                # Simulate some work
                time.sleep(0.001)

    def _optimized_client_usage(self, operations: int):
        """Optimized approach: use thread-local client."""
        thread_local_manager = get_tmdb_thread_local_client(self.test_config)

        for _ in range(operations):
            with patch.object(TMDBClient, '__init__', return_value=None):
                client = thread_local_manager.get_client()
                # Simulate some work
                time.sleep(0.001)

    def test_client_pool_health_check(self):
        """Test pool health check functionality."""
        pool = TMDBClientPool(self.test_config, initial_size=2, max_size=4)

        with patch.object(TMDBClient, '__init__', return_value=None):
            # Test healthy pool
            health = pool.health_check()
            self.assertTrue(health["healthy"])
            self.assertEqual(len(health["issues"]), 0)

            # Test pool under stress
            clients = []
            for _ in range(4):  # Exhaust the pool
                client = pool.acquire()
                clients.append(client)

            health = pool.health_check()
            self.assertFalse(health["healthy"])
            self.assertGreater(len(health["issues"]), 0)

            # Release clients
            for client in clients:
                pool.release(client)

    def test_pool_resize_functionality(self):
        """Test pool resize functionality."""
        pool = TMDBClientPool(self.test_config, initial_size=2, max_size=4)

        with patch.object(TMDBClient, '__init__', return_value=None):
            # Test shrinking pool
            pool.resize_pool(3)
            stats = pool.get_pool_stats()
            self.assertEqual(stats["max_pool_size"], 3)

            # Test growing pool
            pool.resize_pool(6)
            stats = pool.get_pool_stats()
            self.assertEqual(stats["max_pool_size"], 6)

    def test_global_manager_functions(self):
        """Test global manager functions."""
        # Test getting thread-local client manager
        manager = get_tmdb_thread_local_client(self.test_config)
        self.assertIsInstance(manager, ThreadLocalTMDBClient)

        # Test getting client pool
        pool = get_tmdb_client_pool(self.test_config)
        self.assertIsInstance(pool, TMDBClientPool)

        # Test resetting managers
        reset_tmdb_client_managers()
        # Should create new instances after reset
        manager2 = get_tmdb_thread_local_client(self.test_config)
        self.assertIsNot(manager, manager2)

    def test_concurrent_access_safety(self):
        """Test thread safety of concurrent access."""
        pool = TMDBClientPool(self.test_config, initial_size=2, max_size=8)
        results = []
        errors = []

        def worker(worker_id: int):
            try:
                with patch.object(TMDBClient, '__init__', return_value=None):
                    with pool.get_client() as client:
                        results.append(f"Worker {worker_id} got client")
                        time.sleep(0.01)  # Simulate work
                        results.append(f"Worker {worker_id} released client")
            except Exception as e:
                errors.append(str(e))

        # Run multiple workers concurrently
        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")

        # Verify all workers completed successfully
        self.assertEqual(len(results), 20)  # 2 results per worker

    def test_memory_usage_comparison(self):
        """Test memory usage comparison between approaches."""
        num_operations = 50

        # Traditional approach memory usage
        memory_before = psutil.Process().memory_info().rss
        self._traditional_client_usage(num_operations)
        memory_after_traditional = psutil.Process().memory_info().rss
        traditional_memory = memory_after_traditional - memory_before

        # Reset for optimized test
        reset_tmdb_client_managers()

        # Optimized approach memory usage
        memory_before = psutil.Process().memory_info().rss
        self._optimized_client_usage(num_operations)
        memory_after_optimized = psutil.Process().memory_info().rss
        optimized_memory = memory_after_optimized - memory_before

        print(f"Traditional memory usage: {traditional_memory} bytes")
        print(f"Optimized memory usage: {optimized_memory} bytes")

        # Optimized approach should use significantly less memory
        memory_reduction = (traditional_memory - optimized_memory) / traditional_memory
        self.assertGreater(memory_reduction, 0.1, "Memory usage should be reduced by at least 10%")


class TestTMDBClientPoolIntegration(unittest.TestCase):
    """Integration tests for TMDB client pool with actual usage patterns."""

    def setUp(self):
        """Set up integration test fixtures."""
        reset_tmdb_client_managers()
        self.test_api_key = "test_api_key_12345"
        self.test_config = TMDBConfig(api_key=self.test_api_key)

    def tearDown(self):
        """Clean up after integration tests."""
        reset_tmdb_client_managers()

    def test_simulated_file_processing_workflow(self):
        """Test simulated file processing workflow with optimized clients."""
        num_files = 20
        num_threads = 4

        def process_file(file_id: int):
            """Simulate processing a single file."""
            thread_local_manager = get_tmdb_thread_local_client(self.test_config)

            with patch.object(TMDBClient, '__init__', return_value=None):
                client = thread_local_manager.get_client()

                # Simulate TMDB API call
                time.sleep(0.01)

                return f"Processed file {file_id}"

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(process_file, i) for i in range(num_files)]
            results = [future.result() for future in as_completed(futures)]

        processing_time = time.time() - start_time

        # Verify all files were processed
        self.assertEqual(len(results), num_files)

        # Performance should be reasonable
        self.assertLess(processing_time, 2.0, "Processing should complete within 2 seconds")

        print(f"Processed {num_files} files in {processing_time:.3f} seconds with {num_threads} threads")

    def test_pool_statistics_accuracy(self):
        """Test accuracy of pool statistics during concurrent usage."""
        pool = TMDBClientPool(self.test_config, initial_size=2, max_size=6)

        def worker():
            with patch.object(TMDBClient, '__init__', return_value=None):
                with pool.get_client() as client:
                    time.sleep(0.05)  # Hold client for a bit
                    return True

        # Run workers and collect statistics
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(worker) for _ in range(8)]
            for future in as_completed(futures):
                self.assertTrue(future.result())

        # Check final statistics
        stats = pool.get_pool_stats()
        self.assertEqual(stats["active_clients"], 0, "All clients should be released")
        self.assertGreater(stats["pool_hits"], 0, "Should have some pool hits")
        self.assertGreater(stats["total_requests"], 0, "Should have some total requests")


if __name__ == "__main__":
    unittest.main()
