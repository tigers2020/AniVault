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
from anivault.gui.app import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
