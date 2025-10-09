# AniVault Handbook

The AniVault handbook unifies architecture notes, development workflows, and operational rules so contributors can ramp up without hunting through multiple folders.

## Quick Map
- [Architecture Overview](architecture.md)
- [Development Guide](development_guide.md)
- [Team Protocol](development_protocol.md)
- [Rulebook Summary](rulebook.md)

## How to Use This Handbook
- **Start with the architecture** to understand the pipeline (scan -> parse -> match -> organize).
- **Follow the development guide** for local setup, CLI commands, troubleshooting, and release operations.
- **Consult the team protocol** when coordinating multi-person work, proof-driven development flows, or MCP-assisted sessions.
- **Review the rulebook** before coding to stay aligned with the latest standards (type hints, UTF-8, QA expectations, TMDB usage, etc.).

## Legacy Redirects
Historical documents such as `DEVELOPMENT_GUIDE.md`, `ARCHITECTURE_ANIVAULT.md`, and `DEVELOPMENT_PROTOCOL_ANIVAULT.md` now point here. Update any remaining references to use the handbook paths directly.

## Supporting References
Additional deep dives remain in `docs/`:
- Testing, profiling, and benchmark results (`test-optimization-summary.md`, `performance-baseline-results.md`).
- TMDB credentials, validation results, and packaging notes (`tmdb-api-key-guide.md`, `tmdb-api-validation-results.md`, `pyinstaller-poc-results.md`).
- Proof-driven development resources (`_proof_driven_dev_mode.md`, `EXPERT_OPINIONS_LOG_PROTOCOL.md`).

Keep this directory as the single launch point for AniVault knowledge. When new standards or flows are introduced, update the relevant handbook page and link any long-form evidence from the supporting references section.
