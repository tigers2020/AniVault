# 🎯 AniVault 프로토콜 가이드

**버전**: 2.1 (compact)
**업데이트**: 2025-01-03

**핵심**: 복붙 가능한 프롬프트로 페르소나 대화형 개발

---

## 🚀 프롬프트 기반 개발

| 기존 | 새로운 |
|------|--------|
| 문서 읽기 → 이해 → 적용 | 복사 → 채우기 → 실행 |
| 수동 증거 수집 | MCP 자동 증거 |
| 개인마다 다른 해석 | 일관된 실행 |

---

## 📋 2가지 프로토콜

### 1. 기획 (v4.1, 220줄)
- **5 Phase** × 8인 대화
- **50~75분**
- **사용**: 새 기능, 아키텍처 변경

### 2. 개발 (v3.1, 200줄)
- **4 Round** × 8인 대화
- **20~40분**
- **사용**: 구현, 버그 수정

---

## 👥 8인 페르소나

| 이름 | Phase/Round | 전문 |
|------|------------|------|
| Steward | 모든 단계 | 조율 |
| 윤도현 | 설계·구현 | CLI |
| 사토 미나 | 설계·구현 | 알고리즘 |
| 김지유 | 설계·구현 | 데이터 |
| 리나 | 설계·구현 | UX |
| 박우석 | 위험·검증 | 빌드 |
| 최로건 | 위험·검증 | QA |
| 니아 | 위험·검증 | 보안 |
| 정하림 | 위험·검증 | 라이선스 |

---

## 📊 5가지 테이블

| 테이블 | 사용 시점 | 효과 |
|--------|----------|------|
| Evidence Log | 증거 수집 | 재사용/신규 판단 |
| Tradeoff | 설계 비교 | 선택 근거 |
| Quality Dashboard | 테스트 결과 | 품질 파악 |
| Risks & Mitigations | 위험 분석 | 완화 추적 |
| Consensus | 합의 정리 | 상태 확인 |

---

## 🎯 프로세스 선택

### 기획 필요
- ✅ 새 기능
- ✅ 아키텍처 변경
- ✅ 대규모 리팩토링

### 개발만
- ✅ 버그 수정
- ✅ 소규모 개선
- ✅ 테스트 추가

---

## 🚀 빠른 시작

### 기획 시작
```bash
open PLANNING_PROTOCOL.md
# 섹션 1 "원샷 프롬프트" 복사
# <GOAL/NON-GOALS/CONSTRAINTS> 채우기
# AI에게 실행
```

### 개발 시작
```bash
open DEVELOPMENT_PROTOCOL.md
# 섹션 1 "원샷 프롬프트" 복사
# <TASK/CONTEXT/DONE-WHEN> 채우기
# AI에게 실행
```

---

## ⚙️ 품질 게이트

```bash
ruff check src/    # 0 errors
mypy src/         # 0 errors
pytest tests/     # 0 failures
bandit -r src/    # 0 high

# AniVault 특화
□ @typer_app / --json / --dry-run
□ WAL / operation_id
□ safe_params() / 경로 마스킹
```

---

## 💡 핵심 규칙

1. **대화체** (템플릿 아님)
2. **증거 필수** (_evidence: <path>_)
3. **테이블 활용** (5종)
4. **MCP 로그** (Phase/Round마다)
5. **품질 게이트** (4종 검사)

---

## 🔗 링크

- [기획](./PLANNING_PROTOCOL.md) - v4.1
- [개발](./DEVELOPMENT_PROTOCOL.md) - v3.1
- [페르소나](./personas.mdc)

---

**v2.1 (compact)**: 253줄 → 130줄
