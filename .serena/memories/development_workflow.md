# AniVault 개발 워크플로우

## 코드 품질 도구
- **포매터**: Black (line-length: 100)
- **린터**: Ruff (E, W, F, I, N, UP, B, ANN, D, PT, RUF 규칙)
- **타입 체킹**: PyRight, MyPy
- **테스팅**: pytest + pytest-qt + pytest-cov

## 개발 명령어
```bash
# 코드 포매팅
black .

# 린팅 및 자동 수정
ruff check . --fix

# 타입 체킹
pyright .

# 테스트 실행
pytest

# 커버리지 포함 테스트
pytest --cov=src --cov-report=html
```

## 프로젝트 실행
```bash
# 메인 애플리케이션 실행
python main.py

# 또는 src 디렉토리에서
python -m src.main
```

## 데이터베이스 관리
```bash
# 마이그레이션 실행
alembic upgrade head

# 새 마이그레이션 생성
alembic revision --autogenerate -m "description"
```

## 의존성 관리
- **프로덕션**: requirements.txt
- **개발**: requirements-dev.txt
- **패키지 설정**: pyproject.toml
