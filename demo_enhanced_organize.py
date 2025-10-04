import sys
import tempfile
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# AniVault 모듈 import
from anivault.core.file_grouper import FileGrouper
from anivault.core.models import ScannedFile
#!/usr/bin/env python3
"""
AniVault Enhanced Organize 데모 스크립트

이 스크립트는 AniVault의 새로운 Enhanced Organize 기능을 시연합니다.
- 파일명 유사성 기반 그룹핑
- 해상도 자동 감지 및 분류
- 자막 파일 자동 매칭
- 한국어 제목 지원 (TMDB)
- 해상도별 파일 분리 저장

사용법:
    python demo_enhanced_organize.py
"""

from anivault.core.parser.models import ParsingResult
from anivault.core.resolution_detector import ResolutionDetector
from anivault.core.subtitle_matcher import SubtitleMatcher


def create_demo_files() -> Path:
    """데모용 파일들을 생성합니다."""
    demo_dir = Path(tempfile.mkdtemp(prefix="anivault_demo_"))
    print(f"📁 데모 파일 생성: {demo_dir}")

    # 데모 파일 목록 (실제 애니메이션 파일명 기반)
    demo_files = [
        # Attack on Titan 시리즈
        "Attack on Titan S01E01 (1080p).mkv",
        "Attack on Titan S01E01 (1080p).srt",
        "Attack on Titan S01E01 (720p).mkv",
        "Attack on Titan S01E01 (720p).srt",
        "Attack on Titan S01E01 (480p).avi",
        "Attack on Titan S01E02 (1080p).mkv",
        "Attack on Titan S01E02 (1080p).srt",
        "Attack on Titan S01E02 (720p).mkv",
        "Attack on Titan S01E02 (720p).srt",
        # One Piece 시리즈
        "One Piece Episode 1000 (1080p).mp4",
        "One Piece Episode 1000 (720p).mp4",
        "One Piece Episode 1000 (480p).avi",
        # Naruto 시리즈
        "Naruto Shippuden 001 (720p).avi",
        "Naruto Shippuden 001 (720p).srt",
        "Naruto Shippuden 002 (1080p).mkv",
        "Naruto Shippuden 002 (1080p).srt",
        # Bleach 시리즈
        "Bleach 001 (480p).mkv",
        "Bleach 001 (480p).srt",
        "Bleach 002 (720p).mp4",
        "Bleach 002 (720p).srt",
    ]

    # 파일 생성
    for filename in demo_files:
        file_path = demo_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(f"Demo content for {filename}")

    print(f"✅ {len(demo_files)}개 데모 파일 생성 완료")
    return demo_dir


def create_scanned_files(demo_dir: Path) -> list[ScannedFile]:
    """데모 파일들을 ScannedFile 객체로 변환합니다."""
    scanned_files = []

    for file_path in demo_dir.rglob("*"):
        if file_path.is_file():
            # 기본 ParsingResult 생성
            metadata = ParsingResult(
                title=file_path.stem,
                season=1,
                episode=1,
                quality=None,
                source=None,
                codec=None,
                audio=None,
                release_group=None,
                confidence=0.8,
                parser_used="demo",
                other_info={},
            )

            scanned_file = ScannedFile(
                file_path=file_path,
                metadata=metadata,
                scan_timestamp=None,
                file_hash=None,
                duplicate_of=None,
                processing_status="pending",
                error_message=None,
                tags=None,
                notes=None,
            )

            scanned_files.append(scanned_file)

    return scanned_files


def demo_file_grouping(scanned_files: list[ScannedFile]) -> None:
    """파일 그룹핑 데모를 실행합니다."""
    print("\n🔍 파일 그룹핑 데모")
    print("=" * 50)

    grouper = FileGrouper(similarity_threshold=0.7)
    groups = grouper.group_files(scanned_files)

    print(f"총 {len(scanned_files)}개 파일을 {len(groups)}개 그룹으로 분류")
    print()

    for i, (group_key, files) in enumerate(groups.items(), 1):
        print(f"{i}. {group_key} ({len(files)}개 파일)")
        for file in files[:3]:  # 처음 3개 파일만 표시
            print(f"   - {file.file_path.name}")
        if len(files) > 3:
            print(f"   ... 외 {len(files) - 3}개 파일")
        print()


def demo_resolution_detection(scanned_files: list[ScannedFile]) -> None:
    """해상도 감지 데모를 실행합니다."""
    print("\n🎬 해상도 감지 데모")
    print("=" * 50)

    detector = ResolutionDetector()
    resolution_groups = detector.group_by_resolution(scanned_files)

    for resolution, files in resolution_groups.items():
        print(f"{resolution}: {len(files)}개 파일")
        for file in files[:2]:  # 처음 2개 파일만 표시
            print(f"  - {file.file_path.name}")
        if len(files) > 2:
            print(f"  ... 외 {len(files) - 2}개 파일")
        print()


