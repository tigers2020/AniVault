# GUI 개발 및 품질 가이드

## 🎨 테마 시스템

### 테마 구조 (개발 환경)
```
src/anivault/resources/themes/
├── light.qss          # 라이트 테마
├── dark.qss           # 다크 테마
└── common.qss         # 공통 레이아웃 스타일
```

### 테마 구조 (PyInstaller 번들)
```
# 번들 내 읽기 전용 테마 (기본값)
<bundle>/resources/themes/
├── light.qss
├── dark.qss
└── common.qss

# 사용자 테마 디렉터리 (우선순위)
~/.anivault/themes/
├── light.qss          # 사용자 커스터마이징
├── dark.qss
└── common.qss
```

**폴백 우선순위**: 사용자 테마 → 번들 테마 → 기본 테마 (light) → 빈 스타일시트

### QSS @import 지원
Qt QSS는 기본적으로 `@import`를 지원하지 않지만, ThemeManager가 자체 파싱으로 해결합니다.

```css
/* light.qss */
@import url("common.qss");  /* 공통 레이아웃 import */

QMainWindow {
    background-color: #ffffff;
    color: #000000;
}

/* dark.qss */
@import url("common.qss");  /* 동일한 레이아웃 재사용 */

QMainWindow {
    background-color: #1e1e1e;
    color: #ffffff;
}

/* common.qss - 레이아웃만 정의 */
QFrame {
    border: none;
    border-radius: 6px;
}
```

**주의사항**:
- CSS Variables (`--var-name`)는 Qt QSS에서 지원되지 않음
- 대신 직접 색상 값 사용: `#007acc`, `rgba(0, 122, 204, 0.8)`
- Import depth 제한: 최대 10 레벨 (보안 및 성능)
- 순환 import 자동 탐지 및 방지

### 테마 적용 및 동기화
```python
from anivault.gui.themes import ThemeManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # ThemeManager 초기화 (자동으로 번들/개발 환경 감지)
        self.theme_manager = ThemeManager()

        # 테마 적용 (3-level fallback + 캐싱)
        self.theme_manager.apply_theme("dark")

    def switch_theme(self, theme_name: str):
        """사용자 테마 전환"""
        self.theme_manager.apply_theme(theme_name)
```

**ThemeManager 핵심 기능**:
- **자동 환경 감지**: PyInstaller 번들 vs 개발 환경
- **3-level 폴백**: 요청 테마 → 기본 테마 → 빈 스타일시트
- **@import 해석**: 재귀적 파일 로딩, 순환 탐지, 경로 검증
- **mtime 기반 캐싱**: 파일 변경 시 자동 무효화
- **성능 모니터링**: 50ms 초과 시 경고 로그
- **보안 로깅**: 절대 경로 마스킹 (`~/.anivault/...`)

## 🖼️ 스냅샷 테스트

### E2E 스냅샷 테스트 설정
```python
import pytest
from PySide6.QtWidgets import QApplication
from anivault.gui.main_window import MainWindow

@pytest.fixture
def app():
    """QApplication 픽스처"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    app.quit()

@pytest.fixture
def main_window(app):
    """메인 윈도우 픽스처"""
    window = MainWindow()
    window.show()
    yield window
    window.close()

def test_light_theme_snapshot(main_window):
    """라이트 테마 스냅샷 테스트"""
    # 라이트 테마 적용
    main_window.theme_manager.apply_theme("light")

    # 스크린샷 캡처
    screenshot = main_window.grab()

    # 기준 이미지와 비교
    expected_image = QPixmap("tests/snapshots/light_theme.png")
    assert screenshot == expected_image

def test_dark_theme_snapshot(main_window):
    """다크 테마 스냅샷 테스트"""
    # 다크 테마 적용
    main_window.theme_manager.apply_theme("dark")

    # 스크린샷 캡처
    screenshot = main_window.grab()

    # 기준 이미지와 비교
    expected_image = QPixmap("tests/snapshots/dark_theme.png")
    assert screenshot == expected_image
```

### 스냅샷 업데이트
```bash
# 스냅샷 업데이트 (새 기준 이미지 생성)
pytest tests/gui/test_theme_snapshots.py --update-snapshots

# 스냅샷 비교 (픽셀 단위)
pytest tests/gui/test_theme_snapshots.py --snapshot-diff
```

## 🎯 접근성 (Accessibility)

