# Cache Performance Benchmark Report

**Date**: 2025-10-06
**Environment**: Windows 10, Python 3.11.9, pytest 8.4.2
**Test File**: `tests/performance/bench_cache_db.py`
**Duration**: 16.39 seconds

---

## Executive Summary

Performance benchmarks comparing **SQLiteCacheDB** and **JSONCacheV2** implementations across four scenarios: single read/write operations, bulk operations, and concurrent access patterns.

### Key Findings

- **SQLite dominates sequential operations**: 2-9x faster for single read/write
- **JSON excels in concurrent scenarios**: 1.4x faster with 10 threads
- **Both implementations are highly reliable**: 0% error rate across all tests
- **SQLite recommended for high-volume sequential**: Better for batch processing
- **JSON recommended for concurrent workloads**: Better thread safety without locks

---

## Test Results

### 1. Single Write Performance (1,000 items)

Measures average time to write 1,000 cache items sequentially.

| Metric | SQLiteCacheDB | JSONCacheV2 | Winner |
|--------|---------------|-------------|--------|
| **Total Time** | 0.2894s | 0.7155s | ✅ SQLite |
| **Time per Item** | 0.2894ms | 0.7155ms | ✅ SQLite (2.5x faster) |

**Analysis**: SQLite's batched transaction model provides superior write performance for sequential operations.

---

### 2. Single Read Performance (1,000 items)

Measures average time to read 1,000 cache items sequentially from pre-populated cache.

| Metric | SQLiteCacheDB | JSONCacheV2 | Winner |
|--------|---------------|-------------|--------|
| **Total Time** | 0.1203s | 1.0533s | ✅ SQLite |
| **Time per Item** | 0.1203ms | 1.0533ms | ✅ SQLite (8.8x faster) |

**Analysis**: SQLite's indexed queries significantly outperform JSON file I/O for read operations. The gap is larger than write operations due to SQLite's query optimization.

---

### 3. Bulk Write Performance (10,000 items)

Measures throughput (TPS) when writing 10,000 items in bulk.

| Metric | SQLiteCacheDB | JSONCacheV2 | Winner |
|--------|---------------|-------------|--------|
| **Total Time** | 3.6962s | 7.9830s | ✅ SQLite |
| **Throughput (TPS)** | 2,705.45 | 1,252.66 | ✅ SQLite (2.2x faster) |

**Analysis**: SQLite maintains consistent performance at scale. JSON overhead increases with data volume due to file system operations.

---

### 4. Concurrent Operations (10 threads, 1,000 ops)

Tests 10 threads performing mixed read/write operations simultaneously.

| Metric | SQLiteCacheDB | JSONCacheV2 | Winner |
|--------|---------------|-------------|--------|
| **Total Time** | 0.2770s | 0.1955s | ✅ JSON |
| **Throughput** | 3,610 ops/sec | 5,114 ops/sec | ✅ JSON (1.4x faster) |
| **Errors** | 0 (0.00%) | 0 (0.00%) | Tie |

**Analysis**: **Surprising result!** JSONCacheV2 outperforms SQLite in concurrent scenarios, likely due to:
- No database locking overhead
- Parallel file I/O capabilities
- Independent cache file writes reduce contention

---

## Performance Characteristics

### SQLiteCacheDB

**Strengths**:
- ✅ Excellent sequential read performance (8.8x faster)
- ✅ Superior sequential write performance (2.5x faster)
- ✅ Consistent bulk operation throughput (2,705 TPS)
- ✅ ACID guarantees with WAL mode
- ✅ Query optimization and indexing

**Weaknesses**:
- ⚠️ Slower in highly concurrent scenarios
- ⚠️ Database locking can become a bottleneck
- ⚠️ Requires proper connection management

**Recommended Use Cases**:
- High-volume sequential processing
- Batch operations with many items
- Complex queries and filtering
- Single-threaded or low-concurrency environments

---

### JSONCacheV2

**Strengths**:
- ✅ **Best concurrent performance** (5,114 ops/sec)
- ✅ Lock-free concurrent writes
- ✅ Simple file-based architecture
- ✅ Easy to inspect and debug (human-readable)

