# AniVault Development Guide

This guide provides comprehensive instructions for setting up, developing, and contributing to the AniVault project.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Project Setup](#project-setup)
4. [Development Environment](#development-environment)
5. [Project Structure](#project-structure)
6. [Development Workflow](#development-workflow)
7. [Testing](#testing)
8. [Code Quality](#code-quality)
9. [Building and Packaging](#building-and-packaging)
10. [Configuration](#configuration)
11. [Troubleshooting](#troubleshooting)
12. [Contributing](#contributing)

## Overview

AniVault is a Python-based anime file organization tool that integrates with TMDB (The Movie Database) API to automatically parse, identify, and organize anime files. The project uses modern Python development practices with comprehensive testing, type hints, and automated quality checks.

### Key Features

- **Anime File Parsing**: Uses `anitopy` library for intelligent anime filename parsing
- **TMDB Integration**: Fetches metadata from TMDB API with rate limiting and caching
- **Cross-platform Support**: Works on Windows, macOS, and Linux
- **Standalone Executables**: PyInstaller support for creating single-file executables
- **Rich CLI Interface**: Beautiful terminal interface using Rich library
- **Comprehensive Testing**: Full test coverage with pytest and integration tests

## Prerequisites

### System Requirements

- **Python**: 3.9 or higher
- **Operating System**: Windows 10+, macOS 10.15+, or Linux (Ubuntu 20.04+)
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Storage**: 1GB free space for development environment

### Required Software

- **Git**: For version control
- **Python 3.9+**: [Download Python](https://www.python.org/downloads/)
- **pip**: Usually comes with Python
- **Poetry** (optional): For dependency management

### External Services

- **TMDB API Key**: Required for metadata fetching
  - Sign up at [The Movie Database](https://www.themoviedb.org/)
  - Follow the [TMDB API Key Guide](docs/tmdb-api-key-guide.md)

## Project Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/anivault.git
cd anivault
```

### 2. Create Virtual Environment

**Using venv (recommended):**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

**Using Poetry (alternative):**
```bash
poetry install
poetry shell
```

### 3. Install Dependencies

**Install in development mode:**
```bash
pip install -e .
```

**Install with development dependencies:**
```bash
pip install -e ".[dev]"
```

### 4. Verify Installation

```bash
python -c "import anivault; print('AniVault installed successfully')"
anivault --help
```

## Development Environment

### IDE Configuration

**VS Code (Recommended):**
1. Install the Python extension
2. Install recommended extensions:
   - Python
   - Pylance
   - Ruff
   - pytest
   - GitLens

**PyCharm:**
1. Open the project folder
2. Configure Python interpreter to use the virtual environment
3. Enable type checking and code inspections

### Environment Variables

Create a `.env` file in the project root:

```env
# TMDB API Configuration
TMDB_API_KEY=your_api_key_here

# Development Settings
ANIVAULT_LOG_LEVEL=DEBUG
ANIVAULT_LOG_FILE=logs/anivault.log

# Testing
ANIVAULT_TEST_MODE=true
```

### Pre-commit Hooks (Optional)

Install pre-commit hooks for automated code quality checks:

```bash
pip install pre-commit
pre-commit install
```

## Project Structure

```
anivault/
├── src/
│   └── anivault/
│       ├── __init__.py
│       ├── cli/
│       │   ├── __init__.py
│       │   └── main.py          # CLI entry point
│       ├── core/                # Core business logic
│       ├── services/            # External service integrations
│       ├── ui/                  # User interface components
│       └── utils/               # Utility functions
│           ├── __init__.py
│           ├── encoding.py      # Text encoding utilities
│           └── logging_config.py # Logging configuration
├── tests/                       # Test files
│   ├── __init__.py
│   ├── test_cli_entry_point.py
│   └── test_encoding_and_logging.py
├── docs/                        # Documentation
│   ├── development-plan.md
│   ├── tmdb-api-key-guide.md
│   └── tmdb-api-validation-results.md
├── scripts/                     # Development scripts
│   ├── dev.py
│   └── setup.py
├── config/                      # Configuration files
│   └── settings.yaml
├── .taskmaster/                 # Task management
│   ├── tasks/
│   ├── docs/
│   └── reports/
├── pyproject.toml              # Project configuration
├── requirements.txt            # Dependencies
├── .env                        # Environment variables (create this)
├── .gitignore                  # Git ignore rules
└── README.md                   # Project overview
```

### Key Files Explained

- **`src/anivault/cli/main.py`**: Main CLI entry point using Click
- **`pyproject.toml`**: Project metadata, dependencies, and tool configurations
- **`requirements.txt`**: Basic dependencies for pip installation
- **`.taskmaster/`**: TaskMaster AI project management files
- **`docs/`**: Comprehensive project documentation
- **`tests/`**: Test suite with unit and integration tests

## Development Workflow

### 1. Task Management

This project uses TaskMaster AI for task management:

```bash
# Initialize TaskMaster (already done)
task-master init

# View current tasks
task-master list

# Get next task to work on
task-master next

# View specific task details
task-master show <task_id>

# Mark task as complete
task-master set-status --id=<task_id> --status=done
```

### 2. Feature Development

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes:**
   - Follow the coding standards (see [Code Quality](#code-quality))
   - Add tests for new functionality
   - Update documentation if needed

3. **Test your changes:**
   ```bash
   pytest
   ruff check
   mypy src/
   ```

4. **Commit your changes:**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push and create PR:**
   ```bash
   git push origin feature/your-feature-name
   ```

### 3. Code Review Process

1. All changes require code review
2. Ensure all tests pass
3. Check code quality metrics
4. Verify documentation is updated
5. Test on multiple platforms if applicable

## Testing

### Test Structure

The project uses pytest with the following test organization:

```
tests/
├── __init__.py
├── test_cli_entry_point.py      # CLI functionality tests
├── test_encoding_and_logging.py # Utility function tests
└── test_initial.py              # Basic sanity tests
```

### Running Tests

**Run all tests:**
```bash
pytest
```

**Run with coverage:**
```bash
pytest --cov=src --cov-report=html
```

**Run specific test categories:**
```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

**Run specific test file:**
```bash
pytest tests/test_cli_entry_point.py
```

### Test Markers

The project uses pytest markers for test categorization:

- `@pytest.mark.unit`: Fast unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.slow`: Tests that take longer to run
- `@pytest.mark.memory_intensive`: Tests requiring significant memory

### Writing Tests

**Example test structure:**
```python
import pytest
from anivault.utils.encoding import normalize_text

@pytest.mark.unit
def test_normalize_text():
    """Test text normalization function."""
    assert normalize_text("Test String") == "test string"
    assert normalize_text("") == ""
    assert normalize_text("   ") == ""
```

## Code Quality

### Code Style

The project enforces consistent code style using:

- **Ruff**: Fast Python linter and formatter
- **MyPy**: Static type checking
- **Black**: Code formatting (via Ruff)

### Running Quality Checks

**Lint code:**
```bash
ruff check src/ tests/
```

**Format code:**
```bash
ruff format src/ tests/
```

**Type checking:**
```bash
mypy src/
```

**All quality checks:**
```bash
ruff check src/ tests/ && ruff format src/ tests/ && mypy src/
```

### Type Hints

All functions should include type hints:

```python
from typing import List, Optional, Dict, Any
from pathlib import Path

def process_files(file_paths: List[Path]) -> Dict[str, Any]:
    """Process a list of files and return results."""
    results = {}
    # Implementation here
    return results
```

### Documentation

- Use Google-style docstrings for all functions and classes
- Include type information in docstrings
- Document complex algorithms and business logic
- Keep README and documentation up to date

## Building and Packaging

### Development Build

**Install in development mode:**
```bash
pip install -e .
```

### Standalone Executable

**Build with PyInstaller:**
```bash
# Install PyInstaller
pip install pyinstaller

# Build executable
pyinstaller --onefile --name anivault src/anivault/cli/main.py
```

**Test the executable:**
```bash
./dist/anivault --help
```

### Distribution

**Create source distribution:**
```bash
python -m build
```

**Install from source:**
```bash
pip install dist/anivault-0.1.0.tar.gz
```

## Configuration

### Application Configuration

Configuration is managed through multiple sources:

1. **Environment variables** (`.env` file)
2. **Configuration files** (`config/settings.yaml`)
3. **pyproject.toml** (tool-specific settings)

### TMDB API Configuration

See [TMDB API Key Guide](docs/tmdb-api-key-guide.md) for detailed API setup instructions.

### Logging Configuration

Logging is configured in `src/anivault/utils/logging_config.py`:

```python
# Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = "INFO"
LOG_FILE = "logs/anivault.log"
LOG_MAX_BYTES = 10485760  # 10MB
LOG_BACKUP_COUNT = 5
```

## Troubleshooting

### Common Issues

#### 1. Import Errors

**Problem**: `ModuleNotFoundError` when importing anivault

**Solution**:
```bash
# Ensure you're in the virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install in development mode
pip install -e .
```

#### 2. TMDB API Errors

**Problem**: API authentication failures

**Solution**:
```bash
# Test your API key
python check_api_key.py --file .env

# Verify .env file exists and contains valid key
cat .env
```

#### 3. Test Failures

**Problem**: Tests failing with import errors

**Solution**:
```bash
# Install test dependencies
pip install -e ".[dev]"

# Run tests with verbose output
pytest -v
```

#### 4. PyInstaller Build Issues

**Problem**: Executable build fails

**Solution**:
```bash
# Clean previous builds
rm -rf build/ dist/

# Rebuild
pyinstaller --clean --onefile --name anivault src/anivault/cli/main.py
```

#### 5. Code Quality Check Failures

**Problem**: Ruff or MyPy errors

**Solution**:
```bash
# Fix auto-fixable issues
ruff check --fix src/ tests/

# Check specific error types
ruff check --select E src/ tests/  # Errors only
mypy src/ --ignore-missing-imports
```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
export ANIVAULT_LOG_LEVEL=DEBUG
anivault --verbose your-command
```

### Performance Issues

**Memory usage:**
```bash
# Run memory profiler
python -m memory_profiler src/anivault/cli/main.py your-command
```

**Performance profiling:**
```bash
# Install profiling tools
pip install line-profiler

# Profile specific functions
kernprof -l -v your_script.py
```

## Contributing

### Getting Started

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Contribution Guidelines

1. **Code Style**: Follow the project's code style guidelines
2. **Testing**: Add tests for new functionality
3. **Documentation**: Update documentation for user-facing changes
4. **Commits**: Use conventional commit messages
5. **Pull Requests**: Provide clear descriptions and link related issues

### Commit Message Format

Use conventional commits:

```
feat: add new feature
fix: fix bug in existing feature
docs: update documentation
test: add or update tests
refactor: refactor code without changing functionality
style: fix code style issues
chore: update build process or dependencies
```

### Pull Request Template

When creating a pull request, include:

1. **Description**: What changes were made and why
2. **Testing**: How the changes were tested
3. **Documentation**: Any documentation updates needed
4. **Breaking Changes**: Any breaking changes and migration steps
5. **Related Issues**: Link to related issues or discussions

### Code Review Checklist

Before submitting code for review, ensure:

- [ ] All tests pass
- [ ] Code follows style guidelines
- [ ] Type hints are included
- [ ] Documentation is updated
- [ ] No breaking changes (or properly documented)
- [ ] Performance impact is considered
- [ ] Security implications are reviewed

## Additional Resources

### Documentation

- [Development Plan](docs/development-plan.md)
- [TMDB API Key Guide](docs/tmdb-api-key-guide.md)
- [Risk Validation Report](RISK_VALIDATION_REPORT.md)

### External Resources

- [Python Official Documentation](https://docs.python.org/3/)
- [Click Documentation](https://click.palletsprojects.com/)
- [Rich Documentation](https://rich.readthedocs.io/)
- [TMDB API Documentation](https://developers.themoviedb.org/3)
- [Anitopy Documentation](https://github.com/igorcmoura/anitopy)
- [PyInstaller Documentation](https://pyinstaller.readthedocs.io/)

### Community

- [GitHub Issues](https://github.com/yourusername/anivault/issues)
- [Discussions](https://github.com/yourusername/anivault/discussions)
- [TMDB Community](https://www.themoviedb.org/talk)

---

**Last Updated**: January 2025
**Version**: 1.0
**Maintainers**: AniVault Team
