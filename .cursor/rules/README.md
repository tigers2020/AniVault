# AniVault Cursor Rules

## 최적화된 규칙 구조 (25개 → 8개)

### **핵심 규칙 (8개)**
1. **`python_development.mdc`** - Python 개발 표준 (통합)
2. **`system_standards.mdc`** - 시스템 표준 (통합)
3. **`quality_assurance.mdc`** - 품질 보증 (통합)
4. **`project_management.mdc`** - 프로젝트 관리 (통합)
5. **`file_processing.mdc`** - 파일 처리 패턴
6. **`packaging.mdc`** - 패키징 및 배포
7. **`tmdb_api.mdc`** - TMDB API 클라이언트
8. **`taskmaster/`** - Taskmaster 워크플로우

## 최적화 결과

### **통합된 규칙들**
- **`python_development.mdc`**: `python_core.mdc` + `code_quality.mdc` + `naming_conventions.mdc` 통합
- **`system_standards.mdc`**: `utf8_encoding.mdc` + `logging.mdc` 통합
- **`quality_assurance.mdc`**: `error_handling.mdc` + `testing.mdc` 통합
- **`project_management.mdc`**: `cursor_rules.mdc` 확장

### **삭제된 규칙들 (17개)**
- `python_core.mdc` → `python_development.mdc`에 통합
- `code_quality.mdc` → `python_development.mdc`에 통합
- `naming_conventions.mdc` → `python_development.mdc`에 통합
- `utf8_encoding.mdc` → `system_standards.mdc`에 통합
- `logging.mdc` → `system_standards.mdc`에 통합
- `error_handling.mdc` → `quality_assurance.mdc`에 통합
- `testing.mdc` → `quality_assurance.mdc`에 통합
- `cursor_rules.mdc` → `project_management.mdc`에 통합
- `async_patterns.mdc` → `python_development.mdc`에 통합
- `database_patterns.mdc` → `quality_assurance.mdc`에 통합
- `gui_patterns.mdc` → `quality_assurance.mdc`에 통합
- `performance.mdc` → `quality_assurance.mdc`에 통합
- `python_tooling.mdc` → `python_development.mdc`에 통합
- `mcp_server_utilization.mdc` → `project_management.mdc`에 통합
- `self_improve.mdc` → `project_management.mdc`에 통합
- `agents.mdc` → `project_management.mdc`에 통합

## AniVault 프로젝트 특성 반영

### **애니메이션 파일 관리 CLI 도구**
- **Python CLI**: Click + Rich 기반
- **TMDB API**: 애니메이션 메타데이터 연동
- **파일 처리**: anitopy 파싱
- **UTF-8 지원**: 국제화 필수
- **Nuitka**: 단일 실행파일 패키징 (PyInstaller 대안)

### **핵심 개발 패턴**
- **타입 힌트 필수**: 모든 함수에 타입 힌트
- **에러 처리**: 구조적 로깅 + 사용자 친화적 메시지
- **테스트**: 실패 우선 테스트 패턴
- **코드 품질**: One Source of Truth + SRP + 매직 값 제거
- **UTF-8**: 전역 UTF-8 인코딩 강제

## 사용 가이드

### **새 코드 작성 시**
1. `python_development.mdc` - Python 개발 표준
2. `system_standards.mdc` - 시스템 레벨 표준
3. `quality_assurance.mdc` - 품질 보증 및 테스트
4. `project_management.mdc` - 프로젝트 관리

### **API 연동 시**
- `tmdb_api.mdc` - TMDB API 패턴

### **파일 처리 시**
- `file_processing.mdc` - 파일 스캔, 파싱 패턴

### **패키징 시**
- `packaging.mdc` - Nuitka/PyInstaller 설정

## 성능 개선

- **규칙 수**: 25개 → 8개 (68% 감소)
- **중복 제거**: 17개 규칙 통합/삭제
- **프로젝트 특화**: AniVault에 맞는 규칙만 유지
- **유지보수성**: 통합된 규칙으로 관리 용이
- **일관성**: 통합된 규칙으로 일관된 가이드라인
