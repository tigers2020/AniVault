# AniVault 협업 개발 프로토콜

Personas 가상 개발자들과 MCP 서버 기능을 활용한 다중 협업 개발 프로토콜입니다.

## 📋 프로토콜 개요

이 프로토콜은 AniVault 프로젝트에서 **8명의 전문가 personas**와 **MCP 서버 도구들**을 활용하여 실제 팀 협업과 같은 개발 환경을 구현합니다.

## 👥 협업 팀 구성

### 핵심 개발팀 (Core Development Team)

#### 1. **윤도현 (Python 백엔드/CLI 전문가)**
- **전문 분야**: CLI 아키텍처, 백엔드 서비스, 파이프라인 설계
- **핵심 원칙**: "하나의 의도, 하나의 명령", "실패가 더 설명적이어야 한다"
- **MCP 도구**: `mcp_serena_find_symbol`, `mcp_serena_search_for_pattern`

#### 2. **사토 미나 (메타데이터/매칭 알고리즘 전문가)**
- **전문 분야**: 매칭 알고리즘, 점수 함수, 데이터 분석
- **핵심 원칙**: "가정은 점수로 말하라", "후보는 숨기지 말고 근거를 노출"
- **MCP 도구**: `mcp_sequential-thinking_sequentialthinking`

#### 3. **김지유 (데이터 품질/카탈로그 전문가)**
- **전문 분야**: 데이터 무결성, 스키마 관리, 감사 추적
- **핵심 원칙**: "영수증 드리븐 개발", "쓰기 전에 저널링"
- **MCP 도구**: `mcp_task-master-ai_*` (태스크 관리)

### 지원팀 (Support Team)

#### 4. **리나 하트만 (PySide6 GUI 전문가)**
- **전문 분야**: GUI 설계, 사용자 경험, PySide6 개발
- **핵심 원칙**: "사용자 중심 설계", "접근성 우선"

#### 5. **박우석 (Windows 패키징 전문가)**
- **전문 분야**: PyInstaller, 배포, Windows 호환성
- **핵심 원칙**: "크로스 플랫폼 호환성", "사용자 친화적 설치"

#### 6. **최로건 (테스트 자동화/QA 전문가)**
- **전문 분야**: 테스트 전략, 자동화, 품질 보증
- **핵심 원칙**: "테스트 우선 개발", "회귀 방지"

#### 7. **니아 오코예 (보안·프라이버시 전문가)**
- **전문 분야**: 보안 설계, 프라이버시 보호, 안전 운영
- **핵심 원칙**: "보안은 기본", "최소 권한 원칙"

#### 8. **정하림 (오픈소스 라이선스 전문가)**
- **전문 분야**: 라이선스 관리, 컴플라이언스, 법적 리스크
- **핵심 원칙**: "라이선스 투명성", "법적 안전성"

## 🔄 협업 프로세스

### Phase 1: 초기 기획 및 역할 분담

#### 1.1 요구사항 분석 (윤도현 주도)
```markdown
**MCP 도구 활용:**
- `mcp_task-master-ai_initialize_project` - 프로젝트 초기화
- `mcp_task-master-ai_parse_prd` - 요구사항 문서 파싱
- `mcp_serena_find_symbol` - 기존 코드베이스 분석

**협업 프로세스:**
1. 윤도현이 CLI 관점에서 요구사항 분석
2. 사토 미나가 알고리즘 관점에서 검토
3. 김지유가 데이터 관점에서 검증
4. 나머지 전문가들이 각자 관점에서 피드백
```

#### 1.2 아키텍처 설계 (팀 전체 협업)
```markdown
**MCP 도구 활용:**
- `mcp_sequential-thinking_sequentialthinking` - 설계 의사결정
- `mcp_serena_search_for_pattern` - 기존 패턴 분석
- `mcp_task-master-ai_add_task` - 세부 작업 분해

**협업 프로세스:**
1. 윤도현: CLI 구조 및 백엔드 아키텍처 제안
2. 사토 미나: 매칭 알고리즘 및 데이터 플로우 검토
3. 김지유: 데이터 스키마 및 무결성 요구사항
4. 리나 하트만: GUI/UX 관점에서 사용자 경험 검토
5. 박우석: 배포 및 패키징 관점에서 기술적 제약 검토
6. 최로건: 테스트 전략 및 품질 보증 계획
7. 니아 오코예: 보안 및 프라이버시 요구사항
8. 정하림: 라이선스 및 법적 요구사항 검토
```

