#!/usr/bin/env python
"""
AniVault GUI Application Launcher

This is the entry point for the PyInstaller executable.
It uses absolute imports to avoid relative import issues.
"""

import sys
from pathlib import Path

# Ensure the src directory is in the path
src_dir = Path(__file__).parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Import and run the GUI application
try:
    from anivault.gui.app import main

    if __name__ == "__main__":
        sys.exit(main())
except ImportError as e:
    print(f"GUI import failed: {e}")
    print("Falling back to CLI mode...")
    try:
        from anivault.cli.typer_app import app

        if __name__ == "__main__":
            app()
    except ImportError as cli_error:
        print(f"CLI import also failed: {cli_error}")
        print("No valid entry point found!")
        sys.exit(1)
