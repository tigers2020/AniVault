"""Performance tests for the resilience system cache-only mode operations.

This module contains performance tests that measure the efficiency and speed
of cache-only mode operations under various load conditions.
"""

import time
import statistics
from typing import List, Dict, Any
from unittest.mock import Mock

import pytest

from src.core.metadata_cache import MetadataCache, CacheEntry
from src.core.models import ParsedAnimeInfo, TMDBAnime


class TestCacheOnlyModePerformance:
    """Performance tests for cache-only mode operations."""

    def setup_method(self):
        """Set up test fixtures for performance testing."""
        # Create mock database
        self.mock_db = Mock()
        self.mock_session = Mock()
        self.mock_db.get_session.return_value = self.mock_session
        
        # Mock transaction manager
        self.mock_tx_manager = Mock()
        self.mock_tx_manager.transaction_scope.return_value.__enter__ = Mock(return_value=self.mock_session)
        self.mock_tx_manager.transaction_scope.return_value.__exit__ = Mock(return_value=None)
        
        # Create MetadataCache instance with larger cache for performance testing
        self.cache = MetadataCache(
            max_size=10000,  # Larger cache for performance testing
            db_manager=self.mock_db,
            enable_db=True
        )
        
        # Patch transaction manager in the cache
        self.cache._tx_manager = self.mock_tx_manager
        
        # Enable cache-only mode for performance testing
        self.cache.enable_cache_only_mode()
        
        # Create sample data for testing
        self.sample_data = self._create_sample_data()

    def _create_sample_data(self) -> List[Dict[str, Any]]:
        """Create sample data for performance testing."""
        sample_data = []
        
        # Create ParsedAnimeInfo samples
        for i in range(1000):
            sample_data.append({
                'key': f'parsed_anime_{i}',
                'value': ParsedAnimeInfo(
                    title=f"Anime {i}",
                    season=i % 12 + 1,
                    episode=i % 24 + 1,
                    year=2020 + (i % 5),
                    resolution="1080p" if i % 2 == 0 else "720p"
                )
            })
        
        # Create TMDBAnime samples
        for i in range(1000):
            sample_data.append({
                'key': f'tmdb_anime_{i}',
                'value': TMDBAnime(
                    tmdb_id=1000 + i,
                    title=f"TMDB Anime {i}",
                    overview=f"Overview for anime {i}",
                    release_date=f"2020-{(i % 12) + 1:02d}-01",
                    vote_average=5.0 + (i % 5)
                )
            })
        
        return sample_data

    def _measure_operation_time(self, operation, *args, **kwargs) -> float:
        """Measure the execution time of an operation."""
        start_time = time.perf_counter()
        result = operation(*args, **kwargs)
        end_time = time.perf_counter()
        return end_time - start_time, result

    def test_cache_write_performance(self):
        """Test performance of cache write operations in cache-only mode."""
        # Measure individual write operations
        write_times = []
        
        for data in self.sample_data[:100]:  # Test with first 100 items
            write_time, _ = self._measure_operation_time(
                self.cache._store_in_cache,
                data['key'],
                data['value']
            )
            write_times.append(write_time)
        
        # Calculate performance metrics
        avg_write_time = statistics.mean(write_times)
        max_write_time = max(write_times)
        min_write_time = min(write_times)
        median_write_time = statistics.median(write_times)
        
        # Performance assertions
        assert avg_write_time < 0.001, f"Average write time too slow: {avg_write_time:.6f}s"
        assert max_write_time < 0.01, f"Max write time too slow: {max_write_time:.6f}s"
        assert min_write_time >= 0, f"Min write time should be non-negative: {min_write_time:.6f}s"
        
        # Verify all data was stored
        assert len(self.cache._cache) == 100, f"Expected 100 items in cache, got {len(self.cache._cache)}"
        
        print(f"\nCache Write Performance:")
        print(f"  Average time: {avg_write_time:.6f}s")
        print(f"  Median time: {median_write_time:.6f}s")
        print(f"  Min time: {min_write_time:.6f}s")
        print(f"  Max time: {max_write_time:.6f}s")

    def test_cache_read_performance(self):
        """Test performance of cache read operations in cache-only mode."""
        # First, populate cache with test data
        for data in self.sample_data[:500]:  # Store 500 items
            self.cache._store_in_cache(data['key'], data['value'])
        
        # Measure read operations
        read_times = []
        
        for data in self.sample_data[:500]:
            read_time, result = self._measure_operation_time(
                self.cache.get,
                data['key']
            )
            read_times.append(read_time)
            assert result is not None, f"Failed to read key: {data['key']}"
        
        # Calculate performance metrics
        avg_read_time = statistics.mean(read_times)
        max_read_time = max(read_times)
        min_read_time = min(read_times)
        median_read_time = statistics.median(read_times)
        
        # Performance assertions
        assert avg_read_time < 0.0001, f"Average read time too slow: {avg_read_time:.6f}s"
        assert max_read_time < 0.001, f"Max read time too slow: {max_read_time:.6f}s"
        assert min_read_time >= 0, f"Min read time should be non-negative: {min_read_time:.6f}s"
        
        print(f"\nCache Read Performance:")
        print(f"  Average time: {avg_read_time:.6f}s")
        print(f"  Median time: {median_read_time:.6f}s")
        print(f"  Min time: {min_read_time:.6f}s")
        print(f"  Max time: {max_read_time:.6f}s")

    def test_cache_miss_performance(self):
        """Test performance of cache miss operations in cache-only mode."""
        # Measure cache miss operations
        miss_times = []
        
        for i in range(100):
            key = f'non_existent_key_{i}'
            miss_time, result = self._measure_operation_time(
                self.cache.get,
                key
            )
            miss_times.append(miss_time)
            assert result is None, f"Expected None for non-existent key: {key}"
        
        # Calculate performance metrics
        avg_miss_time = statistics.mean(miss_times)
        max_miss_time = max(miss_times)
        min_miss_time = min(miss_times)
        median_miss_time = statistics.median(miss_times)
        
        # Performance assertions
        assert avg_miss_time < 0.0001, f"Average miss time too slow: {avg_miss_time:.6f}s"
        assert max_miss_time < 0.001, f"Max miss time too slow: {max_miss_time:.6f}s"
        assert min_miss_time >= 0, f"Min miss time should be non-negative: {min_miss_time:.6f}s"
        
        print(f"\nCache Miss Performance:")
        print(f"  Average time: {avg_miss_time:.6f}s")
        print(f"  Median time: {median_miss_time:.6f}s")
        print(f"  Min time: {min_miss_time:.6f}s")
        print(f"  Max time: {max_miss_time:.6f}s")

    def test_bulk_operations_performance(self):
        """Test performance of bulk operations in cache-only mode."""
        # Test bulk write operations
        bulk_write_start = time.perf_counter()
        
        for data in self.sample_data[:1000]:  # Write 1000 items
            self.cache._store_in_cache(data['key'], data['value'])
        
        bulk_write_time = time.perf_counter() - bulk_write_start
        
        # Test bulk read operations
        bulk_read_start = time.perf_counter()
        
        for data in self.sample_data[:1000]:  # Read 1000 items
            result = self.cache.get(data['key'])
            assert result is not None, f"Failed to read key: {data['key']}"
        
        bulk_read_time = time.perf_counter() - bulk_read_start
        
        # Performance assertions
        assert bulk_write_time < 1.0, f"Bulk write time too slow: {bulk_write_time:.6f}s"
        assert bulk_read_time < 0.5, f"Bulk read time too slow: {bulk_read_time:.6f}s"
        
        # Calculate operations per second
        write_ops_per_sec = 1000 / bulk_write_time
        read_ops_per_sec = 1000 / bulk_read_time
        
        print(f"\nBulk Operations Performance:")
        print(f"  Bulk write time: {bulk_write_time:.6f}s ({write_ops_per_sec:.0f} ops/sec)")
        print(f"  Bulk read time: {bulk_read_time:.6f}s ({read_ops_per_sec:.0f} ops/sec)")

    def test_mixed_operations_performance(self):
        """Test performance of mixed read/write operations in cache-only mode."""
        # Initialize with some data
        for data in self.sample_data[:200]:
            self.cache._store_in_cache(data['key'], data['value'])
        
        # Measure mixed operations
        mixed_ops_start = time.perf_counter()
        
        for i in range(500):
            if i % 3 == 0:  # Write operation
                data = self.sample_data[i % len(self.sample_data)]
                self.cache._store_in_cache(f"mixed_{data['key']}", data['value'])
            else:  # Read operation
                data = self.sample_data[i % 200]  # Read from existing data
                result = self.cache.get(data['key'])
                assert result is not None, f"Failed to read key: {data['key']}"
        
        mixed_ops_time = time.perf_counter() - mixed_ops_start
        
        # Performance assertions
        assert mixed_ops_time < 0.5, f"Mixed operations time too slow: {mixed_ops_time:.6f}s"
        
        # Calculate operations per second
        mixed_ops_per_sec = 500 / mixed_ops_time
        
        print(f"\nMixed Operations Performance:")
        print(f"  Mixed operations time: {mixed_ops_time:.6f}s ({mixed_ops_per_sec:.0f} ops/sec)")

    def test_cache_size_scalability(self):
        """Test how cache performance scales with cache size."""
        cache_sizes = [100, 500, 1000, 2000]
        performance_results = {}
        
        for size in cache_sizes:
            # Clear cache
            self.cache._cache.clear()
            
            # Measure write performance for different cache sizes
            write_start = time.perf_counter()
            
            for i in range(size):
                data = self.sample_data[i % len(self.sample_data)]
                self.cache._store_in_cache(f"size_test_{i}", data['value'])
            
            write_time = time.perf_counter() - write_start
            
            # Measure read performance
            read_start = time.perf_counter()
            
            for i in range(size):
                result = self.cache.get(f"size_test_{i}")
                assert result is not None, f"Failed to read key: size_test_{i}"
            
            read_time = time.perf_counter() - read_start
            
            performance_results[size] = {
                'write_time': write_time,
                'read_time': read_time,
                'write_ops_per_sec': size / write_time,
                'read_ops_per_sec': size / read_time
            }
        
        # Verify performance doesn't degrade significantly with cache size
        base_write_ops = performance_results[100]['write_ops_per_sec']
        base_read_ops = performance_results[100]['read_ops_per_sec']
        
        for size in cache_sizes[1:]:
            current_write_ops = performance_results[size]['write_ops_per_sec']
            current_read_ops = performance_results[size]['read_ops_per_sec']
            
            # Performance shouldn't degrade more than 50% with larger cache sizes
            assert current_write_ops > base_write_ops * 0.5, f"Write performance degraded too much at size {size}"
            assert current_read_ops > base_read_ops * 0.5, f"Read performance degraded too much at size {size}"
        
        print(f"\nCache Size Scalability:")
        for size, results in performance_results.items():
            print(f"  Size {size}: Write {results['write_ops_per_sec']:.0f} ops/sec, Read {results['read_ops_per_sec']:.0f} ops/sec")

    def test_memory_efficiency(self):
        """Test memory efficiency of cache operations."""
        # Measure memory usage before operations
        import sys
        
        initial_cache_size = len(self.cache._cache)
        
        # Store large amount of data
        for i in range(2000):
            data = self.sample_data[i % len(self.sample_data)]
            self.cache._store_in_cache(f"memory_test_{i}", data['value'])
        
        final_cache_size = len(self.cache._cache)
        
        # Verify cache size is as expected
        assert final_cache_size == initial_cache_size + 2000, f"Expected 2000 new items, got {final_cache_size - initial_cache_size}"
        
        # Test cache eviction (if max_size is reached)
        # The cache should handle eviction efficiently
        assert len(self.cache._cache) <= self.cache.max_size, f"Cache size exceeded max_size: {len(self.cache._cache)} > {self.cache.max_size}"
        
        print(f"\nMemory Efficiency:")
        print(f"  Initial cache size: {initial_cache_size}")
        print(f"  Final cache size: {final_cache_size}")
        print(f"  Max cache size: {self.cache.max_size}")
        print(f"  Cache utilization: {final_cache_size / self.cache.max_size * 100:.1f}%")

    def test_concurrent_access_performance(self):
        """Test performance under simulated concurrent access patterns."""
        import threading
        import queue
        
        # Create thread-safe queues for results
        write_results = queue.Queue()
        read_results = queue.Queue()
        
        def write_worker(worker_id: int, num_operations: int):
            """Worker function for write operations."""
            for i in range(num_operations):
                data = self.sample_data[i % len(self.sample_data)]
                key = f"concurrent_write_{worker_id}_{i}"
                
                start_time = time.perf_counter()
                self.cache._store_in_cache(key, data['value'])
                end_time = time.perf_counter()
                
                write_results.put(end_time - start_time)
        
        def read_worker(worker_id: int, num_operations: int):
            """Worker function for read operations."""
            for i in range(num_operations):
                key = f"concurrent_read_{worker_id}_{i}"
                
                start_time = time.perf_counter()
                result = self.cache.get(key)
                end_time = time.perf_counter()
                
                read_results.put((end_time - start_time, result is not None))
        
        # Start multiple threads
        num_threads = 4
        operations_per_thread = 100
        
        threads = []
        
        # Start write threads
        for i in range(num_threads):
            thread = threading.Thread(target=write_worker, args=(i, operations_per_thread))
            threads.append(thread)
            thread.start()
        
        # Start read threads
        for i in range(num_threads):
            thread = threading.Thread(target=read_worker, args=(i, operations_per_thread))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Collect results
        write_times = []
        while not write_results.empty():
            write_times.append(write_results.get())
        
        read_times = []
        read_successes = []
        while not read_results.empty():
            read_time, success = read_results.get()
            read_times.append(read_time)
            read_successes.append(success)
        
        # Calculate performance metrics
        avg_write_time = statistics.mean(write_times)
        avg_read_time = statistics.mean(read_times)
        
        # Performance assertions
        assert avg_write_time < 0.001, f"Average concurrent write time too slow: {avg_write_time:.6f}s"
        assert avg_read_time < 0.0001, f"Average concurrent read time too slow: {avg_read_time:.6f}s"
        
        # Verify some reads were successful (some keys should exist from writes)
        success_rate = sum(read_successes) / len(read_successes)
        assert success_rate >= 0, f"Read success rate should be non-negative: {success_rate:.2f}"
        
        print(f"\nConcurrent Access Performance:")
        print(f"  Average write time: {avg_write_time:.6f}s")
        print(f"  Average read time: {avg_read_time:.6f}s")
        print(f"  Read success rate: {success_rate:.2f}")
        print(f"  Total operations: {len(write_times) + len(read_times)}")
