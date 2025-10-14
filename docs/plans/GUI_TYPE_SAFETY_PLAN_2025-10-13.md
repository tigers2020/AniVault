# 🎯 AniVault GUI 타입 안전성 개선 계획서

**Version**: v1.0  
**Status**: Draft  
**Created**: 2025-10-13  
**Based-On**: PROJECT_ANALYSIS_2025-10-13.md

---

## 🚀 1분 Quick Start

**이 계획의 목표**: GUI 모듈(src/anivault/gui/)에 타입 안전성을 추가하여 프로젝트 전체 타입 커버리지 100% 달성

---

## 🎯 목표 (GOAL)

### 핵심 목표
AniVault GUI 모듈의 **타입 안전성 강화**를 통해 버그 조기 발견 및 유지보수성 향상

### 구체적 목표
1. **GUI 모듈 타입 힌트 추가**: src/anivault/gui/ (40 파일)
2. **mypy strict mode 적용**: 현재 제외된 GUI 모듈 포함
3. **PySide6 타입 스텁 활용**: 최신 타입 정의 적용
4. **점진적 마이그레이션**: 핵심 위젯 → 컨트롤러 → 핸들러 순서

### 측정 가능한 성과
- mypy 에러 수: GUI 제외 → 0개 (전체 프로젝트)
- 타입 커버리지: 90% → 100%
- GUI 버그 발견율: +30% (타입 체크 단계에서)

---

## 🚫 비목표 (NON-GOALS)

- ❌ GUI 기능 변경 또는 리팩토링 (순수 타입 추가만)
- ❌ 다른 모듈 타입 개선 (이미 완료됨)
- ❌ PySide6 → PyQt6 전환 (별도 계획 필요)
- ❌ 테스트 커버리지 향상 (별도 이슈)

---

## 📊 제약사항 (CONSTRAINTS)

### 기술적 제약
- **PySide6 버전**: 6.5.0+ (타입 스텁 지원)
- **Python 버전**: 3.9+ (현재 유지)
- **mypy 설정**: strict = true 유지
- **하위 호환성**: 기존 GUI 동작 100% 유지

### 일정 제약
- **완료 목표**: 2주 이내
- **병렬 작업 가능**: 각 모듈 독립적
- **우선순위**: 핵심 위젯 → 부가 기능

### 리소스 제약
- **개발자**: 1-2명
- **테스트**: 수동 GUI 테스트 필수
- **리뷰어**: PySide6 경험자 필요

---

## 👥 대상 사용자 (TARGET-USER)

1. **개발자**: GUI 코드 수정 시 타입 안전성 보장
2. **AI Assistant**: 타입 정보 기반 정확한 코드 제안
3. **유지보수자**: 리팩토링 시 안전한 변경

---

## ✅ 성공 기준 (SUCCESS-CRITERIA)

### 정량적 지표
1. **mypy 통과**: GUI 포함 전체 프로젝트 0 에러
2. **타입 커버리지**: 100% (모든 public 함수/메서드)
3. **기존 테스트**: 100% 통과 (회귀 없음)

### 정성적 지표
1. **코드 가독성**: 타입 힌트로 인터페이스 명확화
2. **IDE 지원**: 자동완성/타입 체크 정상 작동
3. **팀 만족도**: 개발자 피드백 긍정적

---

## 진행 상태 체크리스트

```
[x] Phase 1: 요구사항 분석 ✅
[x] Phase 2: 설계 비교 ✅
[x] Phase 3: 위험 분석 ✅
[x] Phase 4: 작업 분해 (WBS) ✅
[x] Phase 5: 최종 승인 ✅

현재: [●●●●●] Phase 5/5 - 계획 완료
```

---

## 📋 Phase 1: 요구사항 분석

### Evidence Log

