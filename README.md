# AniVault

AniVault는 TMDB API를 활용한 애니메이션 파일 자동 정리 시스템입니다.

## 기능

- 애니메이션 파일 자동 인식 및 파싱
- TMDB API를 통한 메타데이터 수집
- 자동 파일 정리 및 이름 변경
- Windows 단일 실행파일(.exe) 지원

## 설치

```bash
pip install -e .
```

## 사용법

```bash
anivault --help
```

## 개발

프로젝트 초기화 후 개발을 시작하려면:

```bash
# Taskmaster 초기화 (이미 완료됨)
task-master init

# PRD 파싱하여 작업 생성
task-master parse-prd .taskmaster/docs/prd.txt

# 다음 작업 확인
task-master next
```

## 라이선스

MIT License

