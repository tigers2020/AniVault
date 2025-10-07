# AniVault 리팩토링 다음 액션

**현재 시점**: 2025-10-07 17:00
**완료된 작업**: Stage 1 보안 즉시 조치
**다음 단계**: Stage 2 - 나머지 HIGH 심각도 56개 수정

---

## 🎯 즉시 시작 가능 작업

### Option A: Stage 2 계속 (권장) - rollback_handler.py
**대상**: 9개 silent failure 패턴
**공수**: 2-3일
**방법**: Failure-First 테스트 → 예외 재전파

**작업 흐름**:
```bash
# 1. Failure 테스트 작성
# tests/cli/test_rollback_handler_failures.py 생성

# 2. 헬퍼 함수 리팩토링
# _get_rollback_log_path: None → raise ApplicationError
# _generate_rollback_plan: None → raise ApplicationError
# _collect_rollback_data: None → raise ApplicationError

# 3. 최상위 핸들러만 예외 catch
# 4. 테스트 실행 (green)
# 5. 커밋
```

### Option B: 매직 값 일부 제거 시작 - 상수 모듈 설계
**대상**: shared/constants/ 모듈 구조 설계
**공수**: 1일
**산출물**: 8개 상수 모듈 스켈레톤

### Option C: print() → logger 전환 - profiler.py부터
**대상**: core/profiler.py (34개 print)
**공수**: 2-3시간
**방법**: print() → logger.info()

---

## 📊 현재 상태 스냅샷

### 완료 ✅
- [x] 전체 코드 정밀 분석 (3,442개 위반)
- [x] 8인 페르소나 주도 기획 완료
- [x] 6-8주 로드맵 수립
- [x] 보안 치명적 결함 3개 수정
- [x] 보안 테스트 14개 추가
- [x] Pre-commit + CI/CD 구축
- [x] 문서 12개 작성

### 진행 중 🔄
- [ ] HIGH 심각도 에러 처리 (59개 중 3개 완료, 5%)

### 대기 ⏳
- [ ] 매직 값 3,130개
- [ ] 함수 품질 164개
- [ ] 테스트 커버리지 32% → 80%

---

## 💡 추천 진행 방향

### 권장: Option A - Stage 2 계속

**이유**:
1. HIGH 심각도는 운영 리스크 (우선순위 최고)
2. Failure-First 패턴 확립되어 진행 빠름
3. 점진적으로 Exception Swallowing 제거

**예상 타임라인**:
- Day 1-2: rollback_handler.py (9개)
- Day 3-4: metadata_enricher.py (7개)
- Day 5: organize_handler.py (4개)
- Week 2: 나머지 36개

### 대안: Quick Win - Option C

**이유**:
1. print() → logger는 기계적 변환 (빠름)
2. 즉시 가시적 성과 (72개 → 0개)
3. 로깅 시스템 일원화

**예상 타임라인**:
- Today: profiler.py (34개) - 2시간
- Tomorrow: benchmark.py (15개) - 1시간
- Day 3: scanner.py (23개) - 2시간

---

## 🚀 실행 명령어 (Option A 선택 시)

```bash
# 1. Failure 테스트 작성
code tests/cli/test_rollback_handler_failures.py

# 2. 테스트 실행 (현재 실패 확인)
python -m pytest tests/cli/test_rollback_handler_failures.py -v

# 3. 헬퍼 함수 리팩토링
code src/anivault/cli/rollback_handler.py

# 4. 테스트 재실행 (통과 확인)
python -m pytest tests/cli/test_rollback_handler_failures.py -v

# 5. 전체 회귀 테스트
python -m pytest tests/test_rollback_handler.py -v

# 6. 커밋
git add .
git commit -m "refactor(cli): Remove silent failure in rollback_handler helper functions"
```

---

## 📝 체크포인트

현재 위치: **Stage 1 완료, Stage 2 Ready**

**완료 비율**:
- 전체 리팩토링: 1% (3/3,442)
- HIGH 심각도: 5% (3/59)
- 보안 영역: 100% (3/3)

**소요 시간**: 3시간
**남은 예상 시간**: 6-8주 (120-160시간)

---

## 🎖️ 오늘의 성과

1. **증거 기반 분석**: 110개 파일, 3,442개 위반 정량화
2. **전문가 합의**: 8인 페르소나 전원 합의로 승인
3. **보안 강화**: 치명적 결함 3개 즉시 제거
4. **자동화 구축**: Pre-commit + CI/CD 완성
5. **문서화**: 2,500+ 줄 종합 계획서

**다음 진행 시**: 이 문서를 참고하여 Option A 또는 C 선택 후 진행