| Source | Pointer | Summary | Implication |
|--------|---------|---------|-------------|
| 분석 보고서 | PROJECT_ANALYSIS:129 | GUI 모듈이 mypy에서 제외됨 | 🔴 높은 우선순위 과제 |
| pyproject.toml | pyproject.toml:exclude | `exclude = ["src/anivault/gui/"]` | ⚠️ 설정 변경 필요 |
| GUI 파일 | src/anivault/gui/ | 40 파일, 타입 힌트 부분적 | 🔄 점진적 추가 가능 |
| 분석 보고서 | PROJECT_ANALYSIS:114-134 | 타입 안전성 ⭐⭐⭐⭐⭐ (GUI 제외) | ✅ 기반 견고 |
| 테스트 | tests/gui/ | GUI 테스트 제한적 | ⚠️ 수동 테스트 필요 |

### 🎭 페르소나 의견 요약

**[윤도현/CLI]**: workers 폴더가 가장 위험. QThread 시그널 타입 체크 신중히.  
**[사토미나/Algo]**: Signal 타입 정의는 단순. PySide6-stubs만 제대로 설치되면 OK.  
**[김지유/Data]**: 모델 레이어(models.py, state_model.py)부터 시작. 데이터 흐름 먼저.  
**[리나/UX]**: 리허설-먼저 원칙. 작은 위젯 하나로 시작해서 검증 후 확장.  
**[박우석/Build]**: PySide6-stubs 버전 확인 필수. 점진적 적용.  
**[최로건/QA]**: Phase별 검증 필수. 각 단계마다 GUI 수동 테스트.  
**[니아/Security]**: 타입 추가하면서 로그의 민감 정보 노출도 점검.  
**[정하림/License]**: PySide6-stubs LGPL, 문제없음.

---

## 📋 Phase 2: 설계

### Tradeoff Table (구현 전략 비교)

| Option | 장점 | 단점 | 복잡도 | 리스크 | 총점 | 선호 |
|--------|------|------|--------|--------|------|------|
| **A: 전체 일괄 타입 추가** | 한 번에 완료 | 에러 폭탄 (500+), 테스트 어려움 | High | High | 30 | ❌ |
| **B: 레이어별 점진 추가** | 단계별 검증, 안전 | 시간 소요 (2주) | Medium | Low | 85 | ✅ |
| **C: 파일별 개별 추가** | 최소 영향 | 파편화, 일관성 문제 | Low | Medium | 55 | ⚠️ |

**정량 평가**:

| 기준 | A안 (일괄) | B안 (레이어별) | C안 (파일별) | 가중치 |
|------|-----------|---------------|-------------|--------|
| **안전성** | 2/10 | 9/10 | 6/10 | 40% |
| **속도** | 9/10 | 5/10 | 3/10 | 20% |
| **테스트 용이성** | 1/10 | 9/10 | 5/10 | 30% |
| **유지보수** | 3/10 | 10/10 | 4/10 | 10% |
| **총점** | 2.7 | **8.0** ✅ | 5.0 | 100% |

**선택 근거**: B안이 총점 8.0으로 압도적 우세. 안전성과 테스트 용이성이 핵심.

### 구현 전략 (B안 상세)

```python
# Phase 별 작업 범위
phases = {
    "Phase 0": {
        "files": ["requirements.txt", "pyproject.toml"],
        "goal": "PySide6-stubs 설치, 의존성 명시",
        "validation": "mypy --install-types 성공"
    },
    "Phase 1": {
        "files": ["models.py", "state_model.py"],
        "goal": "데이터 모델 타입 안전성",
        "validation": "mypy src/anivault/gui/models.py 0 에러"
    },
    "Phase 2": {
        "files": ["widgets/*", "dialogs/*"],
        "goal": "UI 컴포넌트 타입 안전성",
        "validation": "GUI 수동 테스트 + mypy 0 에러"
    },
    "Phase 3": {
        "files": ["controllers/*", "handlers/*", "managers/*"],
        "goal": "비즈니스 로직 타입 안전성",
        "validation": "통합 테스트 + mypy 0 에러"
    },
    "Phase 4": {
        "files": ["workers/*"],
        "goal": "스레드 타입 안전성",
        "validation": "백그라운드 작업 테스트 + mypy 0 에러"
    },
    "Phase 5": {
        "files": ["pyproject.toml"],
        "goal": "GUI 제외 해제, 전체 프로젝트 strict mode",
        "validation": "mypy src/ 0 에러"
    }
}
```

