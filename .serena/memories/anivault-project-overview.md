# AniVault v3 CLI 프로젝트 개요

## 프로젝트 목표
- **Windows 단일 실행파일(.exe) 1개**의 CLI 앱 개발
- TMDB API를 활용한 애니메이션 파일 자동 정리 시스템
- 레이트리밋 준수, JSON 캐시, UTF-8 전제, 스레드 필수

## 핵심 기술 스택
- **CLI**: Click 8.1.0
- **TMDB API**: tmdbv3api 1.9.0
- **파일 파싱**: anitopy 2.1.1 (C 확장)
- **UI**: rich 14.1.0
- **암호화**: cryptography 41.0.0
- **패키징**: PyInstaller 6.16.0

## 현재 상태
- Phase 1 기반 구축 단계
- 8개 주요 작업이 정의됨
- 첫 번째 작업: 프로젝트 구조 및 의존성 초기화

## 개발 계획
- 36주 개발 기간 (3개 페이즈)
- Phase 1: 기반 구축 (W1-W12)
- Phase 2: 핵심 기능 개발 (W13-W24)
- Phase 3: 안정화 & 릴리스 (W25-W36)
