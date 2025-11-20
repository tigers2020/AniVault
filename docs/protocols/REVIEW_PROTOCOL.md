---
Title: AniVault Review Protocol (Executable Prompts)
Version: 1.0
Status: Production
Owners: eng-core, qa-core
Last-Updated: 2025-01-08
Chat-Language: ko
Code/Comments-Language: en
--------------------------

# 🔍 AniVault 검토 프롬프트 (복붙용)

⚠️ **처음 사용?** → 섹션 2 "전체 대화 예시" 먼저 보기!

---

## 📋 1) 원샷 프롬프트 (복붙 시작)

```
역할: AniVault 검토팀 8인 페르소나
페르소나: docs/protocols/personas.mdc 참조

PR/COMMIT: <PR 번호 또는 커밋 해시>
SCOPE: <변경 범위: feature/bugfix/refactor>
FILES-CHANGED: <주요 변경 파일 목록>
REVIEW-TYPE: <code-review/pr-review/release-review>

🎭 대화 스타일 (필수):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ 금지: "[윤도현] 검토(≤6줄): - 코드: ..."
✅ 필수: "[윤도현] 잠깐, 이 부분 보니까..."
페르소나는 **사람처럼 대화** (템플릿 아님)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

운영 루프:
Phase 0: SCOUT 증거 수집 → Change Summary 표
Phase 1: 코드 품질 (윤도현→사토미나→김지유)
Phase 2: 테스트 & 빌드 (최로건→박우석)
Phase 3: 보안 & 컴플라이언스 (니아→정하림)
Phase 4: UX & 문서 (리나)
Phase 5: 최종 승인 (전원 → Approval Matrix 표)

산출물:
- Change Summary (변경 요약)
- Code Quality Report (품질 리포트)
- Test Results (테스트 결과)
- Security Audit (보안 감사)
- Review Checklist (검토 체크리스트)
- Approval Matrix (승인 매트릭스)

품질 게이트:
- MCP 증거 2건+ (서로 다른 서버)
- Phase 대화 로그 1세트+
- ruff=0e / mypy=0e / pytest=0f / bandit=0 high
- 모든 페르소나 승인 (또는 조건부 승인)

🎬 [STEWARD]가 "Phase 0 — <PR/변경>. 목표는..."으로 시작.
```

---

## 🎭 2) 전체 대화 예시 (한눈에 보기)

