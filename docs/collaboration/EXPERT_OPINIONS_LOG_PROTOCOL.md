# 전문가 의견 로그 규약 (Chat 출력용)

## 개요

NovelSorter 프로젝트의 Tree-of-Thought (ToT) 라운드에서 각 전문가의 의견을 체계적으로 기록하고 의사결정 과정을 추적하기 위한 표준화된 로그 형식입니다.

## 전문가 의견 로그 템플릿

### 마크다운 템플릿

```markdown
### ToT Round {N} — Complexity: {L|M|H}
**Steward**: {Steward Role} ({Steward Name})
**Question**: {핵심 질문 또는 결정 사항}

- **{전문가 역할}**: {주장 및 제안}. _evidence: {코드경로/테스트ID/문서링크}_
- **{전문가 역할}**: {주장 및 제안}. _evidence: {코드경로/테스트ID/문서링크}_
- **{전문가 역할}**: {주장 및 제안}. _evidence: {코드경로/테스트ID/문서링크}_

**Conflicts**: {충돌하는 의견이나 기술적 갈등}
**Decision (by Steward)**: {최종 결정}. _rejected: {거부된 대안}_. **Rationale**: {결정 근거}
**Next**: {proceed|blocked|needs_research}
```

### JSON 요약 스키마

```json
{
  "round": 1,
  "complexity": "M",
  "steward": {
    "role": "Technical PM",
    "name": "한서연"
  },
  "question": "문자열 요약",
  "experts": [
    {
      "role": "PySide6 엔지니어",
      "name": "장도윤",
      "opinion": "주장 요약",
      "evidence": ["src/gui/reader_tab.py", "tests/test_ui_consistency.py"]
    }
  ],
  "conflicts": ["기술적 갈등 설명"],
  "decision": {
    "selected": "선택된 방안",
    "rejected": ["거부된 대안들"],
    "rationale": "결정 근거"
  },
  "next_action": "proceed"
}
```

## 출력 규칙

### 필수 요구사항
1. **근거 최소 1개**: 모든 전문가 의견에는 반드시 증거(_evidence_) 포함
2. **반례 우선**: 충돌하는 의견이나 예외 상황을 명시적으로 기록
3. **비밀 마스킹**: 민감한 정보는 `***` 또는 `[REDACTED]` 처리

### 증거 표준화
- **코드 경로**: `src/reader/epub_viewer.py:45-67`
- **테스트 ID**: `tests/test_encoding_detection.py::test_mojibake_repair`
- **문서 링크**: `doc/developer/06-yoon-gaon-document-rendering-engineer.md`
- **아키텍처 참조**: `ARCHITECTURE_READER_MODE.md#pdf-처리`

## NovelSorter 프로젝트 적용 예시

### ToT Round 1 — Complexity: M
**Steward**: Technical PM (한서연)
**Question**: EPUB 렌더링 전략 결정 - EbookLib vs 직접 파싱

- **Document Rendering Engineer**: EbookLib 사용 권장. 표준 라이브러리로 EPUB2/3 완전 지원. _evidence: doc/developer/06-yoon-gaon-document-rendering-engineer.md_
- **Performance Tuner**: 직접 파싱이 성능상 유리할 수 있음. _evidence: ARCHITECTURE_READER_MODE.md#성능-고려사항_
- **QA Engineer**: EbookLib 사용 시 테스트 커버리지 확보 용이. _evidence: tests/test_epub_parsing.py_

**Conflicts**: 성능 vs 표준화, 테스트 용이성
**Decision (by Steward)**: EbookLib 채택. _rejected: 직접 파싱_. **Rationale**: 표준화 우선, 유지보수성 확보
**Next**: proceed

### ToT Round 2 — Complexity: H
**Steward**: Technical PM (한서연)
**Question**: TTS 시스템 아키텍처 - pyttsx3 기본 vs Coqui TTS 통합

