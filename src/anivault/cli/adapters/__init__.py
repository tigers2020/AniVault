"""
CLI Adapters Module

This module provides adapters for converting between Typer callbacks and
legacy argparse handlers. It enables gradual migration from argparse to Typer
while maintaining backward compatibility and code reuse.

The adapters handle:
- Type conversion from Typer parameters to argparse.Namespace
- Error handling and logging
- Context management
- Exit code mapping
"""

from .base import BaseAdapter
from .scan_adapter import create_scan_command

__all__ = [
    "BaseAdapter",
    "create_scan_command",
]
