# AniVault 프로젝트 가이드라인

## 코딩 스타일
- Python 3.9+ 사용
- Black 포맷터 (line-length: 88)
- Ruff 린터 사용
- 타입 힌트 필수 (mypy strict mode)
- Google/NumPy 스타일 docstring

## 프로젝트 구조
- `src/anivault/` 메인 패키지
- `src/anivault/core/` 핵심 컴포넌트
- `src/anivault/services/` 서비스 레이어
- `src/anivault/cli/` CLI 인터페이스
- `tests/` 테스트 파일들

## 주요 의존성
- Pydantic (데이터 모델링)
- Rich (터미널 출력)
- Click/Typer (CLI)
- pytest (테스팅)

## 파일 조직화 기능
- 현재 FileOrganizer 클래스가 존재하지 않음
- W13-W14에서 organize, dry-run, rollback 기능 구현 예정
- Operation Logging을 위한 새로운 모델과 매니저 필요