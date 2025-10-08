# AniVault Development Protocol

Use this protocol to coordinate collaborative work, especially when tasks involve multiple pipeline stages or require MCP assistants.

## Roles & Personas
- **Python Backend Lead (Yoon)** – CLI architecture, pipeline composition
- **Metadata Matching Specialist (Sato)** – TMDB heuristics, scoring rules
- **Data Quality Steward (Kim)** – schema validation, catalog consistency
- **GUI/UX Advocate (Hartman)** – optional PySide6 experiments, CLI ergonomics
- **Windows Packaging Owner (Park)** – PyInstaller builds, distribution testing
- **QA Automation Lead (Choi)** – test strategy, coverage, regression triage
- **Security & Privacy Officer (Okoye)** – secrets handling, logging policy
- **Open Source Compliance (Jung)** – licensing, attribution, third-party risk

Invite relevant personas to planning discussions and capture their sign-off in task notes.

## Proof-Driven Workflow
1. **Discover**: Clarify requirements, risk level, and acceptance criteria. Draft a lightweight PRD if scope is unclear.
2. **Plan**: Break work into verifiable checkpoints; outline tests, benchmarks, and rollback steps.
3. **Implement**: Code in small loops. For complex changes, use MCP Task Master to manage TODOs and Serena for codebase queries.
4. **Verify**: Run targeted tests, collect logs, and store evidence (coverage reports, benchmark output).
5. **Record**: Summarize outcomes in the issue or task log, including any follow-ups or debt.

## MCP Assistant Playbook
- **Task Master AI**: seed project plans, expand requirements, monitor progress.
- **Serena**: inspect symbols, search patterns, and surface caller/callee graphs.
- **Sequential Thinking**: capture reasoning chains for ambiguous TMDB matches or heuristic adjustments.

Example session:
```bash
mcp_task-master-ai_initialize_project --projectRoot . --rules cursor
mcp_task-master-ai_parse_prd --input docs/tasks/new_feature_prd.md --numTasks 10
mcp_serena_find_symbol --name_path "OrganizePlan" --relative_path src/anivault
mcp_sequential-thinking_sequentialthinking --thought "Evaluate TMDB score thresholds" --nextThoughtNeeded true
```

## Checklists
- **Kickoff**: personas notified, requirements classified (Low/Med/High risk), tooling access ready.
- **Design Review**: architecture impacts documented, new configs registered, rollback strategy drafted.
- **Implementation**: code adheres to rulebook, migrations included, docs updated.
- **Verification**: tests executed, benchmarks captured if relevant, manual steps recorded.
- **Release**: changelog updated, packaging verified, rollback artifacts archived.

## Risk Levels
- **Low**: single CLI command tweak, localized parser adjustments; 1-2 personas.
- **Medium**: cross-stage impact (parser + organizer), API behavior changes; involve QA and packaging leads.
- **High**: new pipeline stage, TMDB contract shift, filesystem migrations; run multiple Sequential Thinking rounds and secure leadership approval.

Document decisions and remaining questions in `docs/EXPERT_OPINIONS_LOG_PROTOCOL.md` or associated task logs. This keeps the knowledge trail intact for future audits and onboarding.
