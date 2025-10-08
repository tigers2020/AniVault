# 📋 AniVault 프로토콜 - 복붙 프롬프트

**버전**: 2.1 (compact)  
**업데이트**: 2025-01-03

---

## 🚀 3단계로 시작

```
1. 프롬프트 복사 → 2. <변수> 채우기 → 3. AI에게 실행
```

---

## 📁 문서

### 1. [기획 프로토콜](./PLANNING_PROTOCOL.md) (v4.1, 220줄)
- **5개 Phase** × 8인 페르소나 대화
- **50~75분** 예상
- **산출물**: PRD-lite, Evidence, Risks, WBS
- **사용**: 새 기능, 아키텍처 변경, 대규모 리팩토링

### 2. [개발 프로토콜](./DEVELOPMENT_PROTOCOL.md) (v3.1, 200줄)
- **4개 Round** × 8인 페르소나 대화
- **20~40분** 예상
- **산출물**: Evidence, WBS, Patch, Tests, Changelog
- **사용**: 기능 구현, 버그 수정, 소규모 개선

### 3. [Task Master 워크플로우 프로토콜](./TASKMASTER_WORKFLOW_PROTOCOL.md) (v1.0)
- **6개 Phase** × 8인 페르소나 대화
- **30~60분** 예상
- **산출물**: Tag, PRD, Tasks, Complexity Report, Subtasks
- **사용**: 새 기능 태그 설정, PRD→태스크 변환, 복잡도 분석, 서브태스크 생성

### 4. [프로토콜 가이드](./PROTOCOL_GUIDE.md) (v2.0)
- 프로토콜 선택 기준
- 프로세스 플로우
- 빠른 시작 가이드

### 5. [페르소나 정보](./personas.mdc)
- 8인 전문가 프로필

---

## 👥 8인 페르소나

| 이름 | 역할 | 전문 영역 |
|------|------|----------|
| Protocol Steward | 리더 | 조율, 의사결정 |
| 윤도현 | CLI/백엔드 | CLI, 아키텍처 |
| 사토 미나 | 알고리즘 | 매칭, 성능 |
| 김지유 | 데이터 품질 | 데이터, WAL |
| 리나 하트만 | UX | UI/UX, CLI UX |
| 박우석 | 빌드/릴리즈 | CI/CD, 배포 |
| 최로건 | 테스트/QA | 테스트, 검증 |
| 니아 오코예 | 보안 | 보안, 마스킹 |
| 정하림 | 라이선스 | 컴플라이언스 |

---

## 📊 핵심 테이블 (5종)

1. **Evidence Log**: 증거 수집
2. **Tradeoff**: 의사결정
3. **Quality Dashboard**: 품질 검증
4. **Risks & Mitigations**: 위험 관리
5. **Consensus**: 합의 추적

---

## 🎯 빠른 시작

### 새 기능 기획
```bash
open PLANNING_PROTOCOL.md
# → 섹션 1 복사 → <변수> 채우기 → 실행
```

### 기능 개발
```bash
open DEVELOPMENT_PROTOCOL.md
# → 섹션 1 복사 → <변수> 채우기 → 실행
```

### Task Master 설정
```bash
open TASKMASTER_WORKFLOW_PROTOCOL.md
# → 섹션 1 복사 → <변수> 채우기 → 실행
```

---

## 💡 핵심 규칙

1. **대화체**: "좋아", "잠깐", "동의" (템플릿 아님)
2. **증거 필수**: _evidence: <path>_
3. **테이블 활용**: 상황별 5종
4. **품질 게이트**: ruff/mypy/pytest/bandit 0

---

**시작**: [프로토콜 가이드](./PROTOCOL_GUIDE.md)

**v2.1 (compact)**: 153줄 → 80줄
