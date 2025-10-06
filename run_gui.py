#!/usr/bin/env python3
"""
Run AniVault GUI Application
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from anivault.gui.app import main

if __name__ == "__main__":
    sys.exit(main())