### 접근성 가이드라인
```python
class AccessibleWidget(QWidget):
    """접근성을 고려한 위젯"""

    def __init__(self):
        super().__init__()
        self.setup_accessibility()

    def setup_accessibility(self):
        """접근성 설정"""
        # 1. 역할 설정
        self.setAccessibleName("애니메이션 파일 목록")
        self.setAccessibleDescription("스캔된 애니메이션 파일들을 표시합니다")

        # 2. 키보드 네비게이션
        self.setFocusPolicy(Qt.StrongFocus)

        # 3. 색상 대비 확인
        self.ensure_color_contrast()

    def ensure_color_contrast(self):
        """색상 대비 확인 (WCAG 2.1 AA 기준)"""
        # 최소 대비비: 4.5:1 (일반 텍스트), 3:1 (큰 텍스트)
        pass
```

### 색상 대비 검증
```python
def test_color_contrast_compliance():
    """색상 대비 WCAG 2.1 AA 준수 테스트"""
    # 라이트 테마 대비 검증
    light_contrast = calculate_contrast_ratio("#000000", "#ffffff")  # 21:1
    assert light_contrast >= 4.5

    # 다크 테마 대비 검증
    dark_contrast = calculate_contrast_ratio("#ffffff", "#1e1e1e")  # 12.6:1
    assert dark_contrast >= 4.5

def calculate_contrast_ratio(color1: str, color2: str) -> float:
    """색상 대비비 계산"""
    # WCAG 2.1 공식 적용
    pass
```

## 🔄 테마 전환 애니메이션

### 부드러운 테마 전환
```python
class AnimatedThemeTransition:
    """테마 전환 애니메이션"""

    def __init__(self, widget: QWidget):
        self.widget = widget
        self.animation = QPropertyAnimation(widget, b"styleSheet")
        self.animation.setDuration(300)  # 300ms 전환
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)

    def transition_to_theme(self, new_theme: str):
        """새 테마로 부드럽게 전환"""
        current_style = self.widget.styleSheet()
        new_style = self.load_theme_style(new_theme)

        self.animation.setStartValue(current_style)
        self.animation.setEndValue(new_style)
        self.animation.start()
```

## 🎨 커스텀 테마 지원

### 사용자 정의 테마
```python
class CustomThemeManager(ThemeManager):
    """사용자 정의 테마 지원"""

    def create_custom_theme(self, name: str, base_theme: str, customizations: dict):
        """사용자 정의 테마 생성"""
        # 기본 테마 로드
        base_content = self.load_theme_content(base_theme)

        # 사용자 정의 적용
        for selector, properties in customizations.items():
            base_content = self.apply_customization(base_content, selector, properties)

        # 새 테마 파일 저장
        custom_path = self.themes_dir / f"{name}.qss"
        with open(custom_path, 'w', encoding='utf-8') as f:
            f.write(base_content)

        return custom_path
```

## 🧪 GUI 테스트 전략

### 위젯 테스트
```python
def test_widget_creation():
    """위젯 생성 테스트"""
    widget = GroupCardWidget()
    assert widget is not None
    assert widget.isVisible() == False  # 아직 표시되지 않음

def test_widget_visibility():
    """위젯 가시성 테스트"""
    widget = GroupCardWidget()
    widget.show()
    assert widget.isVisible() == True

def test_widget_interaction():
    """위젯 상호작용 테스트"""
    widget = GroupCardWidget()

    # 클릭 이벤트 시뮬레이션
    QTest.mouseClick(widget, Qt.LeftButton)

    # 신호 확인
    assert widget.clicked.emit.called
```

### 테마 통합 테스트
```python
def test_theme_consistency():
    """테마 일관성 테스트"""
    app = QApplication.instance()
    theme_manager = ThemeManager()

    # 모든 테마 테스트
    for theme_name in theme_manager.get_available_themes():
        # 테마 적용
        theme_manager.apply_theme(theme_name)

        # 모든 위젯이 올바르게 스타일링되었는지 확인
        for widget in app.allWidgets():
            assert widget.styleSheet() != ""  # 스타일이 적용되었는지 확인
```

## 📱 반응형 디자인

### 화면 크기별 레이아웃
```python
class ResponsiveLayout(QVBoxLayout):
    """반응형 레이아웃"""

    def __init__(self):
        super().__init__()
        self.setup_responsive_behavior()

    def setup_responsive_behavior(self):
        """반응형 동작 설정"""
        # 화면 크기 변경 감지
        self.screen_size_changed.connect(self.adjust_layout)

    def adjust_layout(self, screen_size: QSize):
        """화면 크기에 따른 레이아웃 조정"""
        if screen_size.width() < 768:  # 모바일
            self.set_compact_mode()
        elif screen_size.width() < 1200:  # 태블릿
            self.set_medium_mode()
        else:  # 데스크톱
            self.set_desktop_mode()
```

