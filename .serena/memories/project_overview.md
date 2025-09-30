# AniVault Project Overview

## Project Purpose
AniVault is a comprehensive anime collection management system that automatically parses, identifies, and organizes anime files using TMDB (The Movie Database) API integration. The system provides intelligent file organization with metadata extraction and cross-platform support.

## Key Features
- **Anime File Parsing**: Uses `anitopy` library for intelligent anime filename parsing
- **TMDB Integration**: Fetches metadata from TMDB API with rate limiting and caching
- **Cross-platform Support**: Works on Windows, macOS, and Linux
- **Standalone Executables**: PyInstaller support for creating single-file executables
- **Rich CLI Interface**: Beautiful terminal interface using Rich library
- **Comprehensive Testing**: Full test coverage with pytest and integration tests
- **UTF-8 Support**: Full Unicode support for international anime titles

## Tech Stack
- **Language**: Python 3.9+
- **CLI Framework**: Click
- **UI Library**: Rich
- **Anime Parsing**: anitopy
- **API Integration**: tmdbv3api
- **Security**: cryptography
- **Testing**: pytest, pytest-cov, pytest-mock
- **Code Quality**: ruff, mypy, black
- **Build System**: PyInstaller
- **Task Management**: TaskMaster AI

## Current Development Status
- **Version**: 0.1.0
- **Current Tag**: w5-w6-scan-parse-pipeline
- **Total Tasks**: 8 main tasks, 40 subtasks
- **Completion**: 0% (all tasks pending)
- **Focus**: Pipeline architecture implementation

## Project Structure
```
src/anivault/
├── cli/main.py          # CLI entry point
├── core/                # Core business logic
│   ├── bounded_queue.py # Thread-safe queue implementation
│   └── statistics.py    # Statistics collection
├── utils/               # Utility functions
│   ├── encoding.py      # UTF-8 encoding utilities
│   └── logging_config.py # Logging configuration
└── services/            # External service integrations (planned)
```

## Development Environment
- **OS**: Windows 10+ (primary), macOS, Linux
- **Python**: 3.9+
- **IDE**: VS Code (recommended), PyCharm
- **Package Manager**: pip (primary), Poetry (optional)
- **Version Control**: Git
