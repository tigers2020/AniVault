# AniVault Architecture

AniVault is a Typer-based CLI that automates the organization of anime libraries. The pipeline is intentionally modular so each stage can be reasoned about, benchmarked, and rolled back independently.

## System Overview
- **Entry Point**: `src/anivault/cli/main.py` exposes commands for scan, match, organize, verify, and rollback.
- **Core Pipeline**: `src/anivault/core/pipeline` implements a staged flow: `scanner` → `parser` → `match` (via services) → `organizer` → `rollback_manager`.
- **Services Layer**: `src/anivault/services` handles TMDB access, caching, rate limiting, and metadata enrichment.
- **Shared Utilities**: `src/anivault/shared` stores constants, error types, and reusable helpers (logging, filesystem operations).

```
┌────────┐   ┌────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐
│  Scan  │─▶│  Parse  │─▶│ Metadata   │─▶│ Organize   │─▶ │ Rollback   │
│ (CLI)  │   │ Stage  │  │ Matching    │   │ Stage      │   │ / Verify   │
└────────┘   └────────┘   └────────────┘   └────────────┘   └────────────┘
    │             │              │               │               │
    ▼             ▼              ▼               ▼               ▼
 file system   parser models   TMDB client   filesystem ops   audit logs
```

## Key Modules
- `cli/scan_handler.py`: collects target directories and orchestrates scan jobs.
- `core/pipeline/scanner.py`: walks directories, yielding `ScannedFile` objects with metadata hints.
- `core/pipeline/parser.py`: delegates to `anitopy` and fallback parsers to normalize filenames.
- `services/tmdb_client.py`: wraps TMDB API calls with caching and rate limiting.
- `core/organizer.py`: plans moves/copies without mutating source files; produces rollback scripts.
- `core/rollback_manager.py`: records and replays rollback operations.
- `cli/verify_handler.py`: validates end-state against expectations and stored metadata hashes.

## Rate Limiting Architecture
For detailed information about TMDB API rate limiting, concurrency control, and state management, see [TMDB Rate Limiting Architecture](../development/tmdb-rate-limiting-architecture.md).

## Data Contracts
- Parsed files share `AnimeFile` dataclasses defined in `core/models.py` and `parser/models.py`.
- Match results use scoring structs in `core/matching/scoring.py`, allowing deterministic selection and auditing.
- Organizer plans are serialized to JSON (see `cli_magic_values.json`) to support dry runs and replay.

## Operational Concerns
- **Logging**: All stages emit structured logs via `shared/logging` helpers; CLI toggles verbosity through environment variables.
- **Caching**: API and filesystem caches live in `cache/` (runtime) and `data/` (seeded). Clean-up scripts are under `scripts/`.
- **Concurrency**: Parallel scanning uses worker pools in `core/pipeline/parallel_scanner.py`; configuration resides in `config/config.toml`.
- **Packaging**: PyInstaller specs live in documentation (`docs/pyinstaller-poc-results.md`). Windows executables bootstrap the Typer entrypoint.

## Extension Points
- Additional parsers can be registered in `core/pipeline/parser.py` by implementing the parser protocol.
- Alternative metadata providers should extend the services layer and reuse the `metadata_enricher` interface.
- GUI experiments must consume the CLI handlers instead of duplicating pipeline logic (see Rulebook section on GUI extensions).

Keep this document updated when the pipeline sequence, module responsibilities, or cross-cutting concerns (logging, caching, packaging) change.