## 🔧 성능 최적화

### 렌더링 최적화
```python
class OptimizedWidget(QWidget):
    """렌더링 최적화된 위젯"""

    def __init__(self):
        super().__init__()
        self.setup_optimization()

    def setup_optimization(self):
        """최적화 설정"""
        # 1. 더블 버퍼링 활성화
        self.setAttribute(Qt.WA_OpaquePaintEvent)

        # 2. 업데이트 최적화
        self.setAttribute(Qt.WA_StaticContents)

        # 3. 불필요한 리페인트 방지
        self.setAttribute(Qt.WA_NoSystemBackground)

    def paintEvent(self, event):
        """커스텀 페인트 이벤트"""
        # 필요한 영역만 다시 그리기
        if event.rect().intersects(self.dirty_region):
            super().paintEvent(event)
```

## 📊 GUI 메트릭스

### 성능 모니터링
```python
class GUIPerformanceMonitor:
    """GUI 성능 모니터링"""

    def __init__(self):
        self.frame_times = []
        self.render_times = []

    def measure_frame_time(self, widget: QWidget):
        """프레임 시간 측정"""
        start_time = time.perf_counter()
        widget.update()
        end_time = time.perf_counter()

        frame_time = end_time - start_time
        self.frame_times.append(frame_time)

        # 60fps 기준 (16.67ms)
        if frame_time > 0.01667:
            logger.warning(f"Slow frame: {frame_time:.3f}s")

    def get_average_frame_time(self) -> float:
        """평균 프레임 시간 반환"""
        return sum(self.frame_times) / len(self.frame_times) if self.frame_times else 0
```

## 🚨 디버깅 도구

### GUI 디버거
```python
class GUIDebugger:
    """GUI 디버깅 도구"""

    def __init__(self, app: QApplication):
        self.app = app
        self.setup_debug_shortcuts()

    def setup_debug_shortcuts(self):
        """디버그 단축키 설정"""
        # F1: 위젯 정보 표시
        # F2: 테마 전환
        # F3: 스타일 정보 표시
        # F4: 성능 정보 표시
        pass

    def show_widget_info(self, widget: QWidget):
        """위젯 정보 표시"""
        info = {
            "class": widget.__class__.__name__,
            "size": widget.size(),
            "position": widget.pos(),
            "style": widget.styleSheet(),
            "theme": widget.property("theme")
        }
        print(json.dumps(info, indent=2))
```

## 📝 GUI 개발 체크리스트

### 위젯 개발 시
- [ ] 접근성 속성 설정 (accessibleName, accessibleDescription)
- [ ] 키보드 네비게이션 지원
- [ ] 테마 토큰 사용 (하드코딩된 색상 금지)
- [ ] 반응형 레이아웃 적용
- [ ] 단위 테스트 작성
- [ ] 스냅샷 테스트 추가

### 테마 개발 시
- [ ] WCAG 2.1 AA 색상 대비 준수
- [ ] 모든 위젯 상태 스타일링 (hover, focus, disabled)
- [ ] 다국어 텍스트 길이 고려
- [ ] 고대비 모드 지원
- [ ] 테마 전환 애니메이션 테스트

### 성능 최적화 시
- [ ] 불필요한 리페인트 방지
- [ ] 메모리 사용량 모니터링
- [ ] 프레임 레이트 측정
- [ ] 렌더링 병목 지점 식별
- [ ] 비동기 작업 적용

## 🆘 문제 해결

### 일반적인 GUI 문제
1. **테마가 적용되지 않음**: 위젯 리폴리시 확인
2. **색상이 보이지 않음**: 색상 대비 확인
3. **레이아웃 깨짐**: 반응형 설정 확인
4. **성능 저하**: 렌더링 최적화 확인
5. **접근성 문제**: ARIA 속성 확인

### 디버깅 명령어
```bash
# GUI 테스트 실행
pytest tests/gui/ -v

# 스냅샷 테스트 실행
pytest tests/gui/test_snapshots.py -v

# 테마 테스트 실행
pytest tests/gui/test_themes.py -v

# 성능 테스트 실행
pytest tests/gui/test_performance.py -v
```
