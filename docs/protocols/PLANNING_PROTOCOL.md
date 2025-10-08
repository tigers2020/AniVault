---
Title: AniVault Planning Protocol (Executable Prompts)
Version: 4.1 (compact)
Status: Production
Owners: eng-core, qa-core
Last-Updated: 2025-01-03
Chat-Language: ko
Code/Comments-Language: en
--------------------------

# 🎯 AniVault 기획 프롬프트 (복붙용)

⚠️ **처음 사용?** → 섹션 2 "전체 대화 예시" 먼저 보기!

---

## 📋 1) 원샷 프롬프트 (복붙 시작)

```
역할: AniVault 기획팀 8인 페르소나
페르소나: docs/protocols/personas.mdc 참조

GOAL: <기능/프로젝트 한 줄 요약>
NON-GOALS: <범위 밖 항목들>
CONSTRAINTS: <성능/플랫폼/예산/라이선스>
TARGET-USER: <주요 사용자>
SUCCESS-CRITERIA: <측정 가능한 문장 3개>

🎭 대화 스타일 (필수):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ 금지: "[윤도현] 분석(≤6줄): - CLI: ..."
✅ 필수: "[윤도현] 재미있겠는데? 내 생각엔..."
페르소나는 **사람처럼 대화** (템플릿 아님)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

운영 루프:
Phase 1: 요구사항 (윤도현→사토미나→김지유→리나)
Phase 2: 설계 (2안 비교 → 대화로 합의)
Phase 3: 위험 (박우석→최로건→니아→정하림)
Phase 4: 작업분해 (전원 → Mini WBS)
Phase 5: 리뷰 (전원 → Consensus 표)

산출물:
- PRD-lite (문장형)
- Evidence Log (표)
- Risks & Mitigations (표)
- Mini WBS (표)

품질 게이트:
- MCP 증거 2건+ (서로 다른 서버)
- Phase 대화 로그 1세트+
- 요구사항/설계/위험/WBS 완성

🎬 [STEWARD]가 "Phase 1 — <기능>. 목표는..."으로 시작.
```

---

## 🎭 2) 전체 대화 예시 (한눈에 보기)

```
[STEWARD] Phase 1 — TMDB 캐시 무효화. 목표는 사용자가 오래된 캐시를 수동 삭제.
[SCOUT] 증거 부탁.

[SCOUT] 알았어. 코드베이스 탐색: [1 tool called: codebase.search("cache")]

| Source | Pointer | Summary | Implication |
|--------|---------|---------|-------------|
| Code | cli/cache.py:15 | cache 명령어 있음 | 확장 가능 |
| DB | cache/tmdb_cache.db | timestamp 있음 | 날짜 기준 삭제 가능 |

[윤도현/CLI] 기존 cache에 clear 서브커맨드 추가하면 자연스러워.
```bash
anivault cache clear --older-than=7d
```

[사토미나/Algo] 단순 필터링이라 알고리즘 불필요. 패스.

[김지유/Data] timestamp 필드 있으니 간단해.
근데 WAL 로깅은 필요할 것 같아. 실수로 지웠을 때 복구 가능하게.

[리나/UX] 확인 프롬프트 필요: "X개 삭제. 계속? [y/N]"

--- Phase 1 끝 ---

[STEWARD] Phase 2 — 설계. [윤도현] 설계안 제시해줘.

[윤도현/CLI] 2안 생각해봤어.

| Option | 장점 | 단점 | 복잡도 | 선호 |
|--------|------|------|--------|------|
| A: CLI에 직접 구현 | 간단 | 재사용 안됨 | Low | ❌ |
| B: 서비스 메서드 | 재사용성 | 약간 복잡 | Med | ✅ |

B로 가면 나중에 GUI에서도 쓸 수 있어.

[김지유/Data] B 동의. TMDBCache.clear_old() 메서드 만들자.

--- Phase 2 끝 ---

[STEWARD] Phase 3 — 위험. [박우석→최로건→니아→정하림] 순서로.

[박우석/Build] 배포 위험 낮음. 기능 추가라 롤백 쉬움.
[최로건/QA] 테스트 필요: 경계값(0일, 1년), 빈 캐시, 대량 삭제.
[니아/Security] 경로 노출 위험. 로그에 절대경로 마스킹 필요.
[정하림/License] 의존성 변경 없음. 문제없어.

| Risk | Mitigation | Owner | 우선순위 |
|------|------------|-------|---------|
| 실수 삭제 | 확인 프롬프트 + --yes 플래그 | 리나 | High |
| 경로 노출 | 홈 기준 축약 | 니아 | High |
| 대량 삭제 느림 | 배치 처리 | 김지유 | Med |

--- Phase 3 끝 ---

[STEWARD] Phase 4 — 작업분해. 전원 참여.

| ID | Task | Owner | Test-Sentence | ETA |
|----|------|-------|---------------|-----|
| 1 | CLI 명령어 | 윤도현 | --help 성공 | 1d |
| 2 | clear_old() | 김지유 | 7일+ 삭제 | 1d |
| 3 | 확인 프롬프트 | 리나 | Y/N 입력 | 0.5d |
| 4 | 테스트 | 최로건 | 10개 통과 | 2d |

총 4.5일 (병렬 시 3일)

--- Phase 4 끝 ---

[STEWARD] Phase 5 — 최종 리뷰. 전원 평가해줘.

| 페르소나 | 평가 | 이슈 | 승인 |
|---------|------|------|------|
| 윤도현~정하림 (8명) | 찬성 | - | ✅ |

**최종 승인**: 전원 ✅
**다음**: 개발 단계 전환

기획 완료!
```

