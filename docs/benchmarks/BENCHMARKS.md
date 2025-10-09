# AniVault Benchmark Suite

## Overview

This document describes the benchmark suite for AniVault, designed to track performance regressions and establish performance baselines.

## Running Benchmarks

### Quick Start

```bash
# Run all benchmarks
pytest tests/benchmarks/ --benchmark-only

# Run with verbose output
pytest tests/benchmarks/ --benchmark-only -v --benchmark-verbose

# Save results
pytest tests/benchmarks/ --benchmark-only --benchmark-save=my_run

# Compare with baseline
pytest tests/benchmarks/ --benchmark-only --benchmark-compare=baseline
```

### Installation

Benchmarks require `pytest-benchmark`:

```bash
pip install pytest-benchmark
```

Or install with dev dependencies:

```bash
pip install -e ".[dev]"
```

## Benchmark Coverage

### 1. Directory Scanning (`test_scan.py`)

- **test_benchmark_scan_directory**: Scan 100 files
- **test_benchmark_scan_large_directory**: Scan 1000 files

**Baseline (Windows, Python 3.11)**:
- 100 files: ~10.25ms (97.6 ops/s)
- 1000 files: ~14.71ms (68.0 ops/s)

### 2. Filename Parsing (`test_parse.py`)

- **test_benchmark_parse_filename**: Single filename parse
- **test_benchmark_parse_batch**: Batch of 5 filenames
- **test_benchmark_parse_complex_filename**: Complex filename with many elements

**Baseline (Windows, Python 3.11)**:
- Single: ~471µs (2,120 ops/s)
- Batch: ~2.70ms (370 ops/s)
- Complex: ~1.79ms (559 ops/s)

### 3. Cache Operations (`test_cache.py`)

- **test_benchmark_cache_set**: Cache write (serialization + DB insert)
- **test_benchmark_cache_get**: Cache read (DB query + deserialization)
- **test_benchmark_cache_roundtrip**: Full set + get cycle
- **test_benchmark_cache_batch_operations**: 100 items batch (set + get)

**Baseline (Windows, Python 3.11)**:
- Set: ~147µs (6,791 ops/s)
- Roundtrip: ~195µs (5,123 ops/s)
- Batch (100): ~19.06ms (52.5 ops/s)

## Baseline Management

### Creating Baseline

After implementing a significant optimization or at the start of a release cycle:

```bash
pytest tests/benchmarks/ --benchmark-only --benchmark-save=baseline
```

This creates `.benchmarks/<platform>/baseline.json`.

### Comparing with Baseline

```bash
# Compare and display differences
pytest tests/benchmarks/ --benchmark-only --benchmark-compare=baseline

# Fail if performance degrades by >5%
pytest tests/benchmarks/ --benchmark-only --benchmark-compare=baseline --benchmark-compare-fail=min:5%
```

### Git Management

- **Committed**: `.benchmarks/baseline.json` (tracking performance over time)
- **Ignored**: `.benchmarks/*` (local benchmark results)

## CI Integration

GitHub Actions automatically runs benchmarks on:
- Pull requests to `main`/`master`
- Pushes to `main`/`master`
- Manual workflow dispatch

See `.github/workflows/benchmark.yml` for configuration.

### Benchmark Results in PRs

The CI posts benchmark results as PR comments:

```markdown
## 📊 Benchmark Results

| Test | Mean | StdDev | Min | Max |
|------|------|--------|-----|-----|
| test_benchmark_scan_directory | 10.25ms | 0.72ms | 8.25ms | 11.86ms |
| ... | ... | ... | ... | ... |
```

## Performance Targets

| Operation | Target | Acceptable Range |
|-----------|--------|------------------|
| Scan (100 files) | <15ms | 8-20ms |
| Parse (single) | <500µs | 300-700µs |
| Cache set | <200µs | 100-300µs |
| Cache get | N/A | <150µs |

## Troubleshooting

### "pytest-benchmark not found"

Install it:
```bash
pip install pytest-benchmark
```

### Async Benchmark Issues

For async functions, use `pytest-asyncio` integration:

```python
@pytest.mark.asyncio
async def test_benchmark_async(benchmark):
    @benchmark
    async def run():
        return await my_async_function()
```

### Platform Differences

Baseline results are platform-specific. Benchmarks on Windows, macOS, and Linux will have different absolute values. Focus on **relative changes** (regression vs improvement) rather than absolute numbers.

## Contributing

When adding new benchmarks:
1. Place in `tests/benchmarks/test_*.py`
2. Follow existing naming convention: `test_benchmark_<operation>`
3. Include docstring explaining what's measured
4. Verify with assertions (e.g., `assert result is not None`)
5. Run locally and ensure it completes in <2s
6. Update this document with baseline numbers

## References

- [pytest-benchmark documentation](https://pytest-benchmark.readthedocs.io/)
- [AniVault Development Protocol](../protocols/DEVELOPMENT_PROTOCOL.md)
- [Performance Optimization Guide](../performance/cache_benchmark.md)