### Phase 2: 구현 단계별 협업

#### 2.1 코어 로직 구현 (윤도현 + 사토 미나 + 김지유)
```markdown
**MCP 도구 활용:**
- `mcp_serena_find_symbol` - 기존 함수/클래스 분석
- `mcp_serena_replace_symbol_body` - 코드 구현
- `mcp_sequential-thinking_sequentialthinking` - 알고리즘 검토

**협업 프로세스:**
1. 윤도현: CLI 인터페이스 및 백엔드 서비스 구현
2. 사토 미나: 매칭 알고리즘 및 점수 함수 구현
3. 김지유: 데이터 처리 파이프라인 및 무결성 보장
4. 실시간 코드 리뷰 및 피드백 교환
```

#### 2.2 GUI 구현 (리나 하트만 주도)
```markdown
**MCP 도구 활용:**
- `mcp_serena_find_symbol` - GUI 컴포넌트 분석
- `mcp_serena_insert_after_symbol` - 새로운 GUI 요소 추가

**협업 프로세스:**
1. 리나 하트만: PySide6 기반 GUI 설계 및 구현
2. 윤도현: CLI와 GUI 간 인터페이스 조정
3. 최로건: GUI 테스트 케이스 작성
4. 니아 오코예: 사용자 데이터 보안 검토
```

#### 2.3 테스트 및 품질 보증 (최로건 주도)
```markdown
**MCP 도구 활용:**
- `mcp_task-master-ai_expand_task` - 테스트 케이스 확장
- `mcp_serena_search_for_pattern` - 테스트 패턴 분석

**협업 프로세스:**
1. 최로건: 종합적인 테스트 전략 수립
2. 각 전문가가 자신의 영역별 테스트 케이스 검토
3. 윤도현: CLI 테스트 케이스
4. 사토 미나: 알고리즘 정확성 테스트
5. 김지유: 데이터 무결성 테스트
6. 니아 오코예: 보안 테스트
```

### Phase 3: 배포 및 패키징 (박우석 주도)

#### 3.1 패키징 및 배포 준비
```markdown
**MCP 도구 활용:**
- `mcp_task-master-ai_get_tasks` - 배포 태스크 확인
- `mcp_serena_find_symbol` - 배포 관련 코드 분석

**협업 프로세스:**
1. 박우석: PyInstaller 기반 패키징 설계
2. 윤도현: CLI 명령과 패키징 통합
3. 리나 하트만: GUI와 패키징 통합
4. 정하림: 라이선스 및 의존성 검토
5. 니아 오코예: 보안 배포 요구사항
```

## 🛠️ MCP 도구별 활용 전략

### Task Master AI 활용
```bash
# 프로젝트 초기화 및 태스크 관리
mcp_task-master-ai_initialize_project --projectRoot . --rules cursor
mcp_task-master-ai_parse_prd --input docs/requirements/feature_prd.md
mcp_task-master-ai_get_tasks --withSubtasks true
mcp_task-master-ai_next_task
mcp_task-master-ai_expand_task --id=1 --research true
```

### Serena 활용
```bash
# 코드베이스 분석 및 탐색
mcp_serena_find_symbol --name_path "MatchingEngine" --relative_path src/anivault
mcp_serena_search_for_pattern --substring_pattern "def.*match.*" --relative_path src/anivault
mcp_serena_get_symbols_overview --relative_path src/anivault/core/matching
```

### Sequential Thinking 활용
```bash
# 복잡한 의사결정 및 알고리즘 검토
mcp_sequential-thinking_sequentialthinking --thought "매칭 알고리즘의 가중치를 어떻게 최적화할까?" --nextThoughtNeeded true
mcp_sequential-thinking_sequentialthinking --thought "CLI 사용자 경험을 개선하기 위한 옵션 설계는?" --nextThoughtNeeded true
```

## 📝 협업 시나리오 예시

### 시나리오 1: 새로운 매칭 알고리즘 개발

