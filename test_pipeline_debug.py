#!/usr/bin/env python3
"""
파이프라인 디버그 테스트 스크립트
"""

import sys
import threading
import time
from pathlib import Path


def test_pipeline_with_timeout():
    """타임아웃이 있는 파이프라인 테스트."""
    print("🔍 파이프라인 타임아웃 테스트 시작...")

    result_container = {"completed": False, "result": None, "error": None}

    def run_pipeline_thread():
        """파이프라인을 별도 스레드에서 실행."""
        try:
            from anivault.core.pipeline.main import run_pipeline

            file_results = run_pipeline(
                root_path="test_anime_files",
                extensions=[".mkv", ".mp4", ".avi"],
                num_workers=2,  # 워커 수 줄임
                max_queue_size=10,  # 큐 크기 줄임
            )

            result_container["result"] = file_results
            result_container["completed"] = True

        except Exception as e:
            result_container["error"] = e
            result_container["completed"] = True

    print("📁 파이프라인 실행 중...")
    start_time = time.time()

    # 별도 스레드에서 파이프라인 실행
    thread = threading.Thread(target=run_pipeline_thread)
    thread.daemon = True
    thread.start()

    # 15초 타임아웃 대기
    thread.join(timeout=15)

    end_time = time.time()
    duration = end_time - start_time

    if result_container["completed"]:
        if result_container["error"]:
            print(f"❌ 파이프라인 오류: {result_container['error']}")
            import traceback

            traceback.print_exc()
            return False
        else:
            print(f"✅ 파이프라인 완료! 소요시간: {duration:.2f}초")
            print(
                f"📄 처리된 파일 수: {len(result_container['result']) if result_container['result'] else 0}"
            )
            return True
    else:
        print("⏰ 타임아웃! 파이프라인이 15초 이상 걸리고 있습니다.")
        return False


def test_simple_file_processing():
    """간단한 파일 처리 테스트."""
    print("🔍 간단한 파일 처리 테스트...")

    try:
        from anivault.core.parser.anitopy_parser import AnitopyParser

        parser = AnitopyParser()
        test_dir = Path("test_anime_files")

        # 첫 번째 파일만 테스트
        test_files = list(test_dir.glob("*.mkv"))[:1]

        if not test_files:
            print("❌ 테스트할 .mkv 파일이 없습니다.")
            return False

        test_file = test_files[0]
        print(f"📄 테스트 파일: {test_file.name}")

        # 파일 파싱 테스트
        result = parser.parse(str(test_file))

        if result and result.title:
            print("✅ 파일 파싱 성공!")
            print(f"  - 제목: {result.title}")
            print(f"  - 에피소드: {result.episode}")
            print(f"  - 시즌: {result.season}")
            print(f"  - 품질: {result.quality}")
        else:
            print("❌ 파일 파싱 실패")
            return False

        return True

    except Exception as e:
        print(f"❌ 파일 처리 테스트 실패: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """메인 디버그 함수."""
    print("=" * 50)
    print("🐛 AniVault 파이프라인 디버그")
    print("=" * 50)

    # 1. 간단한 파일 처리 테스트
    if not test_simple_file_processing():
        return 1

    print()

    # 2. 타임아웃이 있는 파이프라인 테스트
    if not test_pipeline_with_timeout():
        return 1

    print()
    print("🎉 디버그 테스트 완료!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
