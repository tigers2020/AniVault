#!/usr/bin/env python3
"""AniVault GUI v2 실행 스크립트.

이 스크립트는 AniVault GUI v2 애플리케이션을 실행합니다.
"""

import sys
from pathlib import Path

# src 디렉토리를 Python 경로에 추가 (anivault 모듈을 찾기 위해)
project_root = Path(__file__).parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

# AniVault GUI v2 실행
if __name__ == "__main__":
    try:
        from anivault.gui_v2.app import main

        main()
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure you're running from the project root directory")
        print(f"   Project root: {project_root}")
        print(f"   Python path: {sys.path[:3]}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