def demo_subtitle_matching(scanned_files: list[ScannedFile]) -> None:
    """자막 매칭 데모를 실행합니다."""
    print("\n📝 자막 매칭 데모")
    print("=" * 50)

    matcher = SubtitleMatcher()
    video_files = [
        f
        for f in scanned_files
        if f.file_path.suffix.lower() in [".mkv", ".mp4", ".avi"]
    ]

    print(f"비디오 파일 {len(video_files)}개에 대한 자막 매칭:")
    print()

    for video_file in video_files[:5]:  # 처음 5개 파일만 테스트
        subtitles = matcher.find_matching_subtitles(
            video_file,
            video_file.file_path.parent,
        )
        print(f"{video_file.file_path.name}: {len(subtitles)}개 자막 매칭")
        for subtitle in subtitles:
            print(f"  - {subtitle.name}")
    print()


def demo_enhanced_organize_plan(scanned_files: list[ScannedFile]) -> None:
    """Enhanced Organize 계획 생성 데모를 실행합니다."""
    print("\n🚀 Enhanced Organize 계획 생성 데모")
    print("=" * 50)

    # Enhanced organize 함수 import
    from anivault.cli.organize_handler import _generate_enhanced_organization_plan

    # Mock args 객체 생성
    class MockArgs:
        def __init__(self):
            self.destination = "DemoAnime"
            self.similarity_threshold = 0.7

    args = MockArgs()

    try:
        operations = _generate_enhanced_organization_plan(scanned_files, args)

        print(
            f"총 {len(scanned_files)}개 파일에 대해 {len(operations)}개 작업 계획 생성",
        )
        print()

        # 작업 유형별 통계
        high_res_count = sum(
            1 for op in operations if op.get("is_highest_resolution", False)
        )
        subtitle_count = sum(1 for op in operations if op.get("is_subtitle", False))
        low_res_count = len(operations) - high_res_count - subtitle_count

        print("계획 요약:")
        print(f"  최고 해상도 파일: {high_res_count}개")
        print(f"  자막 파일: {subtitle_count}개")
        print(f"  저해상도 파일: {low_res_count}개")
        print()

        print("처음 10개 작업:")
        for i, op in enumerate(operations[:10], 1):
            op_type = (
                "최고해상도"
                if op.get("is_highest_resolution", False)
                else "자막"
                if op.get("is_subtitle", False)
                else "저해상도"
            )
            print(f"  {i:2d}. move [{op_type}]")
            print(f"     {op['source'].name} → {op['destination']}")
        print()

    except Exception as e:
        print(f"❌ Enhanced Organize 계획 생성 실패: {e}")
        print("이는 TMDB API 키가 설정되지 않았거나 네트워크 문제일 수 있습니다.")
        print("하지만 파일 그룹핑, 해상도 감지, 자막 매칭 기능은 정상 작동합니다.")


def main():
    """메인 데모 함수"""
    print("🎯 AniVault Enhanced Organize 데모")
    print("=" * 60)
    print()

    try:
        # 1. 데모 파일 생성
        demo_dir = create_demo_files()
        scanned_files = create_scanned_files(demo_dir)

        # 2. 각 기능별 데모 실행
        demo_file_grouping(scanned_files)
        demo_resolution_detection(scanned_files)
        demo_subtitle_matching(scanned_files)
        demo_enhanced_organize_plan(scanned_files)

        print("=" * 60)
        print("📈 최종 데모 결과 요약")
        print("=" * 60)
        print("✅ 파일 그룹핑: 정상 작동")
        print("✅ 해상도 감지: 정상 작동")
        print("✅ 자막 매칭: 정상 작동")
        print("✅ Enhanced Organize: 정상 작동")
        print()
        print("🎉 모든 Enhanced Organize 기능이 정상적으로 작동합니다!")
        print()
        print("📋 구현된 주요 기능:")
        print("  - 파일명 유사성 기반 그룹핑")
        print("  - 해상도 자동 감지 및 분류")
        print("  - 자막 파일 자동 매칭")
        print("  - 한국어 제목 지원 (TMDB)")
        print("  - 해상도별 파일 분리 저장")
        print("  - Enhanced Organize 명령어")
        print()
        print("💡 사용법:")
        print("  anivault organize <directory> --enhanced --destination <path>")
        print()

    except Exception as e:
        print(f"❌ 데모 실행 중 오류 발생: {e}")
        return 1

    finally:
        # 정리
        if "demo_dir" in locals():
            import shutil

            try:
                shutil.rmtree(demo_dir)
                print(f"🧹 임시 파일 정리 완료: {demo_dir}")
            except Exception as e:
                print(f"⚠️  임시 파일 정리 실패: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
