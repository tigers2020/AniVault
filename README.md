# AniVault CLI

AniVault CLI는 TMDB API를 활용한 애니메이션 파일 정리 도구입니다.

## 특징

- **단일 실행파일**: Windows .exe 파일 하나로 실행
- **TMDB 통합**: The Movie Database API를 활용한 메타데이터 매칭
- **레이트리밋 준수**: 429 에러 처리 및 Retry-After 존중
- **JSON 캐시**: 효율적인 메타데이터 캐싱
- **UTF-8 지원**: 전역 UTF-8 인코딩
- **멀티스레딩**: 병렬 처리로 성능 최적화

## 설치

### 개발 환경

```bash
# 의존성 설치
pip install -e .

# 개발 의존성 설치
pip install -e ".[dev]"
```

### 단일 실행파일 빌드

```bash
# PyInstaller로 빌드
pyinstaller tools/bundle_poc/console_onefile.spec

# 또는 직접 명령어
pyinstaller -F -n anivault --console -p src --collect-all anitopy src/cli/main.py
```

## 사용법

### 기본 사용법

```bash
# TMDB API 키 설정
set TMDB_API_KEY=your_api_key_here

# 애니메이션 파일 정리 (드라이런)
anivault run --src D:\Anime --dst E:\Vault --dry-run --lang ko-KR

# 실제 정리 실행
anivault run --src D:\Anime --dst E:\Vault --lang ko-KR --rate 35 --tmdb-concurrency 4
```

### 명령어 옵션

- `--src`: 소스 디렉터리 (필수)
- `--dst`: 대상 디렉터리 (필수)
- `--lang`: 언어 코드 (기본값: ko-KR)
- `--rate`: 초당 요청 수 (기본값: 35)
- `--tmdb-concurrency`: TMDB 동시 요청 수 (기본값: 4)
- `--dry-run`: 실제 변경 없이 시뮬레이션
- `--log-level`: 로그 레벨 (DEBUG, INFO, WARNING, ERROR)

## 아키텍처

### 핵심 모듈

- **CLI**: Click 기반 명령어 인터페이스
- **TMDB Client**: 레이트리밋 및 재시도 로직이 포함된 API 클라이언트
- **JSON Cache**: TTL 및 스키마 버전 관리
- **로깅**: UTF-8 지원 파일 로테이션

### 레이트리밋 상태머신

1. **Normal**: 정상 API 호출
2. **Throttle**: 429 에러 후 제한 모드
3. **CacheOnly**: API 호출 중단, 캐시만 사용

## 개발

### 프로젝트 구조

```
anivault/
├── src/
│   ├── cli/           # CLI 인터페이스
│   ├── core/          # 핵심 비즈니스 로직
│   ├── services/      # 외부 서비스 (TMDB)
│   ├── cache/         # 캐시 관리
│   └── utils/         # 유틸리티
├── tools/             # 빌드 도구
├── docs/              # 문서
└── tests/             # 테스트
```

### 테스트

```bash
# 전체 테스트 실행
pytest

# 커버리지 포함
pytest --cov=src

# 특정 테스트
pytest tests/test_tmdb_client.py
```

## 라이선스

MIT License

## 기여

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request