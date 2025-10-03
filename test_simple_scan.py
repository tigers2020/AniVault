#!/usr/bin/env python3
"""
간단한 스캔 테스트 스크립트
"""

import sys
import time
from pathlib import Path


def simple_scan_test():
    """간단한 스캔 테스트."""
    print("🔍 간단한 파일 스캔 테스트 시작...")

    # 테스트 디렉토리 확인
    test_dir = Path("test_anime_files")
    if not test_dir.exists():
        print("❌ 테스트 디렉토리가 없습니다.")
        return False

    print(f"📁 테스트 디렉토리: {test_dir}")

    # 파일 목록 출력
    files = list(test_dir.glob("*"))
    print(f"📄 발견된 파일 수: {len(files)}")

    for file in files:
        print(f"  - {file.name}")

    print("✅ 간단한 스캔 테스트 완료!")
    return True


def test_anivault_import():
    """AniVault 모듈 import 테스트."""
    print("🔧 AniVault 모듈 import 테스트...")

    try:
        from anivault.core.pipeline.main import run_pipeline

        print("✅ run_pipeline import 성공")

        from anivault.core.pipeline.scanner import DirectoryScanner

        print("✅ DirectoryScanner import 성공")

        return True

    except Exception as e:
        print(f"❌ Import 실패: {e}")
        return False


def test_directory_scanner():
    """디렉토리 스캐너 직접 테스트."""
    print("🔍 DirectoryScanner 직접 테스트...")

    try:
        from anivault.core.pipeline.scanner import DirectoryScanner

        scanner = DirectoryScanner()
        test_dir = Path("test_anime_files")

        print(f"📁 스캔 대상: {test_dir}")

        # 간단한 스캔 테스트
        files = scanner.scan_directory(str(test_dir), [".mkv", ".mp4", ".avi"])

        print(f"📄 스캔 결과: {len(files)}개 파일")
        for file in files[:5]:  # 처음 5개만 출력
            print(f"  - {Path(file).name}")

        if len(files) > 5:
            print(f"  ... 그리고 {len(files) - 5}개 더")

        print("✅ DirectoryScanner 테스트 완료!")
        return True

    except Exception as e:
        print(f"❌ DirectoryScanner 테스트 실패: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """메인 테스트 함수."""
    print("=" * 50)
    print("🧪 AniVault 간단 테스트")
    print("=" * 50)

    # 1. 간단한 파일 스캔
    if not simple_scan_test():
        return 1

    print()

    # 2. AniVault 모듈 import 테스트
    if not test_anivault_import():
        return 1

    print()

    # 3. DirectoryScanner 직접 테스트
    if not test_directory_scanner():
        return 1

    print()
    print("🎉 모든 테스트 완료!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
