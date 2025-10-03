#!/usr/bin/env python3
"""
AniVault 사용법 데모 스크립트

이 스크립트는 AniVault의 주요 기능들을 시연합니다.
"""

import os
import sys
from pathlib import Path


def print_banner():
    """AniVault 데모 배너 출력."""
    print("=" * 60)
    print("🎌 AniVault - Anime Collection Management System")
    print("=" * 60)
    print()


def print_section(title):
    """섹션 제목 출력."""
    print(f"\n📋 {title}")
    print("-" * 50)


def print_command(description, command):
    """명령어 예시 출력."""
    print(f"💡 {description}")
    print(f"   명령어: {command}")
    print()


def main():
    """메인 데모 함수."""
    print_banner()

    # 현재 디렉토리 확인
    current_dir = Path.cwd()
    print(f"현재 작업 디렉토리: {current_dir}")

    print_section("AniVault 주요 기능")

    print(
        """
AniVault는 애니메이션 파일을 자동으로 정리하고 TMDB API를 통해
메타데이터를 가져오는 도구입니다. 주요 기능은 다음과 같습니다:

1. 📁 파일 스캔: 디렉토리에서 애니메이션 파일 찾기
2. 🎯 TMDB 매칭: TMDB API로 애니메이션 정보 가져오기
3. 📂 파일 정리: 구조화된 디렉토리로 파일 이동
4. 📝 로그 관리: 작업 기록 추적
5. ↩️ 되돌리기: 이전 작업 취소
"""
    )

    print_section("1. 기본 명령어")
    print_command("전체 도움말 보기", "anivault --help")
    print_command("버전 확인", "anivault --version")
    print_command("시스템 검증", "anivault verify")

    print_section("2. 파일 스캔")
    print_command("TMDB 없이 빠른 스캔", "anivault scan /path/to/anime --no-enrich")
    print_command("TMDB와 함께 상세 스캔", "anivault scan /path/to/anime --enrich")
    print_command("특정 확장자만 스캔", "anivault scan /path/to/anime --extensions .mkv .mp4")

    print_section("3. 파일 정리 (가장 중요한 기능)")
    print_command("미리보기 (안전)", "anivault organize /path/to/anime --dry-run")
    print_command("실제 정리 실행", "anivault organize /path/to/anime")
    print_command("확인 없이 바로 실행", "anivault organize /path/to/anime --yes")

    print_section("4. 로그 관리")
    print_command("작업 기록 보기", "anivault log list")
    print_command("특정 로그 상세 보기", "anivault log show YYYYMMDD_HHMMSS")

    print_section("5. 되돌리기")
    print_command("되돌리기 미리보기", "anivault rollback YYYYMMDD_HHMMSS --dry-run")
    print_command("실제 되돌리기", "anivault rollback YYYYMMDD_HHMMSS")

    print_section("안전한 워크플로우 예시")
    print(
        """
🔒 안전한 파일 정리 과정:

1️⃣ 먼저 미리보기로 확인:
   anivault organize ./my_anime --dry-run

2️⃣ 문제없으면 실제 정리:
   anivault organize ./my_anime

3️⃣ 나중에 작업 기록 확인:
   anivault log list

4️⃣ 필요시 되돌리기:
   anivault rollback 20241202_215000
"""
    )

    print_section("실제 사용 예시")

    # 테스트 파일이 있는지 확인
    test_dir = Path("test_anime_files")
    if test_dir.exists():
        print(f"✅ 테스트 디렉토리 발견: {test_dir}")
        print("다음 명령어로 테스트할 수 있습니다:")
        print_command("테스트 파일 스캔", f"anivault scan {test_dir} --no-enrich")
        print_command("테스트 파일 정리 미리보기", f"anivault organize {test_dir} --dry-run")
    else:
        print("❌ 테스트 디렉토리가 없습니다.")
        print("테스트를 위해 다음 명령어로 파일을 생성하세요:")
        print(
            """
mkdir test_anime_files
echo "test content" > "test_anime_files/Attack on Titan S01E01.mkv"
echo "test content" > "test_anime_files/One Piece Episode 1000.mp4"
        """
        )

    print_section("주의사항")
    print(
        """
⚠️ 중요한 주의사항:

1. 항상 --dry-run으로 먼저 확인하세요
2. 중요한 파일은 백업을 만들어두세요
3. TMDB API 사용시 네트워크 연결이 필요합니다
4. 대용량 컬렉션의 경우 시간이 오래 걸릴 수 있습니다
"""
    )

    print_section("문제 해결")
    print(
        """
🔧 문제가 발생하면:

1. 시스템 검증: anivault verify
2. 상세 로그 확인: --verbose 플래그 사용
3. 로그 파일 확인: logs/anivault.log
4. 이슈 리포트: GitHub Issues 페이지
"""
    )

    print("\n" + "=" * 60)
    print("🎯 AniVault 데모 완료!")
    print("더 자세한 정보는 README.md를 참고하세요.")
    print("=" * 60)


if __name__ == "__main__":
    main()
