# AniVault Development Commands

## Essential Commands

### Project Setup
```bash
# Create virtual environment
python -m venv venv

# Windows activation
venv\Scripts\activate

# Install in development mode
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"
```

### Code Quality Commands
```bash
# Lint code
ruff check src/ tests/

# Format code
ruff format src/ tests/

# Type checking
mypy src/

# All quality checks
ruff check src/ tests/ && ruff format src/ tests/ && mypy src/
```

### Testing Commands
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest -m unit                    # Unit tests only
pytest -m integration             # Integration tests only
pytest -m "not slow"              # Skip slow tests

# Run specific test file
pytest tests/test_cli_entry_point.py
```

### Build Commands
```bash
# Development build
pip install -e .

# PyInstaller build
pyinstaller --onefile --name anivault src/anivault/cli/main.py

# Test executable
./dist/anivault --help
```

### TaskMaster Commands
```bash
# View current tasks
task-master list

# Get next task
task-master next

# View specific task
task-master show <task_id>

# Mark task complete
task-master set-status --id=<task_id> --status=done

# Expand task into subtasks
task-master expand --id=<task_id>
```

### Git Commands (Windows)
```bash
# Basic git operations
git status
git add .
git commit -m "feat: add new feature"
git push origin feature-branch

# Branch management
git checkout -b feature/new-feature
git checkout main
git merge feature/new-feature
```

### System Commands (Windows)
```bash
# Directory operations
dir                    # List directory contents
cd path\to\directory   # Change directory
mkdir new_folder       # Create directory
rmdir folder_name      # Remove directory

# File operations
type filename.txt      # Display file contents
copy source dest       # Copy file
move source dest       # Move file
del filename.txt       # Delete file

# Search operations
findstr "pattern" *.py  # Search for pattern in files
where python           # Find executable location
```

### Development Scripts
```bash
# Run development setup
python scripts/setup.py

# Run development utilities
python scripts/dev.py

# Test TMDB API
python scripts/test_tmdb_api.py
```

## Pre-commit Workflow
1. **Code changes**: Make your changes
2. **Quality checks**: `ruff check src/ tests/ && ruff format src/ tests/ && mypy src/`
3. **Run tests**: `pytest`
4. **Commit**: `git add . && git commit -m "feat: description"`
5. **Push**: `git push origin feature-branch`
