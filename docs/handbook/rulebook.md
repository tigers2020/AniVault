# AniVault Rulebook Summary

This condensed rulebook centralizes the operational guidance that previously lived in `.cursor/rules`. Each section links back to the authoritative source so you can dive deeper when needed.

## Core Security (`.cursor/rules/01_core_security.mdc`)
- Enforce input validation, output encoding, and least privilege for all file and network access.
- Treat TMDB API secrets and local filesystem paths as sensitive; never log secrets or write outside approved roots.
- Provide explicit error handling paths for authentication, rate limiting, and corrupted media payloads.

## Python Development (`.cursor/rules/02_python_development.mdc`)
- Require type hints on public functions, dataclasses for structured data, and Google-style docstrings for complex logic.
- Avoid magic values: centralize enums and constants under `src/anivault/shared/constants/`.
- Prefer pure functions and dependency injection to keep pipeline stages testable; raise domain-specific exceptions on failure.

## System Standards (`.cursor/rules/03_system_standards.mdc`)
- Default all file and console I/O to UTF-8 with graceful Windows fallbacks.
- Use structured logging (JSON) via the shared logging helpers; include correlation IDs for multi-stage pipeline runs.
- Keep environment toggles centralized in `config/` and reflect overrides in diagnostics output.

## Quality Assurance (`.cursor/rules/04_quality_assurance.mdc`)
- Maintain >=95% coverage on pipeline modules and exercise success plus failure paths in tests.
- Require benchmark or profiling data for performance-impacting changes (see `tests/benchmarks/`).
- Automate regression checks with pytest markers and ensure snapshot data lives under `tests/data/`.

## Project Management (`.cursor/rules/05_project_management.mdc`)
- Work in task-driven slices: define scope, acceptance criteria, and rollback steps before coding.
- Document state in progress logs and tie user stories to CLI commands or scripts that verify the flow.
- Keep release notes updated with migration instructions for library or schema changes.

## File Processing (`.cursor/rules/06_file_processing.mdc`)
- Normalize filenames, encodings, and metadata before matching; no stage may mutate original media files.
- Cache expensive computations (hashing, TMDB lookups) and respect concurrency limits defined in pipeline configs.
- Validate parser outputs with schema checks before handing results to organizers.

## GUI/CLI Extensions (`.cursor/rules/07_pyside6_gui.mdc`)
- Even though the primary interface is Typer CLI, any optional GUI layer must consume the same services and avoid duplicate logic.
- Keep presentation code side-effect free; delegate file operations to the core pipeline modules.

## TMDB Integration (`.cursor/rules/08_tmdb_api.mdc`)
- Centralize TMDB communication through `services/tmdb_client.py`; throttle requests and cache metadata aggressively.
- Implement fallback strategies when TMDB metadata is incomplete, including fuzzy title matching and manual overrides.
- Log all network anomalies with enough context to reproduce (endpoint, parameters, rate-limit status).

## Taskmaster & Self-Improve Guides
- **Taskmaster rules**: `.cursor/rules/taskmaster/always.mdc`, `.cursor/rules/taskmaster/dev_workflow.mdc`, `.cursor/rules/taskmaster/taskmaster.mdc` - follow the proof-driven loop: plan, implement, verify, and log evidence for each high-risk task.
- **Global Cursor guardrails**: `.cursor/rules/cursor_rules.mdc` - prefer `rg`, avoid destructive commands without explicit instruction, and keep diff outputs tidy.
- **Self reflection**: `.cursor/rules/self_improve.mdc` - capture lessons learned and feed them into future checklists.

## Personas (`.cursor/rules/personas/`)
Eight expert personas cover CLI architecture, metadata matching, data quality, GUI, Windows packaging, QA automation, security/privacy, and open-source compliance. Pull them into design reviews when their domain expertise is relevant; each persona file includes probing questions and acceptance checklists.

For the full details, keep the original `.cursor/rules` files as the authoritative source; this summary keeps the essentials at your fingertips while working inside AniVault.
