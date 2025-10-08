# AniVault

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/tigers2020/AniVault/workflows/CI/badge.svg)](https://github.com/tigers2020/AniVault/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

> **⚠️ 법적 고지**: 이 도구는 개인 라이브러리 정리 전용입니다. 합법적으로 소유한 콘텐츠만 사용하세요.

TMDB API를 활용한 애니메이션 파일 자동 정리 시스템입니다.

## 🚀 빠른 시작

### 1. 설치
```bash
pip install -e .
```

### 2. 환경 설정
```bash
cp env.template .env
# .env 파일에서 TMDB_API_KEY 설정
```

### 3. 사용법 (3단계)
```bash
# 1. 스캔: 애니메이션 파일 발견 및 파싱
anivault scan /path/to/anime

# 2. 매칭: TMDB와 메타데이터 매칭
anivault match /path/to/anime

# 3. 정리: 파일 자동 정리
anivault organize /path/to/anime --dry-run  # 미리보기
anivault organize /path/to/anime            # 실제 정리
```

**또는 한 번에 실행:**
```bash
anivault run /path/to/anime
```

## ✨ 주요 기능

- 🎯 **자동 인식**: 애니메이션 파일 자동 파싱 (anitopy 기반)
- 🌐 **TMDB 연동**: 한국어 제목 지원, 메타데이터 자동 수집
- 📁 **스마트 정리**: 해상도별 분류, 자막 파일 자동 매칭
- 💾 **고성능 캐시**: SQLite WAL 모드, 오프라인 지원
- 🔄 **롤백 지원**: 모든 작업 기록 및 되돌리기 기능
- 🖥️ **GUI 지원**: PySide6 기반 사용자 인터페이스

## 📋 CLI 명령어

### 기본 명령어
```bash
anivault scan <directory>     # 파일 스캔
anivault match <directory>    # TMDB 매칭
anivault organize <directory> # 파일 정리
anivault run <directory>      # 전체 워크플로우
```

### 유틸리티 명령어
```bash
anivault log list                    # 작업 로그 확인
anivault rollback <timestamp>        # 작업 되돌리기
anivault verify <directory>          # 정리 결과 검증
```

### 공통 옵션
```bash
--dry-run          # 미리보기 모드
--yes              # 확인 프롬프트 건너뛰기
--verbose          # 상세 출력
--json-output      # JSON 형식 출력
--log-level LEVEL  # 로그 레벨 설정
```

## 🔧 고급 기능

### Enhanced Organize
- 파일명 유사성 기반 그룹핑
- 해상도별 자동 분류
- 자막 파일 자동 매칭
- 배치 처리 지원

### 캐시 시스템
- TMDB API 응답 캐싱 (24시간 TTL)
- SQLite WAL 모드로 동시성 보장
- 오프라인 모드 지원
- 캐시 무효화 및 관리

### 보안 및 성능
- TMDB API 레이트 리밋 준수
- 지수 백오프 재시도
- 민감한 데이터 로그 마스킹
- 멀티스레딩 지원

## 📚 상세 문서

- [설치 가이드](docs/installation.md)
- [사용법 가이드](docs/usage.md)
- [TMDB API 설정](docs/tmdb-setup.md)
- [문제 해결](docs/troubleshooting.md)
- [개발자 가이드](docs/development.md)

## 🛠️ 개발

### 개발 환경 설정
```bash
git clone https://github.com/tigers2020/AniVault.git
cd AniVault
pip install -e ".[dev]"  # Install with development dependencies
pre-commit install
```

### 테스트 실행
```bash
pytest tests/
ruff check src/
mypy src/
bandit -r src/
```

## 📄 라이선스

MIT License - 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

기여하기 전에 [CONTRIBUTING.md](CONTRIBUTING.md)를 읽어주세요.

## 📞 지원

- 🐛 버그 리포트: [Issues](https://github.com/tigers2020/AniVault/issues)
- 💡 기능 요청: [Discussions](https://github.com/tigers2020/AniVault/discussions)
- 📧 이메일: [프로젝트 페이지](https://github.com/tigers2020/AniVault)

---

**AniVault** - 애니메이션 컬렉션을 깔끔하게 정리하세요! 🎌