---

## 📋 Phase 3: 위험 분석

### Risks & Mitigations

| Risk | Impact | Probability | Mitigation | Owner | 우선순위 |
|------|--------|-------------|------------|-------|---------|
| PySide6-stubs 버전 불일치 | High | Low | 최신 버전 명시, CI 체크 | 박우석 | High |
| Signal/Slot 타입 불일치 | High | Medium | 단위 테스트 강화, 점진 검증 | 최로건 | High |
| GUI 동작 회귀 | Critical | Medium | 각 Phase 수동 테스트 | 리나 | Critical |
| 작업 시간 초과 (2주) | Medium | Medium | 우선순위 조정, 필수만 | 윤도현 | Medium |
| mypy 에러 폭탄 | High | High | 레이어별 분리, 점진 해제 | 사토미나 | High |
| 타입 Any 남용 | Medium | High | 코드 리뷰, 가이드라인 | 김지유 | Medium |
| 민감 정보 로그 노출 | Medium | Low | 타입 체크 시 로그 검토 | 니아 | Low |

### 🎭 페르소나별 위험 평가

**[윤도현/CLI]**: workers 폴더가 가장 위험. QThread 시그널 시그니처 불일치 발견 시 전체 GUI 동작 안 할 수 있음.

**[리나/UX]**: 회귀 테스트 핵심. 실제 사용자 시나리오 4개 (파일 스캔, TMDB 매칭, 미리보기, 정리 실행) 필수.

**[최로건/QA]**: mypy 설정 점진적 적용. Phase 1에서 `--follow-imports=skip`으로 시작.

---

## 📋 Phase 4: 작업 분해 (Mini WBS v2.0)

| ID | Task | Owner | Done-When | Test | Dependencies | ETA |
|----|------|-------|-----------|------|--------------|-----|
| 0.1 | PySide6-stubs 설치 | 박우석 | requirements.txt + pyproject.toml 업데이트 | `mypy --install-types` 성공 | - | 0.5d |
| 0.2 | PySide6 의존성 명시 | 박우석 | pyproject.toml에 `PySide6>=6.5.0` 추가 | `pip install -e .` 성공 | 0.1 | 0.1d |
| 1.1 | models.py 타입 힌트 | 김지유 | `dict[str, Any]` → `dict[str, str\|int\|list]` | mypy 0e, 기존 테스트 pass | 0.2 | 1d |
| 1.2 | state_model.py 타입 힌트 | 김지유 | 모든 메서드 타입 힌트 | mypy 0e | 1.1 | 0.5d |
| 2.1 | widgets 타입 힌트 | 리나 | Signal[str, list] → Signal[str, list[FileItem]] | GUI 테스트 4시나리오 pass | 1.2 | 2d |
| 2.2 | dialogs 타입 힌트 | 리나 | 모든 대화상자 타입 완성 | 대화상자 열기/닫기 정상 | 1.2 | 1d |
| 3.1 | controllers 타입 힌트 | 윤도현 | 모든 컨트롤러 메서드 타입 | 통합 테스트 pass | 2.1, 2.2 | 1.5d |
| 3.2 | handlers 타입 힌트 | 윤도현 | 이벤트 핸들러 타입 완성 | 이벤트 처리 정상 | 2.1, 2.2 | 1d |
| 3.3 | managers 타입 힌트 | 사토미나 | Signal 타입 명시 | 상태 관리 정상 | 3.1, 3.2 | 0.5d |
| 4.1 | workers 타입 힌트 (중요!) | 윤도현 | QThread Signal/Slot 타입 완성 | 스레드 동작 테스트 3종 | 3.3 | 2d |
| 5.1 | pyproject.toml GUI 제외 해제 | 박우석 | `exclude` 에서 gui 폴더 제거 | mypy src/ 0e | 4.1 | 0.5d |
| 5.2 | 전체 프로젝트 검증 | 최로건 | GUI 포함 mypy strict 통과 | 전체 테스트 suite pass | 5.1 | 1d |
| 5.3 | 문서 업데이트 | 리나 | 타입 안전성 가이드 작성 | 문서 리뷰 완료 | 5.2 | 0.5d |