#### 1단계: 기획 (윤도현 + 사토 미나)
```markdown
**윤도현의 관점:**
- CLI 명령으로 새로운 매칭 알고리즘을 어떻게 노출할 것인가?
- 사용자가 알고리즘 파라미터를 조정할 수 있는 옵션은?
- 성능 모니터링을 위한 로깅은 어떻게 할 것인가?

**사토 미나의 관점:**
- 어떤 특징(features)을 사용할 것인가?
- 각 특징의 가중치는 어떻게 설정할 것인가?
- 매칭 결과의 투명성을 어떻게 보장할 것인가?

**MCP 도구 활용:**
- `mcp_sequential-thinking_sequentialthinking` - 알고리즘 설계 검토
- `mcp_task-master-ai_add_task` - 세부 작업 분해
```

#### 2단계: 구현 (사토 미나 + 김지유)
```markdown
**사토 미나의 구현:**
- 데이터카드 작성 (가설, 특징, 라벨링 규칙)
- 점수 함수 구현 (투명한 계산, 근거 제공)
- 시각화 및 검증 도구

**김지유의 검증:**
- 데이터 무결성 보장 (Write-Ahead Log)
- 스냅샷 기반 검증
- 롤백 가능한 구현

**MCP 도구 활용:**
- `mcp_serena_replace_symbol_body` - 알고리즘 구현
- `mcp_serena_insert_after_symbol` - 검증 로직 추가
```

#### 3단계: 테스트 (최로건 + 전체팀)
```markdown
**최로건의 테스트 전략:**
- 단위 테스트: 각 점수 함수별 테스트
- 통합 테스트: 전체 매칭 파이프라인 테스트
- 성능 테스트: 대용량 데이터 처리 테스트

**전체팀 검토:**
- 윤도현: CLI 인터페이스 테스트
- 사토 미나: 알고리즘 정확성 검증
- 김지유: 데이터 무결성 테스트
- 니아 오코예: 보안 테스트
```

### 시나리오 2: GUI 인터페이스 추가

#### 1단계: 설계 (리나 하트만 + 윤도현)
```markdown
**리나 하트만의 설계:**
- PySide6 기반 GUI 아키텍처
- 사용자 경험 중심의 인터페이스 설계
- 접근성 고려사항

**윤도현의 통합:**
- CLI와 GUI 간 데이터 공유 방식
- 백엔드 서비스와 GUI 연결
- 에러 처리 및 로깅 통합

**MCP 도구 활용:**
- `mcp_sequential-thinking_sequentialthinking` - GUI 설계 검토
- `mcp_serena_find_symbol` - 기존 백엔드 서비스 분석
```

#### 2단계: 구현 (리나 하트만 + 박우석)
```markdown
**리나 하트만의 구현:**
- PySide6 컴포넌트 구현
- 사용자 인터페이스 로직
- 이벤트 처리 및 상태 관리

**박우석의 패키징:**
- GUI 포함 패키징 전략
- 의존성 관리
- 크로스 플랫폼 호환성

**MCP 도구 활용:**
- `mcp_serena_insert_after_symbol` - GUI 컴포넌트 추가
- `mcp_task-master-ai_expand_task` - GUI 관련 태스크 확장
```

## 📊 협업 품질 지표

### 코드 품질 지표
- **전문가별 리뷰 완료율**: 100% (모든 전문가가 자신의 영역 검토)
- **MCP 도구 활용률**: 각 단계별 적절한 도구 사용
- **코드 커버리지**: 90% 이상
- **성능 지표**: 기존 대비 성능 저하 10% 이내

### 협업 효과성 지표
- **의사결정 품질**: Sequential Thinking 활용으로 체계적 검토
- **코드 일관성**: Serena 도구로 기존 패턴 준수
- **태스크 완료율**: Task Master AI로 체계적 관리
- **지식 공유**: 각 전문가의 관점이 코드에 반영

## 🔄 지속적 개선

### 협업 프로세스 개선
- **분기별 회고**: 협업 프로세스 효과성 평가
- **도구 활용도 분석**: MCP 도구별 사용 효과 측정
- **전문가 피드백**: 각 personas의 관점에서 개선점 도출

### 지식 축적
- **패턴 라이브러리**: 성공적인 협업 패턴 문서화
- **베스트 프랙티스**: 각 전문가별 모범 사례 수집
- **실패 사례 학습**: 문제 상황과 해결 방법 기록

---

**문서 버전**: 1.0  
**최종 업데이트**: 2024-01-XX  
**다음 검토 예정일**: 2024-04-XX  
**관리자**: AniVault 협업팀