**Weaknesses**:
- ⚠️ Slower sequential reads (8.8x slower)
- ⚠️ Slower sequential writes (2.5x slower)
- ⚠️ Lower bulk throughput (1,253 TPS)
- ⚠️ File system overhead increases with scale

**Recommended Use Cases**:
- Multi-threaded applications with high concurrency
- Real-time cache updates from multiple sources
- Development and debugging (human-readable format)
- Distributed systems with minimal shared state

---

## Recommendations

### When to Use SQLiteCacheDB

Use SQLiteCacheDB when:
- Processing large batches of items sequentially
- Query performance is critical
- ACID guarantees are required
- Single-threaded or low-concurrency environment

**Example**: Batch processing 10,000+ anime files in a CLI tool.

---

### When to Use JSONCacheV2

Use JSONCacheV2 when:
- Multiple threads/processes access cache simultaneously
- Real-time updates are frequent
- Simple key-value lookups (no complex queries)
- Human-readable cache format is beneficial

**Example**: GUI application with multiple concurrent TMDB API requests.

---

### Hybrid Approach

**Consider using both** in a hybrid configuration:
- **SQLiteCacheDB** for persistent, long-term cache
- **JSONCacheV2** for temporary, high-concurrency cache
- Promote frequently accessed items from JSON to SQLite

---

## Test Configuration

### Environment
- **OS**: Windows 10
- **Python**: 3.11.9
- **Test Framework**: pytest 8.4.2
- **Markers**: `@pytest.mark.benchmark`

### Test Data
- **Small Dataset**: 1,000 items (for single operations)
- **Large Dataset**: 10,000 items (for bulk operations)
- **Concurrency**: 10 threads with mixed read/write operations

### Cache Configuration
- **SQLite**: WAL mode enabled, auto-checkpoint
- **JSON**: orjson serialization, separate directories for search/details
- **TTL**: 24 hours for all test entries

---

## Conclusion

Both cache implementations demonstrate excellent reliability (0% error rate) but serve different use cases:

- **SQLiteCacheDB wins for sequential workloads** with superior read/write performance and bulk throughput
- **JSONCacheV2 wins for concurrent workloads** with 1.4x better multi-threaded performance
- **Choose based on your access pattern**: Sequential batch processing → SQLite; Concurrent real-time → JSON

---

## Appendix: Raw Test Output

```
tests/performance/bench_cache_db.py::TestSingleOperations::test_single_write_sqlite PASSED
SQLite write: 0.2894s total, 0.2894ms per item

tests/performance/bench_cache_db.py::TestSingleOperations::test_single_write_json PASSED
JSON write: 0.7155s total, 0.7155ms per item

tests/performance/bench_cache_db.py::TestSingleOperations::test_single_read_sqlite PASSED
SQLite read: 0.1203s total, 0.1203ms per item

tests/performance/bench_cache_db.py::TestSingleOperations::test_single_read_json PASSED
JSON read: 1.0533s total, 1.0533ms per item

tests/performance/bench_cache_db.py::TestBulkOperations::test_bulk_write_sqlite PASSED
SQLite bulk write: 3.6962s total, 2705.45 TPS

tests/performance/bench_cache_db.py::TestBulkOperations::test_bulk_write_json PASSED
JSON bulk write: 7.9830s total, 1252.66 TPS

tests/performance/bench_cache_db.py::TestConcurrency::test_concurrent_operations_sqlite PASSED
SQLite concurrent: 0.2770s, 1000 ops, 3610.23 ops/sec, 0 errors (0.00%)

tests/performance/bench_cache_db.py::TestConcurrency::test_concurrent_operations_json PASSED
JSON concurrent: 0.1955s, 1000 ops, 5114.20 ops/sec, 0 errors (0.00%)

======================== 8 passed in 16.39s =========================
```

---

**Generated by**: Task 6 - Performance Benchmark
**Repository**: AniVault
**Branch**: tmdb-cache-db