- **Offline TTS Engineer**: pyttsx3 기본, Coqui TTS 옵션으로 단계적 접근. _evidence: doc/developer/07-shin-taekyung-offline-tts-engineer.md_
- **Build Engineer**: Coqui TTS 모델 크기 고려 필요. _evidence: PyInstaller 번들 크기 제한_
- **Performance Tuner**: GPU 메모리 사용량 모니터링 필요. _evidence: ARCHITECTURE_READER_MODE.md#메모리-관리_
- **QA Engineer**: 두 엔진 모두 테스트 필요. _evidence: tests/test_tts_integration.py_

**Conflicts**: 기능성 vs 번들 크기, GPU 리소스 관리
**Decision (by Steward)**: 하이브리드 접근 - pyttsx3 기본, Coqui TTS 선택적. _rejected: Coqui TTS만 사용_. **Rationale**: 사용자 선택권 보장, 점진적 확장
**Next**: proceed

### ToT Round 3 — Complexity: L
**Steward**: Technical PM (한서연)
**Question**: CLI 명령어 구조 - Typer vs Click

- **CLI Tooling Engineer**: Typer 사용 권장. 타입 힌트 기반, 현대적 API. _evidence: doc/developer/03-lee-soheun-cli-tooling-engineer.md_
- **Build Engineer**: Typer 번들링 호환성 확인됨. _evidence: PyInstaller spec 테스트 완료_

**Conflicts**: 없음
**Decision (by Steward)**: Typer 채택. **Rationale**: 타입 안전성과 현대적 API
**Next**: proceed

## 자동화 파이프라인

### Jinja 템플릿

```jinja
### ToT Round {{ round_number }} — Complexity: {{ complexity }}
**Steward**: {{ steward.role }} ({{ steward.name }})
**Question**: {{ question }}

{% for expert in experts %}
- **{{ expert.role }}**: {{ expert.opinion }}. _evidence: {{ expert.evidence | join(', ') }}_
{% endfor %}

{% if conflicts %}
**Conflicts**: {{ conflicts | join(', ') }}
{% endif %}
**Decision (by Steward)**: {{ decision.selected }}. {% if decision.rejected %}_rejected: {{ decision.rejected | join(', ') }}_. {% endif %}**Rationale**: {{ decision.rationale }}
**Next**: {{ next_action }}
```

### 최소 파이프라인 코드

```python
from dataclasses import dataclass
from typing import List, Optional
import json
from jinja2 import Template

@dataclass
class ExpertOpinion:
    role: str
    name: str
    opinion: str
    evidence: List[str]

@dataclass
class Decision:
    selected: str
    rejected: Optional[List[str]] = None
    rationale: str = ""

@dataclass
class ToTRound:
    round_number: int
    complexity: str  # L|M|H
    steward: dict
    question: str
    experts: List[ExpertOpinion]
    conflicts: Optional[List[str]] = None
    decision: Optional[Decision] = None
    next_action: str = "proceed"

def generate_expert_log(round_data: ToTRound, template: str) -> str:
    """전문가 의견 로그를 마크다운으로 생성."""
    jinja_template = Template(template)
    return jinja_template.render(
        round_number=round_data.round_number,
        complexity=round_data.complexity,
        steward=round_data.steward,
        question=round_data.question,
        experts=round_data.experts,
        conflicts=round_data.conflicts or [],
        decision=round_data.decision or Decision(selected="", rationale=""),
        next_action=round_data.next_action
    )

def export_json_summary(round_data: ToTRound) -> dict:
    """JSON 요약 데이터 생성."""
    return {
        "round": round_data.round_number,
        "complexity": round_data.complexity,
        "steward": round_data.steward,
        "question": round_data.question,
        "experts": [
            {
                "role": expert.role,
                "name": expert.name,
                "opinion": expert.opinion,
                "evidence": expert.evidence
            }
            for expert in round_data.experts
        ],
        "conflicts": round_data.conflicts or [],
        "decision": {
            "selected": round_data.decision.selected if round_data.decision else "",
            "rejected": round_data.decision.rejected if round_data.decision else [],
            "rationale": round_data.decision.rationale if round_data.decision else ""
        },
        "next_action": round_data.next_action
    }

# 사용 예시
def example_usage():
    round_data = ToTRound(
        round_number=1,
        complexity="M",
        steward={"role": "Technical PM", "name": "한서연"},
        question="EPUB 렌더링 전략 결정",
        experts=[
            ExpertOpinion(
                role="Document Rendering Engineer",
                name="윤가온",
                opinion="EbookLib 사용 권장",
                evidence=["doc/developer/06-yoon-gaon-document-rendering-engineer.md"]
            )
        ],
        conflicts=["성능 vs 표준화"],
        decision=Decision(
            selected="EbookLib 채택",
            rejected=["직접 파싱"],
            rationale="표준화 우선, 유지보수성 확보"
        ),
        next_action="proceed"
    )
    
    template = """### ToT Round {{ round_number }} — Complexity: {{ complexity }}
**Steward**: {{ steward.role }} ({{ steward.name }})
**Question**: {{ question }}
{% for expert in experts %}
- **{{ expert.role }}**: {{ expert.opinion }}. _evidence: {{ expert.evidence | join(', ') }}_
{% endfor %}
{% if conflicts %}
**Conflicts**: {{ conflicts | join(', ') }}
{% endif %}
**Decision (by Steward)**: {{ decision.selected }}. {% if decision.rejected %}_rejected: {{ decision.rejected | join(', ') }}_. {% endif %}**Rationale**: {{ decision.rationale }}
**Next**: {{ next_action }}"""
    
    markdown_output = generate_expert_log(round_data, template)
    json_output = export_json_summary(round_data)
    
    return markdown_output, json_output
```

