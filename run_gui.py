#!/usr/bin/env python3
"""AniVault GUI 실행 스크립트.

이 스크립트는 AniVault GUI 애플리케이션을 실행합니다.
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# AniVault GUI 실행
if __name__ == "__main__":
    try:
        from src.anivault.gui.app import main

        main()
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure you're running from the project root directory")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
