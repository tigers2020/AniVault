#!/usr/bin/env python3
"""Stage 1 검증 스크립트"""
import json

# Load error violations
with open('error_violations.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

violations = data['violations']

# Stage 1 대상 파일들
stage1_files = [
    'settings.py',
    'encryption.py',
    'tmdb_matching_worker.py'
]

print("="*70)
print("Stage 1: 보안 즉시 조치 검증")
print("="*70)
print()

# 파일별 HIGH 위반 확인
for filename in stage1_files:
    file_violations = [
        v for v in violations 
        if filename in v['file'] and v['severity'] == 'high'
    ]
    
    print(f"📁 {filename}: {len(file_violations)}개 HIGH 위반")
    for v in file_violations:
        print(f"   Line {v['line']}: {v['function']}() - {v['type']}")
    print()

# 전체 HIGH 위반 집계
high_violations = [v for v in violations if v['severity'] == 'high']
stage1_high = [v for v in high_violations if any(f in v['file'] for f in stage1_files)]

print(f"전체 HIGH 심각도: {len(high_violations)}개")
print(f"Stage 1 수정 대상: 3개")
print(f"Stage 1 남은 HIGH: {len(stage1_high)}개")
print(f"Stage 2 대상 HIGH: {len(high_violations) - len(stage1_high)}개")
print()

# Next steps
print("="*70)
print("다음 단계: Stage 2 - 나머지 HIGH 심각도 수정")
print("="*70)
print()

# Top priority files
from collections import Counter
file_counter = Counter(v['file'].split('\\')[-1] for v in high_violations if not any(f in v['file'] for f in stage1_files))
print("우선순위 파일 TOP 5:")
for i, (file, count) in enumerate(file_counter.most_common(5), 1):
    print(f"  {i}. {file}: {count}개")

