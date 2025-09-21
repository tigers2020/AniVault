# AniVault 개발을 위한 권장 명령어

## 개발 환경 설정
```bash
# 가상환경 생성 및 활성화
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## 코드 품질 검사
```bash
# 포매팅
black .

# 린팅 (자동 수정 포함)
ruff check . --fix

# 타입 체킹
pyright .

# 모든 품질 검사 통과 확인
black . && ruff check . && pyright . && pytest
```

## 테스트 실행
```bash
# 기본 테스트
pytest

# 커버리지 포함
pytest --cov=src --cov-report=term-missing

# HTML 커버리지 리포트
pytest --cov=src --cov-report=html
```

## 데이터베이스 관리
```bash
# 마이그레이션 실행
alembic upgrade head

# 새 마이그레이션 생성
alembic revision --autogenerate -m "description"

# 데이터베이스 초기화
python check_db.py
```

## 애플리케이션 실행
```bash
# 메인 애플리케이션
python main.py

# 또는 src 모듈로
python -m src.main
```

## Git 워크플로우
```bash
# 변경사항 확인
git status
git diff

# 커밋 (Conventional Commits)
git add .
git commit -m "feat: add new feature"
git commit -m "fix: resolve bug in file processing"
git commit -m "docs: update README"

# 푸시
git push origin main
```

## 디버깅
```bash
# 로그 확인
tail -f logs/anivault.log

# 데이터베이스 상태 확인
python check_db.py

# 설정 파일 검증
python -c "from src.core.config_manager import get_config_manager; print(get_config_manager().get_all_config())"
```
