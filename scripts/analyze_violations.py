#!/usr/bin/env python3
"""코드 품질 위반 사항 분석 스크립트"""
import json
import sys
from pathlib import Path
from collections import Counter

def analyze_violations(json_file: str):
    """위반 사항 분석 및 요약"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading {json_file}: {e}")
        return
    
    print(f"\n{'='*60}")
    print(f"코드 품질 분석 결과: {json_file}")
    print(f"{'='*60}\n")
    
    print(f"📊 분석 파일 수: {data.get('files_analyzed', 0)}")
    print(f"⚠️  총 위반 사항: {data.get('violations_count', 0)}\n")
    
    violations = data.get('violations', [])
    
    if not violations:
        print("✅ 위반 사항이 없습니다!")
        return
    
    # 위반 타입별 집계
    type_counter = Counter(v.get('type', 'unknown') for v in violations)
    print(f"📋 위반 유형별 집계:")
    for vtype, count in type_counter.most_common():
        print(f"   {vtype:30s}: {count:4d}개")
    
    # 심각도별 집계 (에러 처리 위반인 경우)
    if 'severity' in violations[0]:
        severity_counter = Counter(v.get('severity', 'unknown') for v in violations)
        print(f"\n🚨 심각도별 집계:")
        for severity, count in sorted(severity_counter.items(), 
                                      key=lambda x: {'high': 3, 'medium': 2, 'low': 1}.get(x[0], 0), 
                                      reverse=True):
            print(f"   {severity.upper():10s}: {count:4d}개")
    
    # 파일별 위반 수 TOP 10
    file_counter = Counter(v.get('file', 'unknown') for v in violations)
    print(f"\n📁 위반 사항 많은 파일 TOP 10:")
    for i, (file, count) in enumerate(file_counter.most_common(10), 1):
        file_name = Path(file).name
        print(f"   {i:2d}. {file_name:40s}: {count:3d}개")
    
    # 함수별 위반 수 TOP 10 (함수 정보가 있는 경우)
    if 'function' in violations[0]:
        func_violations = [(v.get('function', 'unknown'), v.get('file', '')) 
                          for v in violations if v.get('function')]
        func_counter = Counter(func_violations)
        print(f"\n🔧 위반 사항 많은 함수 TOP 10:")
        for i, ((func, file), count) in enumerate(func_counter.most_common(10), 1):
            file_name = Path(file).name
            print(f"   {i:2d}. {func:30s} ({file_name}): {count:2d}개")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_violations.py <json_file>")
        sys.exit(1)
    
    analyze_violations(sys.argv[1])

