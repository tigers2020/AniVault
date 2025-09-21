# AniVault 코드 스타일 및 컨벤션

## 코딩 스타일
- **포매터**: Black (line-length: 100, skip-string-normalization: false)
- **타입 힌트**: 필수 (Python 3.10+ 문법 사용)
- **Docstring**: Google 스타일 (PEP257 준수)

## 네이밍 컨벤션
- **클래스**: PascalCase (예: `AnimeFile`, `FileGroup`)
- **함수/변수**: snake_case (예: `file_path`, `get_metadata`)
- **상수**: UPPER_SNAKE_CASE (예: `MAX_FILE_SIZE`)
- **프라이빗 멤버**: `_` 접두사 (예: `_private_method`)

## 금지된 용어
- **"unified"** 사용 금지: 메서드명, 변수명, 주석에서 사용하지 않음
- 예시:
  - ❌ `search_unified()`, `unified_strategies`
  - ✅ `search()`, `search_strategies`

## 아키텍처 패턴
- **MVVM 패턴**: ViewModel을 통한 데이터 바인딩
- **의존성 주입**: ConfigManager, ThemeManager 등
- **이벤트 기반**: PyQt5 시그널/슬롯 시스템

## 에러 처리
- **로깅**: 구조화된 로깅 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **예외**: 구체적인 예외 타입 사용
- **사용자 피드백**: QMessageBox를 통한 오류 알림

## 파일 구조
- **모듈별 분리**: 기능별로 명확한 모듈 분리
- **인터페이스**: 추상 클래스와 프로토콜 활용
- **설정 관리**: 중앙화된 설정 관리 시스템
