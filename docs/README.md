# AniVault 문서 센터

AniVault 프로젝트의 모든 문서와 가이드를 체계적으로 정리한 중앙 허브입니다.

> **📌 주요 업데이트 (2025-10-13)**: 문서 구조를 대폭 간소화하고 재정리했습니다.  
> - 과거 작업 기록은 `archive/`로 이동
> - `handbook`, `development`, `guidelines`를 `guides/`로 통합
> - TMDB 관련 문서를 `api/`로 통합

---

## 📁 문서 구조

### 🚀 [Guides](./guides/) - 개발 가이드 (★ 시작 여기)
새로운 개발자와 기여자를 위한 핵심 가이드입니다.

| 문서 | 설명 |
|-----|------|
| **[시작하기](./guides/getting-started.md)** | 환경 설정, 의존성 설치, 첫 번째 커밋 |
| **[개발 가이드](./guides/README.md)** | 일상적인 개발 워크플로우 |

### 🌐 [API](./api/) - TMDB API 통합
TMDB API 설정, Rate Limiting, 캐싱 전략에 관한 문서들입니다.

| 문서 | 설명 |
|-----|------|
| **[API 가이드](./api/README.md)** | TMDB API 통합 개요 |
| [설정 가이드](./api/tmdb-setup.md) | API 키 설정 및 환경 구성 |
| [Rate Limiting](./api/tmdb-rate-limiting-architecture.md) | Rate Limiting 아키텍처 |

### 🏗️ [Architecture](./architecture/) - 시스템 아키텍처
전체 시스템 설계와 핵심 컴포넌트 구조입니다.

| 문서 | 설명 |
|-----|------|
| **[전체 아키텍처](./architecture/ARCHITECTURE_ANIVAULT.md)** | 시스템 전체 구조 |
| [캐시 시스템](./architecture/cache_system.md) | 캐싱 전략 및 구현 |
| [파일 그룹화](./architecture/file-grouper.md) | 파일 그룹화 알고리즘 |

### 🎯 [Protocols](./protocols/) - 개발 프로토콜
개발 프로세스와 협업 규칙입니다.

| 문서 | 설명 |
|-----|------|
| **[프로토콜 가이드](./protocols/PROTOCOL_GUIDE.md)** | 전체 프로토콜 개요 |
| [개발 프로토콜](./protocols/DEVELOPMENT_PROTOCOL.md) | 실제 구현 단계 프로토콜 |
| [계획 프로토콜](./protocols/PLANNING_PROTOCOL.md) | 기획 및 설계 단계 |

### 👥 [Collaboration](./collaboration/) - 협업
Personas 시스템과 MCP 기반 협업 워크플로우입니다.

| 문서 | 설명 |
|-----|------|
| **[협업 프로토콜](./collaboration/COLLABORATIVE_DEVELOPMENT_PROTOCOL.md)** | 8인 전문가 협업 |
| [MCP 워크플로우](./collaboration/MCP_COLLABORATION_WORKFLOW.md) | MCP 도구 활용 |

### 🧪 [Testing](./testing/) - 테스트 및 품질
테스트 전략과 성능 벤치마크입니다.

| 문서 | 설명 |
|-----|------|
| [성능 벤치마크](./testing/performance-baseline-results.md) | 성능 테스트 결과 |
| [테스트 최적화](./testing/test-optimization-summary.md) | 테스트 최적화 결과 |

### 🚀 [Deployment](./deployment/) - 배포
배포 전략과 패키징 가이드입니다.

| 문서 | 설명 |
|-----|------|
| [PyInstaller 결과](./deployment/pyinstaller-poc-results.md) | PyInstaller POC |
| [Windows 호환성](./deployment/windows-multi-version-execution-test-results.md) | Windows 테스트 |

### 🔒 [Security](./security/) - 보안
보안 정책과 가이드라인입니다.

