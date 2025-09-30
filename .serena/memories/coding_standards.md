# AniVault Coding Standards

## Code Style and Conventions

### Type Hints
- **Required**: All functions must include type hints
- **Style**: Use modern Python type hints (Python 3.9+)
- **Example**:
```python
from typing import List, Optional, Dict, Any
from pathlib import Path

def process_files(file_paths: List[Path]) -> Dict[str, Any]:
    """Process a list of files and return results."""
    pass
```

### Docstrings
- **Style**: Google/NumPy docstring format
- **Placement**: After function definition, not before
- **Required Elements**: Description, Args, Returns, Raises
- **Example**:
```python
def normalize_text(text: str) -> str:
    """Normalize text for consistent processing.

    Args:
        text: Input text to normalize

    Returns:
        Normalized text string

    Raises:
        ValueError: If text is None or empty
    """
    pass
```

### Comments
- **Within functions**: Use `#` for inline comments
- **Constants**: Define alphabet symbols as constants
- **Example**:
```python
# Constants for encoding
UTF8_ENCODING = "utf-8"
UTF8_BOM = "\ufeff"

def process_file(file_path: Path) -> None:
    # Check if file exists before processing
    if not file_path.exists():
        return
```

### Naming Conventions
- **Functions/Variables**: snake_case
- **Classes**: PascalCase
- **Constants**: UPPER_SNAKE_CASE
- **Private methods**: _leading_underscore
- **Protected methods**: __double_underscore

### Code Organization
- **Functions**: Keep small and focused
- **Input validation**: At function boundaries
- **Exception handling**: Raise specific exceptions
- **Error handling**: Consistent patterns across codebase

## File Structure Standards
- **Module organization**: Logical grouping by functionality
- **Import order**: Standard library, third-party, local imports
- **Class organization**: Public methods first, private methods last
- **Function organization**: Related functions grouped together