## 전문가 역할 매핑

### NovelSorter 팀 전문가 역할

| 역할 | 담당자 | 주요 관심사 |
|------|--------|-------------|
| **Technical PM** | 한서연 | 아키텍처, 요구사항, 품질 게이트 |
| **UI/UX Engineer** | 장도윤 | GUI 설계, 사용자 경험 |
| **CLI Engineer** | 이소흔 | 명령줄 인터페이스, 개발자 도구 |
| **Text IR Engineer** | 민지환 | 텍스트 처리, 중복 탐지 |
| **Encoding Specialist** | 고하림 | 인코딩, 국제화 |
| **Document Rendering Engineer** | 윤가온 | EPUB/PDF/TXT 렌더링 |
| **TTS Engineer** | 신태경 | 음성 합성, 오디오 처리 |
| **Build Engineer** | 백지원 | 빌드, 패키징, 배포 |
| **QA Engineer** | 유다인 | 테스트, 품질 보증 |
| **Performance Tuner** | 정라온 | 성능 최적화, 메모리 관리 |

## 복잡도 기준

### L (Low) - 단순한 결정
- 명확한 기술 선택
- 충돌 없는 의견
- 즉시 진행 가능

### M (Medium) - 중간 복잡도
- 여러 기술적 옵션
- 일부 충돌 존재
- 추가 검토 필요

### H (High) - 높은 복잡도
- 복잡한 아키텍처 결정
- 여러 전문가 간 충돌
- 상당한 연구/검증 필요

## 활용 방법

### 1. 라운드 진행 시
- 각 전문가의 의견을 체계적으로 수집
- 증거와 근거를 명확히 기록
- 충돌 지점을 명시적으로 식별

### 2. 의사결정 시
- Steward가 최종 결정
- 거부된 대안과 근거 명시
- 다음 단계 명확히 정의

### 3. 추적 및 검토
- JSON 요약으로 자동화 처리
- 마크다운 로그로 사람이 읽기 쉬운 기록
- 의사결정 과정의 투명성 확보

---

*이 규약은 NovelSorter 프로젝트의 의사결정 과정을 체계화하고 추적 가능하게 만듭니다. 각 ToT 라운드에서 전문가들의 의견을 명확히 기록하고, 최종 결정의 근거를 보존하여 프로젝트의 품질과 일관성을 보장합니다.*
