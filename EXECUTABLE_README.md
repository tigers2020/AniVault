# AniVault 실행 파일 사용 가이드

## 📦 배포 패키지 구성

```
AniVault/
├── AniVault.exe          # 메인 실행 파일
├── config/               # 설정 파일 (자동 생성됨)
│   └── config.toml      # 애플리케이션 설정
└── env.template         # 환경 변수 템플릿
```

## 🚀 첫 실행 준비

### 1. TMDB API 키 설정 (필수)

AniVault는 TMDB (The Movie Database) API를 사용합니다.

**API 키 발급:**
1. [TMDB 웹사이트](https://www.themoviedb.org/)에 가입
2. 계정 설정 > API 메뉴에서 API 키 신청
3. API 키(v3)를 복사

**환경 변수 설정:**

```powershell
# 방법 1: 시스템 환경 변수 설정 (권장)
setx TMDB_API_KEY "your_api_key_here"

# 방법 2: .env 파일 생성 (실행 파일과 같은 폴더)
# env.template을 .env로 복사하고 편집
```

`.env` 파일 예시:
```
TMDB_API_KEY=your_actual_api_key_here
```

### 2. 실행

```powershell
# 더블클릭하거나 터미널에서
.\AniVault.exe
```

## 🔧 설정 파일 (선택)

첫 실행 시 `config/config.toml` 파일이 자동으로 생성됩니다.
필요에 따라 수정 가능합니다.

```toml
[app]
name = "AniVault"
version = "1.0.0"
debug = false
theme = "dark"  # "light" 또는 "dark"

[logging]
level = "INFO"
format = "text"

[tmdb]
# API 키는 환경 변수에서 자동으로 로드됩니다
language = "ko-KR"
region = "KR"

[file_processing]
max_workers = 4
batch_size = 50

[cache]
enabled = true
ttl_seconds = 604800  # 7일
```

## 🐛 문제 해결

### 실행이 안 될 때

1. **콘솔 모드로 실행하여 에러 확인:**
   ```powershell
   # 현재 빌드는 디버그 모드입니다
   # 콘솔 창에서 에러 메시지를 확인하세요
   ```

2. **TMDB API 키 확인:**
   ```powershell
   # 환경 변수 확인
   echo %TMDB_API_KEY%
   ```

3. **설정 파일 확인:**
   - `config/config.toml` 파일이 존재하는지 확인
   - 파일 권한 확인

### 일반적인 에러

**"Configuration file not found"**
- 해결: 실행 파일과 같은 위치에 `config` 폴더가 있는지 확인

**"TMDB API key not found"**
- 해결: 환경 변수 `TMDB_API_KEY` 설정 또는 `.env` 파일 생성

**"Permission denied"**
- 해결: 관리자 권한으로 실행하거나 다른 폴더로 이동

## 📝 사용 방법

### GUI 모드 (기본)

1. **폴더 선택:**
   - File > Open Folder로 애니메이션 파일이 있는 폴더 선택

2. **파일 스캔:**
   - 자동으로 스캔되거나 Scan 버튼 클릭

3. **TMDB 매칭:**
   - TMDB Match 버튼 클릭하여 메타데이터 검색

4. **파일 정리:**
   - Organize 버튼 클릭하여 파일 정리

### 테마 변경

- View > Theme에서 Light 또는 Dark 테마 선택

## 🔄 업데이트

새 버전이 나오면:
1. 기존 `AniVault.exe` 파일을 삭제
2. 새 버전의 `AniVault.exe`로 교체
3. `config/config.toml`은 그대로 유지 (설정이 보존됨)

## 📞 지원

문제가 발생하면:
- GitHub Issues에 보고
- 에러 메시지와 함께 로그 파일 첨부 (`logs/anivault.log`)

## ⚠️ 참고사항

- **현재 빌드는 디버그 버전입니다** (콘솔 창이 표시됨)
- 프로덕션 버전은 콘솔 창 없이 GUI만 표시됩니다
- 첫 실행은 의존성 초기화로 인해 느릴 수 있습니다
- Windows Defender가 처음 실행 시 검사할 수 있습니다 (정상)

## 📋 시스템 요구사항

- **OS:** Windows 10 이상 (64-bit)
- **RAM:** 최소 4GB (권장 8GB)
- **디스크:** 100MB 이상의 여유 공간
- **네트워크:** TMDB API 접근을 위한 인터넷 연결

## 🔐 보안

- API 키는 안전하게 보관하세요
- `.env` 파일은 공유하지 마세요
- 실행 파일은 공식 소스에서만 다운로드하세요
