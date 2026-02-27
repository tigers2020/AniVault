# AGENTS.md

## Cursor Cloud specific instructions

### Overview

AniVault is a Python CLI/GUI tool for organizing anime files using TMDB metadata. The primary interface is a Typer CLI (`anivault`), with an optional PySide6 GUI.

### Package Manager

This project uses **uv** (lockfile: `uv.lock`). Install dependencies with:

```bash
uv sync --extra dev
```

This also installs `pytest-timeout` (required by pyproject.toml's `timeout = 300` setting but not listed in `[project.optional-dependencies.dev]`). Run `uv pip install pytest-timeout` after `uv sync` if tests fail with "Unknown config option: timeout".

### Environment Setup

- Copy `env.template` to `.env` before running. The `TMDB_API_KEY` is required for matching functionality but not for basic CLI operations.
- Config template at `config/config.toml.template` — copy to `config/config.toml` if needed.

### Known Issue: Missing `anivault.services.cache` module

The `src/anivault/services/__init__.py` imports `from .cache import SQLiteCacheDB`, but no `cache.py` or `cache/` directory exists under `services/`. This was lost during the circular-imports refactoring (commit `06aef29`). As a result, **all imports of the `anivault` package fail** with `ModuleNotFoundError: No module named 'anivault.services.cache'`.

This means `anivault --help`, `anivault scan`, and all CLI/GUI commands crash on startup. Until this module is restored, the application cannot run.

### Lint / Type-check / Test

| Command | Notes |
|---|---|
| `uv run ruff check src/` | Linting (13 pre-existing warnings, mostly style) |
| `uv run mypy src/` | Type checking (20 pre-existing errors, mostly GUI stubs) |
| `uv run pytest tests/` | No `tests/` directory exists in the repo currently |

### GUI

The PySide6 GUI requires a display server. In headless environments, the CLI is the expected interface. Launch GUI via `python run_gui.py`.

### Pre-commit

Pre-commit hooks are configured in `.pre-commit-config.yaml` (ruff, mypy, bandit, pytest-fast, circular import detection). Install with `pre-commit install`.