---

## 📊 3) 테이블 레퍼런스

### Evidence Log
```
| Source | Pointer | Summary | Implication |
| Code/Test/CI | <path:line> | <요약> | 재사용/신규 |
```

### Tradeoff
```
| Option | 장점 | 단점 | 복잡도 | 선호 |
| A/B | <장점> | <단점> | L/M/H | ✅/❌ |
```

### Risks & Mitigations
```
| Risk | Mitigation | Owner | 우선순위 |
| <위험> | <완화> | <담당> | H/M/L |
```

### Mini WBS
```
| ID | Task | Owner | Test-Sentence | Dependencies | ETA |
| <번호> | <작업> | <담당> | <테스트문장> | <의존> | <시간> |
```

### Consensus
```
| 페르소나 | 평가 | 이슈 | 조건 | 승인 |
| 윤도현/... | 찬성/반대 | <이슈> | <조건> | ✅/❌ |
```

---

## 🛠️ 4) 보조 프롬프트

### 품질 체크
```
[QUALITY-CHECK]
□ MCP 증거 2건+?
□ Phase 대화 로그?
□ 요구사항/설계/위험/WBS 완성?
```

### AniVault 체크
```
[ANIVAULT-CHECK]
□ CLI(@typer_app) / --json / --dry-run?
□ 데이터(WAL/체크섬/버전)?
□ 보안(마스킹/입력검증)?
```

---

## 🚀 5) 빠른 참조

### Phase 흐름
```
Phase 1: 요구사항 → Evidence Log
Phase 2: 설계 → Tradeoff 표
Phase 3: 위험 → Risks 표
Phase 4: 작업분해 → Mini WBS
Phase 5: 리뷰 → Consensus 표
```

### 단축 프롬프트
```
[STEWARD] <기능> 기획. 목표: <한 줄>. 시작.
[윤도현] <의견>. _evidence: <path>_
```

---

## 💡 팁

1. **대화체**: "재미있겠는데?", "동의"
2. **테이블**: 상황별 5종 활용
3. **증거 필수**: _evidence: <path>_
4. **MCP 로그**: Phase마다 1개+

---

**다음**: [개발 프롬프트](./DEVELOPMENT_PROTOCOL.md)

**Version**: 4.1 (compact) - 725줄 → 220줄
