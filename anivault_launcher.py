#!/usr/bin/env python
"""
AniVault GUI Application Launcher

This is the entry point for the PyInstaller executable.
It uses absolute imports to avoid relative import issues.
"""

import sys
import traceback
from pathlib import Path


# Debug mode: Set to True to enable debug output (useful for troubleshooting)
DEBUG = False


def _debug_print(*args, **kwargs) -> None:
    """Print debug messages only if DEBUG is enabled."""
    if DEBUG:
        print(*args, **kwargs)


def _setup_paths() -> None:
    """Setup Python path for both development and PyInstaller environments."""
    # Check if running as PyInstaller bundle
    if getattr(sys, "frozen", False):
        # Running as PyInstaller bundle
        # _MEIPASS is the temp directory where PyInstaller extracts files
        base_path = Path(sys._MEIPASS)  # type: ignore[attr-defined]
        _debug_print(f"[DEBUG] Running as frozen app, base_path: {base_path}")
    else:
        # Running in development mode
        base_path = Path(__file__).parent / "src"
        _debug_print(f"[DEBUG] Running in dev mode, base_path: {base_path}")

    # Add to sys.path if not already there
    base_path_str = str(base_path)
    if base_path_str not in sys.path:
        sys.path.insert(0, base_path_str)
        _debug_print(f"[DEBUG] Added to sys.path: {base_path_str}")

    # For frozen apps, also add the directory containing the exe
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        exe_dir_str = str(exe_dir)
        if exe_dir_str not in sys.path:
            sys.path.insert(0, exe_dir_str)
            _debug_print(f"[DEBUG] Added exe dir to sys.path: {exe_dir_str}")


def _run_gui_v2() -> int:
    """Run GUI v2 entry point."""
    _debug_print("[DEBUG] Attempting to import gui_v2...")
    from anivault.gui_v2.app import main

    _debug_print("[DEBUG] gui_v2 imported successfully, starting main()...")
    return main()


def _run_gui_v1() -> int:
    """Run GUI v1 entry point."""
    _debug_print("[DEBUG] Attempting to import gui_v1...")
    from anivault.gui.app import main

    _debug_print("[DEBUG] gui_v1 imported successfully, starting main()...")
    return main()


def _run_cli() -> None:
    """Run CLI fallback entry point."""
    _debug_print("[DEBUG] Attempting to import CLI...")
    from anivault.cli.typer_app import app

    _debug_print("[DEBUG] CLI imported successfully, starting app()...")
    app()


def main() -> int:
    """Main entry point with comprehensive error handling."""
    _debug_print("=" * 60)
    _debug_print("AniVault Launcher Starting...")
    _debug_print(f"Python version: {sys.version}")
    _debug_print(f"Executable: {sys.executable}")
    _debug_print(f"Frozen: {getattr(sys, 'frozen', False)}")
    _debug_print("=" * 60)

    try:
        _setup_paths()

        _debug_print("\n[DEBUG] sys.path contents:")
        for i, p in enumerate(sys.path[:5]):
            _debug_print(f"  [{i}] {p}")
        _debug_print("  ...")

        # Try GUI v2 first
        try:
            return _run_gui_v2()
        except ImportError as e:
            # Always show errors, even in production
            print(f"\n[ERROR] GUI v2 import failed: {e}", file=sys.stderr)
            if DEBUG:
                traceback.print_exc()

        # Fallback to GUI v1
        _debug_print("\n[DEBUG] Falling back to GUI v1...")
        try:
            return _run_gui_v1()
        except ImportError as e:
            print(f"\n[ERROR] GUI v1 import failed: {e}", file=sys.stderr)
            if DEBUG:
                traceback.print_exc()

        # Fallback to CLI
        _debug_print("\n[DEBUG] Falling back to CLI mode...")
        try:
            _run_cli()
            return 0
        except ImportError as e:
            print(f"\n[ERROR] CLI import failed: {e}", file=sys.stderr)
            if DEBUG:
                traceback.print_exc()

        print("\n[FATAL] No valid entry point found!", file=sys.stderr)
        return 1

    except Exception as e:
        # Always show fatal errors
        print(f"\n[FATAL] Unexpected error: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        # In windowed mode, show error dialog or keep console open
        if not getattr(sys, "frozen", False) or DEBUG:
            input("\nPress Enter to exit...")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        if exit_code != 0 and (not getattr(sys, "frozen", False) or DEBUG):
            input("\nPress Enter to exit...")
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n[FATAL] Top-level exception: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        if not getattr(sys, "frozen", False) or DEBUG:
            input("\nPress Enter to exit...")
        sys.exit(1)
