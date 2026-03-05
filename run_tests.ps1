# Run unit tests (sequential, no coverage for speed ~1-2 min).
# Usage: .\run_tests.ps1 [extra args]
# With coverage (~5+ min): .\run_tests.ps1 --cov --cov-report=term-missing
# Full coverage with 90% gate: .\run_tests.ps1 --cov --cov-report=term-missing --cov-fail-under=90

pytest tests/unit/ -q -o addopts="-q --tb=short --strict-markers --strict-config -p no:pytest-qt --ignore=tests/gui/ --ignore=tests/benchmarks_disabled/ --ignore=tests/core/file_grouper/test_group_name_manager_benchmark.py --ignore=tests/unit/test_subtitle_matcher_benchmark.py --ignore=tests/unit/test_title_matcher_accuracy_benchmark.py" @args