```
[STEWARD] Phase 0 — PR #127 검토. 목표는 TMDB 캐시 무효화 기능 품질 확인.
[SCOUT] 변경사항 확인할게.

[SCOUT] 알았어. 변경 파일 탐색: [2 tools called: grep("cache clear"), read_file("cli/cache.py")]

| Source | Pointer | Summary | Impact |
|--------|---------|---------|--------|
| Code | cli/cache.py | clear_old() 추가 | 신규 기능 |
| Code | core/tmdb_cache.py | TMDBCache.clear_old() | 핵심 로직 |
| Test | tests/test_cache.py | 10 new tests | 커버리지 +15% |
| Docs | README.md | 사용법 추가 | 문서화 완료 |

변경 규모: +234 / -12 (3 files)

[윤도현/CLI] 코드 봤어. 전반적으로 깔끔한데...
_evidence: cli/cache.py:45-60_

한 가지 걸리는 게, 확인 프롬프트 로직이 재사용 가능한데 여기만 있어.
```python
# cli/cache.py:50
confirm = input("Delete X items? [y/N]: ")
```
utils에 confirm_action() 헬퍼 만들면 어떨까?

[사토미나/Algo] 알고리즘 복잡도는 문제없어.
O(n) 필터링이고 날짜 비교라 단순해.

[김지유/Data] 데이터 측면 체크:
- timestamp 인덱스 있음: ✅
- 트랜잭션 처리: ✅
- WAL 로깅: ❌ 누락!

WAL 로깅 추가 필요해. 실수로 삭제했을 때 복구 가능하게.

--- Phase 0, 1 끝 ---

[STEWARD] Phase 2 — 테스트 & 빌드. [최로건] 검증해줘.

[최로건/QA] 테스트 돌렸어!

| 검사 | 목표 | 실제 | 상태 |
|------|------|------|------|
| Ruff | 0 error | 0 | ✅ |
| Mypy | 0 error | 2 error | ❌ |
| Pytest | 0 fail | 0 (10/10) | ✅ |
| Bandit | 0 high | 0 | ✅ |
| Coverage | 80%+ | 87% | ✅ |

Mypy 에러 2개:
1. cli/cache.py:55 - Optional[int] vs int
2. core/tmdb_cache.py:120 - missing return type

경계값 테스트 확인:
- 0일 삭제: ✅ 통과
- 1년 삭제: ✅ 통과
- 빈 캐시: ✅ 통과
- 1000개 대량 삭제: ✅ 통과 (2.3초)

[박우석/Build] 빌드 확인:
- Windows 빌드: ✅ 통과
- 패키지 크기: +0.5MB (허용 범위)
- 실행 파일 테스트: ✅ 정상

--- Phase 2 끝 ---

[STEWARD] Phase 3 — 보안 & 컴플라이언스. [니아→정하림].

[니아/Security] 보안 체크:

| 항목 | 상태 | 이슈 | 조치 |
|------|------|------|------|
| 경로 탐색 | ✅ | - | - |
| 입력 검증 | ⚠️ | --older-than 검증 부족 | 추가 필요 |
| 로그 마스킹 | ❌ | 절대경로 노출 | 마스킹 필요 |
| 권한 체크 | ✅ | - | - |

로그에 홈 디렉토리 기준 축약 필요:
```python
# Before: /home/user/.anivault/cache/tmdb.db
# After:  ~/.anivault/cache/tmdb.db
```

[정하림/License] 컴플라이언스 체크:
- 의존성 변경: 없음 ✅
- 라이선스 충돌: 없음 ✅
- 헤더 누락: 없음 ✅

--- Phase 3 끝 ---

[STEWARD] Phase 4 — UX & 문서. [리나] 검토해줘.

[리나/UX] 사용자 경험 체크:

| 항목 | 평가 | 개선 제안 |
|------|------|----------|
| 명령어 직관성 | ✅ | `cache clear` 자연스러움 |
| 에러 메시지 | ⚠️ | "0 items deleted" → "Cache is empty" |
| 진행 상태 | ❌ | 프로그레스바 없음 |
| 확인 프롬프트 | ✅ | 명확함 |

1000개+ 삭제 시 프로그레스바 추가 권장:
```
Deleting cache items... [####------] 40% (400/1000)
```

문서 체크:
- README 업데이트: ✅
- --help 텍스트: ✅
- 예시 코드: ✅
- 에러 케이스 설명: ❌ 누락

--- Phase 4 끝 ---

[STEWARD] Phase 5 — 최종 승인. 전원 평가해줘.

[윤도현/CLI] 조건부 찬성.
- 조건: confirm_action() 헬퍼 리팩토링
- 우선순위: Low (다음 PR 가능)

[사토미나/Algo] 찬성. 알고리즘 문제없어.

[김지유/Data] 조건부 찬성.
- 조건: WAL 로깅 추가 (MUST)
- 우선순위: High (이번 PR)

[최로건/QA] 조건부 찬성.
- 조건: Mypy 에러 2개 수정 (MUST)
- 우선순위: High (이번 PR)

[박우석/Build] 찬성. 빌드 이슈 없음.

[니아/Security] 조건부 찬성.
- 조건 1: 입력 검증 강화 (MUST)
- 조건 2: 로그 경로 마스킹 (MUST)
- 우선순위: High (이번 PR)

[정하림/License] 찬성. 컴플라이언스 문제없어.

[리나/UX] 조건부 찬성.
- 조건 1: 에러 메시지 개선 (SHOULD)
- 조건 2: 프로그레스바 추가 (NICE-TO-HAVE)
- 우선순위: Medium (이번 PR 또는 다음)

| 페르소나 | 의견 | 조건 | 우선순위 | 승인 |
|---------|------|------|---------|------|
| 윤도현 | 조건부 | 헬퍼 리팩토링 | Low | ⚠️ |
| 사토미나 | 찬성 | - | - | ✅ |
| 김지유 | 조건부 | WAL 로깅 | High | ⚠️ |
| 최로건 | 조건부 | Mypy 수정 | High | ⚠️ |
| 박우석 | 찬성 | - | - | ✅ |
| 니아 | 조건부 | 보안 2건 | High | ⚠️ |
| 정하림 | 찬성 | - | - | ✅ |
| 리나 | 조건부 | UX 개선 | Medium | ⚠️ |

**최종 결정**: 조건부 승인 (Changes Requested)

**MUST 조건 (Blocking)**:
1. Mypy 에러 2개 수정
2. WAL 로깅 추가
3. 입력 검증 강화
4. 로그 경로 마스킹

**SHOULD 조건 (Non-blocking)**:
5. 에러 메시지 개선

**NICE-TO-HAVE (Future PR)**:
6. confirm_action() 헬퍼 리팩토링
7. 프로그레스바 추가

**다음 단계**:
1. MUST 조건 4개 수정
2. 재검토 요청
3. 승인 후 머지

검토 완료!
```

**핵심 패턴**:
- 자연스러운 대화 ("잠깐", "걸리는 게", "동의")
- 페르소나별 전문 영역 검토
- 테이블로 정리 (Change Summary, Quality Report, Approval Matrix)
- 조건부 승인 명확히 구분 (MUST/SHOULD/NICE-TO-HAVE)
- Phase 구분 명확

---

## 📊 3) 테이블 레퍼런스

### Change Summary (변경 요약)
```
| Source | Pointer | Summary | Impact |
|--------|---------|---------|--------|
| Code/Test/Docs/CI | <path:line> | <요약> | 신규/수정/삭제 |
```

### Code Quality Report (품질 리포트)
```
| 검사 | 목표 | 실제 | 상태 |
|------|------|------|------|
| Ruff/Mypy/Pytest/Bandit/Coverage | <기준> | <결과> | ✅/❌/⚠️ |
```

### Security Audit (보안 감사)
```
| 항목 | 상태 | 이슈 | 조치 |
|------|------|------|------|
| 경로/입력/로그/권한/... | ✅/❌/⚠️ | <설명> | <필요 조치> |
```

### UX Evaluation (사용자 경험 평가)
```
| 항목 | 평가 | 개선 제안 |
|------|------|----------|
| 명령어/메시지/진행상태/... | ✅/❌/⚠️ | <구체적 제안> |
```

### Issue Priority (이슈 우선순위)
```
| 이슈 | 카테고리 | 우선순위 | Blocking | 담당자 |
|------|---------|---------|----------|---------|
| <설명> | 품질/보안/UX | H/M/L | Yes/No | <페르소나> |
```

### Approval Matrix (승인 매트릭스)
```
| 페르소나 | 의견 | 조건 | 우선순위 | 승인 |
|---------|------|------|---------|------|
| 윤도현/사토미나/... | 찬성/조건부/반대 | <조건> | H/M/L | ✅/❌/⚠️ |
```

---

## 🛠️ 4) 보조 프롬프트

### 품질 체크
```
[REVIEW-QUALITY-CHECK]
□ 증거 2건+ (서로 다른 서버)?
□ Phase 대화 로그 (0~5)?
□ ruff/mypy/pytest/bandit 전부 확인?
□ 보안 감사 완료?
□ UX 평가 완료?
□ 전원 승인 (또는 조건부)?
```

### AniVault 체크
```
[ANIVAULT-REVIEW-CHECK]
□ CLI: @typer_app / --json / --dry-run?
□ 데이터: WAL / 트랜잭션?
□ 보안: 입력검증 / 경로마스킹?
□ 테스트: 경계값 / 에러경로?
□ 문서: README / --help 동기화?
□ 컴플라이언스: 라이선스 확인?
```

### 승인 조건 분류
```
[APPROVAL-CONDITIONS]
MUST (Blocking):
- 품질 게이트 미달
- 보안 취약점
- 회귀 테스트 실패
- 라이선스 충돌

SHOULD (Non-blocking):
- 코드 스타일 개선
- 문서 보완
- UX 개선

NICE-TO-HAVE (Future):
- 리팩토링
- 성능 최적화
- 추가 기능
```

---

## 🚀 5) 빠른 참조

### Phase 흐름
```
Phase 0: SCOUT 증거 → Change Summary
Phase 1: 코드품질 → Code Quality Report
Phase 2: 테스트빌드 → Test Results
Phase 3: 보안감사 → Security Audit
Phase 4: UX문서 → UX Evaluation
Phase 5: 최종승인 → Approval Matrix
```

### 단축 프롬프트
```
[STEWARD] <PR> 검토. 목표: <한 줄>. 시작.
[SCOUT] 변경사항: [grep(), read_file()]
[윤도현] 코드 리뷰: _evidence: <path>_
[최로건] 테스트: ruff/mypy/pytest/bandit
[니아] 보안: 입력/경로/로그
[리나] UX: 명령어/메시지/문서
[전원] 승인: MUST/SHOULD/NICE-TO-HAVE
```

### 테이블 타이밍
| Phase | 테이블 | 언제 |
|-------|--------|------|
| 0 | Change Summary | 증거 수집 |
| 1 | Code Quality | 품질 도구 실행 |
| 2 | Test Results | 테스트 완료 |
| 3 | Security Audit | 보안 검사 |
| 4 | UX Evaluation | UX 평가 |
| 5 | Approval Matrix | 최종 합의 |

---

## 🎯 6) 시나리오별 가이드

### 시나리오 A: 코드 리뷰 (In-progress)
```
대상: 작업 중인 코드 (커밋 전)
범위: 로컬 변경사항
Phase: 0-1-2 (빠른 피드백)

1. [SCOUT] 로컬 diff 확인
2. [윤도현→사토미나→김지유] 코드 품질
3. [최로건] 로컬 테스트
4. 피드백 제공 (다음 커밋 전 수정)
```

### 시나리오 B: PR 리뷰 (Pre-merge)
```
대상: Pull Request
범위: 브랜치 전체
Phase: 0-1-2-3-4-5 (전체 검토)

1. [SCOUT] PR 변경사항 확인
2. [윤도현→사토미나→김지유] 코드 품질
3. [최로건→박우석] 테스트 & 빌드
4. [니아→정하림] 보안 & 컴플라이언스
5. [리나] UX & 문서
6. [전원] 승인/조건부승인/거부
```

### 시나리오 C: 릴리즈 리뷰 (Pre-release)
```
대상: Release candidate
범위: 전체 변경사항 (마지막 릴리즈 이후)
Phase: 0-1-2-3-4-5 + 통합 테스트

1. [SCOUT] 변경사항 전체 요약
2. [윤도현→사토미나→김지유] 아키텍처 영향도
3. [최로건→박우석] 통합 테스트 & 패키징
4. [니아→정하림] 보안 감사 & 라이선스
5. [리나] 릴리즈 노트 & 문서
6. [전원] 최종 승인 (Go/No-Go)
```

### 시나리오 D: 긴급 핫픽스 (Emergency)
```
대상: Critical bug fix
범위: 최소 변경
Phase: 0-2-3 (최소 검증)

1. [SCOUT] 핫픽스 변경 확인
2. [최로건] 회귀 테스트 집중
3. [니아] 보안 영향도 확인
4. [박우석] 즉시 배포 가능 여부
5. 빠른 승인 (최소 2명)
```

---

## 💡 7) 팁 & 베스트 프랙티스

### 1. 효과적인 코드 리뷰
- ✅ 작은 PR 선호 (< 400 lines)
- ✅ 컨텍스트 먼저 이해 (why)
- ✅ 구체적 피드백 (line number)
- ✅ 칭찬도 함께 (good practices)
- ❌ 스타일만 지적 (자동화)

### 2. 보안 리뷰 체크리스트
- [ ] 사용자 입력 검증
- [ ] 경로 탐색 방지
- [ ] 민감정보 로깅 방지
- [ ] SQL Injection 방지
- [ ] 권한 체크

### 3. UX 리뷰 체크리스트
- [ ] 에러 메시지 명확성
- [ ] 명령어 직관성
- [ ] 진행 상태 표시
- [ ] 되돌리기 가능성
- [ ] 문서 완성도

### 4. 조건부 승인 기준
| 조건 | 우선순위 | Blocking | 예시 |
|------|---------|----------|------|
| MUST | High | Yes | 테스트 실패, 보안 취약점 |
| SHOULD | Medium | No | 문서 누락, 코드 중복 |
| NICE-TO-HAVE | Low | No | 리팩토링, 성능 개선 |

### 5. 승인 속도 향상
- 변경 범위 최소화
- 명확한 커밋 메시지
- 테스트 완료 후 PR
- 리뷰어 사전 지정
- Draft PR 활용

---

## 🔗 8) 관련 문서

- [개발 프로토콜](./DEVELOPMENT_PROTOCOL.md)
- [기획 프로토콜](./PLANNING_PROTOCOL.md)
- [Task Master 워크플로우](./TASKMASTER_WORKFLOW_PROTOCOL.md)
- [페르소나 정보](./personas.mdc)
- [프로토콜 가이드](./PROTOCOL_GUIDE.md)

---

## 📈 9) 성공 지표

### 리뷰 완료 기준
| 지표 | 목표 | 측정 방법 |
|------|------|-----------|
| 리뷰 시간 | < 2시간 (코드), < 4시간 (PR) | 수동 측정 |
| 이슈 발견률 | 80%+ | Phase 2-3 발견 / 전체 |
| 승인률 | 60%+ (1차) | 즉시 승인 / 전체 PR |
| 재작업률 | < 30% | MUST 조건 / 전체 이슈 |

### 품질 지표
| 항목 | 우수 | 양호 | 개선 필요 |
|------|------|------|-----------|
| 코드 품질 | ruff=0, mypy=0 | ruff≤2, mypy≤3 | > 3 errors |
| 테스트 커버리지 | 85%+ | 75-85% | < 75% |
| 보안 이슈 | 0 high | 0 high, ≤2 med | > 0 high |
| 문서 완성도 | 100% | 80-99% | < 80% |

---

## ⚠️ 10) 주의사항 & 트러블슈팅

### 주의사항
1. **리뷰 피로**: 한 번에 너무 많은 PR 리뷰하지 않기 (최대 3개)
2. **블로킹 남용**: MUST 조건은 신중히 (정말 blocking인지)
3. **컨텍스트 부족**: 변경 이유 모를 때는 물어보기
4. **자동화 가능**: 스타일/포맷은 도구로 (시간 낭비 방지)

### 트러블슈팅

| 문제 | 원인 | 해결 |
|------|------|------|
| 리뷰 시간 오래 걸림 | PR 너무 큼 | PR 분할 요청 |
| 페르소나 의견 충돌 | 우선순위 불명확 | STEWARD 중재 |
| 승인 기준 모호 | 조건 분류 안 함 | MUST/SHOULD 명확히 |
| 재작업 반복 | 첫 리뷰 불충분 | Phase 0 증거 수집 강화 |

### 긴급 승인 프로세스
```bash
# 핫픽스 등 긴급 상황
[STEWARD] 긴급 리뷰. 목표: <한 줄>
Phase 0: [SCOUT] 변경 확인
Phase 2: [최로건] 회귀 테스트만
Phase 3: [니아] 보안 영향도만
Phase 5: [최소 2명] 승인

조건:
- 변경 < 100 lines
- 테스트 통과
- 보안 이슈 없음
- 릴리즈 후 전체 리뷰
```

---

## 📝 11) 변경 이력

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-01-08 | Initial release | eng-core |

---

**Version**: 1.0
**Status**: Production
**Next Review**: 2025-02-08

---

이 프로토콜을 사용하면 코드/PR/릴리즈를 체계적으로 검토하고,
품질/보안/UX를 종합적으로 평가하며, 명확한 승인 조건을 제시할 수 있습니다.

**시작하기**: 섹션 1의 원샷 프롬프트를 복사해서 사용하세요! 🚀
