# AniVault 프로젝트 개요

## 프로젝트 목적
AniVault는 PyQt5 기반의 데스크톱 애플리케이션으로, 애니메이션 컬렉션을 관리하고 정보를 제공하는 도구입니다.

## 주요 기능
- 애니메이션 파일 스캔 및 분류
- TMDB API를 통한 메타데이터 검색
- 파일 그룹화 및 자동 정리
- 사용자 친화적인 GUI 인터페이스
- 크로스 플랫폼 지원

## 기술 스택
- **언어**: Python 3.10+
- **GUI 프레임워크**: PyQt5
- **데이터베이스**: SQLAlchemy + Alembic (마이그레이션)
- **파일 파싱**: anitopy
- **메타데이터**: tmdbsimple (TMDB API)
- **아키텍처**: MVVM 패턴

## 프로젝트 구조
```
src/
├── app.py              # 메인 애플리케이션 클래스
├── main.py             # 애플리케이션 진입점
├── core/               # 핵심 비즈니스 로직
│   ├── models.py       # 데이터 모델 (AnimeFile, FileGroup)
│   ├── database.py     # 데이터베이스 관리
│   ├── tmdb_client.py  # TMDB API 클라이언트
│   ├── file_scanner.py # 파일 스캔 로직
│   ├── file_grouper.py # 파일 그룹화 로직
│   └── ...
├── gui/                # 사용자 인터페이스
│   ├── main_window.py  # 메인 윈도우
│   ├── work_panel.py   # 작업 패널
│   ├── result_panel.py # 결과 표시 패널
│   └── ...
├── viewmodels/         # MVVM 뷰모델
└── themes/             # 테마 관리
```

## 핵심 데이터 모델
- **AnimeFile**: 개별 애니메이션 파일 정보
- **FileGroup**: 유사한 파일들을 그룹화한 컬렉션
- **ParsedAnimeInfo**: 파일명에서 파싱된 애니메이션 정보
- **TMDBAnime**: TMDB API에서 가져온 메타데이터