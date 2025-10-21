# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2024-12-19

### Added
- **GUI 실행 스크립트**: Windows, Linux, macOS용 GUI 실행 스크립트 추가
  - `run_gui.bat` (Windows)
  - `run_gui.sh` (Linux/macOS)
  - `run_gui.py` (크로스 플랫폼)
- **공유 모델 시스템**: `src/anivault/shared/models/` 디렉토리 추가
- **자동 설정 파일 생성**: GUI에서 자동으로 설정 파일 생성 기능
- **환경 변수 오버라이드 시스템**: 설정 파일 우선순위 시스템 구현
- **폴더 보안 설정**: 향상된 보안 설정 모델
- **경로 빌더 개선**: 연도별 정리 기능 강화
- **GUI 설정 다이얼로그**: 사용자 친화적인 설정 인터페이스

### Changed
- **설정 템플릿 업데이트**: `config/config.toml.template` 개선
- **자동 스캐너 개선**: 더 정확한 파일 스캔 알고리즘
- **정리기 메인 로직**: 성능 최적화 및 안정성 향상
- **경로 빌더**: 연도별 분류 로직 개선

### Fixed
- **Import 오류 수정**: MetadataEnricher 조건부 import 구현
- **테스트 파일 정리**: 중복된 테스트 파일 제거
- **타입 안정성**: GUI 컴포넌트 타입 오류 수정
- **메모리 누수**: 캐시 시스템 최적화

### Security
- **보안 설정 강화**: 폴더 접근 권한 검증
- **환경 변수 보안**: 민감한 정보 마스킹 개선
- **파일 시스템 보안**: 안전한 파일 처리 로직

### Performance
- **캐시 성능 향상**: SQLite WAL 모드 최적화
- **메모리 사용량 감소**: 효율적인 메모리 관리
- **스캔 속도 개선**: 병렬 처리 최적화

### Documentation
- **개발 가이드 업데이트**: 새로운 기능 사용법 추가
- **API 문서 개선**: TMDB 통합 가이드 강화
- **설정 가이드**: 환경 변수 설정 방법 추가

## [0.1.0] - 2024-12-01

### Added
- **초기 릴리즈**: AniVault CLI 기본 기능
- **TMDB API 통합**: 애니메이션 메타데이터 자동 수집
- **파일 정리 시스템**: 스마트 파일 분류 및 정리
- **GUI 인터페이스**: PySide6 기반 사용자 인터페이스
- **캐시 시스템**: 고성능 SQLite 캐시
- **롤백 기능**: 작업 되돌리기 지원
- **다국어 지원**: 한국어/영어 지원
- **테마 시스템**: 라이트/다크 테마 지원

### Features
- 자동 애니메이션 파일 인식
- TMDB 메타데이터 매칭
- 해상도별 파일 분류
- 자막 파일 자동 매칭
- 배치 처리 지원
- 오프라인 모드 지원
- 상세한 로깅 시스템
- JSON 출력 지원