| 문서 | 설명 |
|-----|------|
| [AI 보안 가이드라인](./security/ai-security-guidelines.md) | AI 보안 규칙 |
| [보안 교육](./security/ai-security-training.md) | 보안 교육 자료 |

### 📊 [Benchmarks](./benchmarks/) - 벤치마크
성능 측정 결과입니다.

| 문서 | 설명 |
|-----|------|
| [벤치마크 결과](./benchmarks/BENCHMARKS.md) | 전체 벤치마크 결과 |

### 📋 [Compliance](./compliance/) - 라이선스 준수
오픈소스 라이선스 컴플라이언스입니다.

| 문서 | 설명 |
|-----|------|
| [PySide6 LGPL](./compliance/PYSIDE6_LGPL_COMPLIANCE.md) | PySide6 라이선스 준수 |

### 🗂️ [Archive](./archive/) - 과거 기록
과거 작업 기록과 레거시 문서들입니다.

| 폴더 | 설명 |
|-----|------|
| `stages/` | STAGE 1-8 요약 |
| `tasks/` | TASK 완료 기록 |
| `phases/` | PHASE 완료 기록 |
| `refactoring-history/` | 리팩토링 과정 |
| `handbook/` | 구 핸드북 (→ guides) |
| `development/` | 구 개발 가이드 (→ guides) |
| `guidelines/` | 구 가이드라인 (→ guides) |

---

## 🎯 빠른 시작 가이드

### 새로운 개발자라면?
1. **[시작하기](./guides/getting-started.md)** - 환경 설정부터
2. **[전체 아키텍처](./architecture/ARCHITECTURE_ANIVAULT.md)** - 시스템 구조 파악
3. **[개발 가이드](./guides/README.md)** - 개발 워크플로우

### 새로운 기능을 개발한다면?
1. **[계획 프로토콜](./protocols/PLANNING_PROTOCOL.md)** - 계획 단계
2. **[개발 프로토콜](./protocols/DEVELOPMENT_PROTOCOL.md)** - 구현 단계
3. **[협업 프로토콜](./collaboration/COLLABORATIVE_DEVELOPMENT_PROTOCOL.md)** - 팀 협업

### TMDB API 연동이 필요하다면?
1. **[TMDB API 가이드](./api/README.md)** - API 설정
2. **[Rate Limiting](./api/tmdb-rate-limiting-architecture.md)** - Rate Limit 관리
3. **[캐시 시스템](./architecture/cache_system.md)** - 캐싱 전략

---

## 📊 문서 통계

| 카테고리 | 문서 수 | 상태 |
|---------|--------|------|
| **Guides** | 2 | ✅ 활성 |
| **API** | 7 | ✅ 활성 |
| **Architecture** | 5 | ✅ 활성 |
| **Protocols** | 7 | ✅ 활성 |
| **Collaboration** | 5 | ✅ 활성 |
| **Testing** | 3 | ✅ 활성 |
| **Deployment** | 3 | ✅ 활성 |
| **Security** | 5 | ✅ 활성 |
| **Archive** | 40+ | 📦 보관 |

---

## 🔄 문서 유지보수

### 문서 업데이트 규칙
- 새로운 기능 추가 시 관련 문서 업데이트
- 아키텍처 변경 시 architecture/ 문서 업데이트
- API 변경 시 api/ 문서 업데이트
- 문서 버전 관리 (문서 하단에 버전 표기)

### 문서 작성 가이드
- 명확하고 간결한 제목
- 목차 (TOC) 포함
- 코드 예시 포함
- 관련 문서 링크 포함

### 문서 리뷰
- PR에 문서 변경 포함
- 기술 리뷰어 검토
- 문서 품질 검사

---

**문서 버전**: 2.0  
**최종 업데이트**: 2025-10-13  
**관리자**: AniVault 문서팀  
**구조 개선**: handbook/development/guidelines → guides, 과거 기록 → archive
