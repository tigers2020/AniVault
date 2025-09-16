# AniVault

AniVault is a PyQt5-based desktop application for managing anime collections and information.

## Features

- Anime collection management
- Search and filter capabilities
- User-friendly interface
- Cross-platform support

## Requirements

- Python 3.10+
- PyQt5

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd AniVault
```

2. Create a virtual environment:
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Development

Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

### Code Quality

- **Formatting**: `black .`
- **Linting**: `ruff check .`
- **Type checking**: `pyright .`
- **Testing**: `pytest`

## Usage

Run the application:
```bash
python main.py
```

## Project Structure

```
AniVault/
├── src/                    # Source code
│   ├── __init__.py
│   ├── main.py            # Application entry point
│   └── app.py             # Main application class
├── tests/                 # Test files
├── .taskmaster/           # Task Master AI configuration
├── pyproject.toml         # Project configuration
├── requirements.txt       # Production dependencies
├── requirements-dev.txt   # Development dependencies
└── README.md
```

## License

MIT License
