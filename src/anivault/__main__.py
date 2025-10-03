"""
AniVault Package Main Entry Point

This module serves as the main entry point when the package is run as a module
using `python -m anivault`. It delegates to the CLI main function.
"""

import sys
from pathlib import Path

# Add the src directory to the Python path for absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from anivault.cli.typer_app import app  # noqa: E402

if __name__ == "__main__":
    app()
