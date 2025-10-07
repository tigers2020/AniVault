#!/usr/bin/env python3
"""HIGH 심각도 에러 처리 위반 사항 분석"""
import json
import sys
from pathlib import Path
from collections import defaultdict

def analyze_high_severity(error_json: str):
    """HIGH 심각도 위반 사항 상세 분석"""
    with open(error_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    violations = data.get('violations', [])
    high_violations = [v for v in violations if v.get('severity') == 'high']
    
    print(f"\n{'='*70}")
    print(f"HIGH 심각도 에러 처리 위반 상세 분석")
    print(f"{'='*70}\n")
    
    print(f"총 HIGH 심각도 위반: {len(high_violations)}개\n")
    
    # 파일별로 그룹화
    by_file = defaultdict(list)
    for v in high_violations:
        file_name = Path(v['file']).name
        by_file[file_name].append(v)
    
    print(f"파일별 HIGH 위반 사항:\n")
    for file_name, file_violations in sorted(by_file.items(), key=lambda x: -len(x[1])):
        print(f"📁 {file_name}: {len(file_violations)}개")
        
        # 타입별로 그룹화
        by_type = defaultdict(list)
        for v in file_violations:
            by_type[v['type']].append(v)
        
        for vtype, type_violations in sorted(by_type.items()):
            print(f"   └─ {vtype}: {len(type_violations)}개")
            for v in type_violations[:3]:  # 처음 3개만 표시
                print(f"      • Line {v['line']}: {v['function']}() - {v['context']}")
        
        print()
    
    # 타입별 집계
    by_type_total = defaultdict(int)
    for v in high_violations:
        by_type_total[v['type']] += 1
    
    print(f"\n타입별 HIGH 위반 집계:")
    for vtype, count in sorted(by_type_total.items(), key=lambda x: -x[1]):
        print(f"  {vtype:30s}: {count:3d}개")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_high_severity.py error_violations.json")
        sys.exit(1)
    
    analyze_high_severity(sys.argv[1])

