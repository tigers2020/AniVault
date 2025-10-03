#!/usr/bin/env python3
"""테스트용 파일 생성 스크립트"""

from pathlib import Path

# 테스트용 파일들 생성
test_dir = Path("test_anime_files")
test_dir.mkdir(exist_ok=True)

# filenames.txt에서 샘플 파일들 생성
with open("filenames.txt", encoding="utf-8") as f:
    lines = f.readlines()

# 처음 20개 파일명으로 테스트 파일들 생성
created_count = 0
for i, line in enumerate(lines[:20]):  # noqa: B007
    if line.strip() and not line.startswith("collect_filenames.py"):
        filename = line.strip()
        file_path = test_dir / filename

        # 디렉토리 생성
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 파일 생성 (빈 파일)
        file_path.touch()
        created_count += 1

        print(f"Created: {filename}")

print(f"Created {created_count} test files")
