# AniVault Development Guide

This guide walks new contributors through environment setup, daily workflows, and troubleshooting tips. Pair it with `handbook/rulebook.md` for policy-level details.

## Prerequisites
- Python 3.9+ (3.11 recommended)
- Git, pip, and optionally Poetry
- TMDB API key stored in `.env` (`TMDB_API_KEY=...`)
- Windows, macOS, or Linux with at least 8GB RAM for large batch runs

## Environment Setup
```bash
# Clone
git clone https://github.com/yourusername/anivault.git
cd AniVault

# Virtualenv
python -m venv venv
venv\\Scripts\\activate    # Windows
source venv/bin/activate  # macOS/Linux

# Install project and dev deps
pip install -e .
pip install -e .[dev]
# or: poetry install && poetry shell
```

## CLI Essentials
```bash
# Show available commands
anivault --help

# Scan a directory (dry run)
anivault scan "D:/Anime" --dry-run

# Full pipeline run
anivault run "D:/Anime" --tmdb-language=ja --profile=default

# Organize with an existing plan
anivault organize plan.json --apply

# Roll back the last plan
anivault rollback last
```

Environment toggles live in `.env` and `config/config.toml`; prefer editing config files over hard-coded changes. Use `ANIVAULT_LOG_LEVEL=DEBUG` for verbose logs and `ANIVAULT_CACHE_DIR` to isolate caches during tests.

## Testing & Quality
```bash
pytest                   # unit + integration tests
pytest -m "not slow"     # quick feedback loop
pytest tests/benchmarks  # throughput benchmarks
ruff check src tests     # linting
mypy src                 # type checking
```

Generate coverage with `pytest --cov=src --cov-report=term-missing` and review artifacts in `htmlcov/`. Performance scripts live in `scripts/` (e.g., `run_memory_profile.py`).

## Troubleshooting
- **TMDB errors**: verify the API key, check rate-limit headers, and consult `logs/anivault.log`.
- **Parser mismatches**: run `anivault match --inspect` to see scoring details; adjust normalization rules if necessary.
- **File operations blocked**: ensure destinations are writeable and not locked by other processes; use `--dry-run` to preview.
- **Packaging issues**: follow `docs/pyinstaller-poc-results.md` and clean build artifacts (`scripts/clean_build.py` if present).

## Workflow Tips
- Work in topic branches, commit frequently with conventional commit prefixes (`feat`, `fix`, `docs`, etc.).
- Update documentation alongside user-facing changes; link proof artifacts (benchmark logs, test runs) in pull requests.
- Capture rollback plans for every organize run; store `plan.json` artifacts in `logs/` for traceability.

Stay aligned with the AniVault handbook: architecture for context, protocol for collaboration, and rulebook for coding standards.