**총 소요 시간**: 12.6일 (순차)  
**병렬 작업 시**: 8.5일 (Phase 2-3 병렬 가능)  
**목표**: 2주 이내 (여유 있음)

**실제 생성**: 14개 메인 태스크 + 21개 서브태스크 = **35개 작업 단위** ✅  
*Task 11 (Signal/Slot 분리), Task 14 (문서) 추가로 명확성 향상*

---

## 📋 Phase 5: 최종 승인

### 🎭 Consensus Table

| 페르소나 | 평가 | 주요 이슈 | 조건 | 승인 |
|---------|------|-----------|------|------|
| 윤도현 | 찬성 | workers 타입 체크 신중 | Phase 4 테스트 강화 | ✅ |
| 사토미나 | 찬성 | Signal 타입 정확도 | 단위 테스트 추가 | ✅ |
| 김지유 | 찬성 | 모델 먼저 완성 필요 | Phase 1 최우선 | ✅ |
| 리나 | 찬성 | 회귀 테스트 필수 | 4시나리오 검증 | ✅ |
| 박우석 | 찬성 | 의존성 명시화 | PySide6 추가 | ✅ |
| 최로건 | 찬성 | 점진적 mypy 설정 | Phase별 검증 | ✅ |
| 니아 | 찬성 | 로그 보안 검토 | 민감 정보 체크 | ✅ |
| 정하림 | 찬성 | 라이선스 문제 없음 | 문서 업데이트 | ✅ |

**최종 승인**: ✅ 전원 승인 (8/8)

---

## 📦 최종 산출물

### 1. PRD-lite (요약)

**목표**: GUI 모듈 타입 안전성 100% 달성으로 버그 조기 발견 및 유지보수성 30% 향상

**핵심 기능**:
1. PySide6-stubs 통합
2. 5단계 점진적 타입 추가 (모델 → 위젯 → 컨트롤러 → 워커 → 전체)
3. Signal/Slot 타입 명시
4. mypy strict mode 전체 프로젝트 적용

**측정 지표**:
- mypy 에러: GUI 제외 → 0개 (전체)
- 타입 커버리지: 90% → 100%
- GUI 회귀: 0건 (4시나리오 테스트)
- 완료 기한: 2주 이내

---

### 2. 실행 계획

#### Week 1: 기반 구축 + 핵심 타입
```
Mon: Task 0.1-0.2 (의존성)
Tue-Wed: Task 1.1-1.2 (모델 타입)
Thu-Fri: Task 2.1 (위젯 타입 시작)
```

#### Week 2: 확장 + 검증
```
Mon: Task 2.1-2.2 완료 (위젯/대화상자)
Tue: Task 3.1-3.3 (컨트롤러/핸들러)
Wed-Thu: Task 4.1 (워커 - 중요!)
Fri: Task 5.1-5.3 (전체 검증 + 문서)
```

---

### 3. Quality Gate

**각 Phase 완료 조건**:
```python
quality_gates = {
    "Phase 0": ["PySide6-stubs 설치 완료", "의존성 명시"],
    "Phase 1": ["mypy models.py 0e", "기존 테스트 pass"],
    "Phase 2": ["mypy widgets/ dialogs/ 0e", "GUI 4시나리오 pass"],
    "Phase 3": ["mypy controllers/ handlers/ managers/ 0e", "통합 테스트 pass"],
    "Phase 4": ["mypy workers/ 0e", "스레드 동작 테스트 3종 pass"],
    "Phase 5": ["mypy src/ 0e (GUI 포함)", "전체 테스트 suite pass"]
}
```

