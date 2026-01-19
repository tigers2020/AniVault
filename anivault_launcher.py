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

def _run_gui_v2() -> int:
    """Run GUI v2 entry point."""
    from anivault.gui_v2.app import main

    return main()


def _run_gui_v1() -> int:
    """Run GUI v1 entry point."""
    from anivault.gui.app import main

    return main()


def _run_cli() -> None:
    """Run CLI fallback entry point."""
    from anivault.cli.typer_app import app

    app()


# Import and run the GUI application (v2 first, v1 fallback)
try:
    if __name__ == "__main__":
        sys.exit(_run_gui_v2())
except ImportError as e:
    print(f"GUI v2 import failed: {e}")
    print("Falling back to GUI v1...")
    try:
        if __name__ == "__main__":
            sys.exit(_run_gui_v1())
    except ImportError as v1_error:
        print(f"GUI v1 import failed: {v1_error}")
        print("Falling back to CLI mode...")
        try:
            if __name__ == "__main__":
                _run_cli()
        except ImportError as cli_error:
            print(f"CLI import also failed: {cli_error}")
            print("No valid entry point found!")
            sys.exit(1)
