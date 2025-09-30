# AniVault Suggested Commands

## Daily Development Commands

### Project Status
```bash
# Check current tasks
task-master list

# Get next task to work on
task-master next

# View specific task details
task-master show <task_id>
```

### Development Workflow
```bash
# Start development session
python -m venv venv
venv\Scripts\activate
pip install -e ".[dev]"

# Check code quality
ruff check src/ tests/
ruff format src/ tests/
mypy src/

# Run tests
pytest

# Mark task complete
task-master set-status --id=<task_id> --status=done
```

### Task Management
```bash
# Expand complex tasks
task-master expand --id=<task_id>

# Update task progress
task-master update-subtask --id=<subtask_id> --prompt="Implementation notes"

# View task complexity
task-master analyze-complexity
```

### Build and Test
```bash
# Build executable
pyinstaller --onefile --name anivault src/anivault/cli/main.py

# Test executable
./dist/anivault --help

# Verify components
./dist/anivault --verify-anitopy
./dist/anivault --verify-crypto
./dist/anivault --verify-tmdb
```

### Git Workflow
```bash
# Create feature branch
git checkout -b feature/new-feature

# Commit changes
git add .
git commit -m "feat: implement new feature"

# Push changes
git push origin feature/new-feature
```

### Development Scripts
```bash
# Run setup
python scripts/setup.py

# Test TMDB API
python scripts/test_tmdb_api.py

# Development utilities
python scripts/dev.py
```

### System Commands (Windows)
```bash
# Directory navigation
cd F:\Python_Projects\AniVault
dir
cd src\anivault

# File operations
type README.md
copy file.txt backup.txt
del temp_file.txt

# Search operations
findstr "class" *.py
where python
```

### Quality Assurance
```bash
# Full quality check
ruff check src/ tests/ && ruff format src/ tests/ && mypy src/ && pytest

# Coverage report
pytest --cov=src --cov-report=html

# Performance test
pytest -m "not slow"
```

### TaskMaster Advanced
```bash
# Analyze project complexity
task-master analyze-complexity --research

# Expand all tasks
task-master expand --all --research

# Update multiple tasks
task-master update --from=<task_id> --prompt="Context update"
```

## Quick Reference
- **Current Tag**: w5-w6-scan-parse-pipeline
- **Total Tasks**: 8 main tasks, 40 subtasks
- **Next Focus**: Pipeline architecture implementation
- **Key Files**: `src/anivault/core/bounded_queue.py`, `src/anivault/cli/main.py`