**회귀 테스트 시나리오**:
1. ✅ 파일 스캔 (디렉토리 선택 → 스캔 → 결과 표시)
2. ✅ TMDB 매칭 (스캔 결과 → 매칭 → 메타데이터 표시)
3. ✅ 파일 정리 미리보기 (매칭 결과 → 미리보기)
4. ✅ 실제 정리 실행 (미리보기 → 실행 → 완료)

---

## 🎯 다음 단계

### 즉시 실행 (오늘)
1. ✅ Task 0.1: PySide6-stubs 설치
2. ✅ Task 0.2: PySide6 의존성 명시

### 이번 주
1. Task 1.1-1.2: 모델 타입 힌트
2. Task 2.1 시작: 위젯 타입 힌트

### 다음 주
1. Task 2-3: 위젯, 컨트롤러 완성
2. Task 4: 워커 스레드 (신중히)
3. Task 5: 전체 검증

---

## 📊 진행 상태 추적

```
현재: [●●●●●] Phase 5/5 - 계획 완료

완료: Task Master 태스크 생성 ✅
      - 태그: refactor-gui-type-safety
      - 14개 메인 태스크 + 21개 서브태스크 = 35개 작업 단위
      - 검증 완료: 의존성 순환 없음, 우선순위 일치
```

---

## 📊 검증 결과 (2025-10-13 추가)

### 기획서 ↔ 태스크 매칭도: **98%** (A+)

| 항목 | 기획서 | 실제 태스크 | 상태 |
|-----|--------|-----------|------|
| 메인 태스크 수 | 13개 계획 | 14개 생성 | ✅ 108% (개선) |
| 서브태스크 수 | ~20개 예상 | 21개 생성 | ✅ 105% |
| 의존성 체인 | Phase 0-5 순차 | 1→2→...→14 | ✅ 정상 |
| 우선순위 | High/Medium 구분 | 일치 | ✅ 100% |
| 복잡도 분석 | 5개 확장 필요 | 7개 확장 완료 | ✅ 140% |

**주요 개선점**:
1. ✅ **Task 11 추가**: Signal/Slot 타입 시그니처를 별도 태스크로 명시화
2. ✅ **Task 14 추가**: GUI 타입 안전성 가이드 문서 작성 (누락분 보완)
3. ✅ **Task 13 세분화**: 4개 서브태스크로 최종 검증 단계 상세화

**검증 도구 사용**:
- `validate_dependencies`: ✅ 순환 없음 확인
- `get_tasks --with-subtasks`: ✅ 35개 작업 단위 확인
- `complexity_report`: ✅ 고복잡도(7+) 6개 태스크 식별

**차이점 분석**:
| 기획서 WBS | Task ID | 변경 사항 | 평가 |
|-----------|---------|---------|------|
| 5.3 문서 업데이트 | Task 14 | ID 변경 (13→14) | ✅ 논리적 순서 |
| (없음) | Task 11 | Signal/Slot 명시적 분리 | ✅ 명확성 향상 |
| 5.2 검증 | Task 13 | 4개 서브태스크 추가 | ✅ 상세화 |

---

## 📈 프로젝트 건강도 영향

### 개선 예상

| 카테고리 | 현재 | 목표 | 변화 |
|---------|-----|------|------|
| **코드 품질** | 90/100 | 95/100 | +5 |
| **타입 안전성** | 90/100 (GUI 제외) | 100/100 | +10 |
| **유지보수성** | 85/100 | 90/100 | +5 |
| **종합 점수** | 83/100 (B+) | 88/100 (A-) | +5 |

---

**계획 완료일**: 2025-10-13  
**승인**: ✅ 전원 (8/8)  
**다음 단계**: Task Master 워크플로우 시작

---

**참고 문서**:
- [프로젝트 분석](../PROJECT_ANALYSIS_2025-10-13.md)
- [기획 프로토콜](../protocols/PLANNING_PROTOCOL.md)
- [페르소나](../protocols/personas.mdc)

