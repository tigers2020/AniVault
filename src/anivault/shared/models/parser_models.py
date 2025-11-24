"""애니메이션 파일명 파싱을 위한 데이터 모델.

이 모듈은 파싱 시스템 전반에서 사용되는 핵심 데이터 구조를 정의합니다.
모든 파서는 일관성을 위해 ParsingResult 형식으로 결과를 반환해야 합니다.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ParsingResult(BaseModel):
    """애니메이션 파일명 파싱의 결과.

    이 dataclass는 시스템의 모든 파서에 대한 표준화된 출력 형식을 나타냅니다.
    anitopy, regex 또는 다른 방법을 사용하는지 여부에 관계없이.

    Attributes:
        title: 파일명에서 추출된 애니메이션 제목.
        episode: 에피소드 번호 (찾을 수 없거나 적용되지 않는 경우 None).
        season: 시즌 번호 (찾을 수 없거나 단일 시즌인 경우 None).
        year: 출시 연도 (찾을 수 없으면 None).
        quality: 비디오 품질 표시자 (예: "1080p", "720p").
        source: 릴리스 소스 (예: "BluRay", "WEB", "HDTV").
        codec: 비디오 코덱 (예: "H.264", "HEVC", "x265").
        audio: 오디오 코덱 또는 채널 정보 (예: "AAC", "FLAC", "5.1").
        release_group: 릴리스 그룹의 이름.
        confidence: 파싱 신뢰도 점수 (0.0 to 1.0).
        parser_used: 이 결과를 생성한 파서의 이름.
        other_info: 추가로 추출된 메타데이터를 위한 딕셔너리.
    """

    title: str
    episode: int | None = None
    season: int | None = None
    year: int | None = None
    quality: str | None = None
    source: str | None = None
    codec: str | None = None
    audio: str | None = None
    release_group: str | None = None
    confidence: float = 0.0
    parser_used: str = "unknown"
    other_info: dict[str, str | int | float | bool] = Field(default_factory=dict, description="추가 정보")

    def model_post_init(self, __context: Any, /) -> None:
        """초기화 후 파싱 결과를 검증.

        Returns:
            None

        Raises:
            ValueError: 신뢰도가 유효한 범위 [0.0, 1.0]에 없는 경우.
        """
        if not 0.0 <= self.confidence <= 1.0:
            msg = f"Confidence must be between 0.0 and 1.0, got {self.confidence}"
            raise ValueError(
                msg,
            )

    def is_valid(self) -> bool:
        """파싱 결과에 필수 정보가 포함되어 있는지 확인.

        유효한 결과는 최소한 제목을 가져야 합니다. 에피소드나 시즌과 같은
        추가 필드는 선택사항이지만 신뢰도를 높입니다.

        Returns:
            결과에 제목이 있으면 True, 그렇지 않으면 False.
        """
        return bool(self.title and self.title.strip())

    def has_episode_info(self) -> bool:
        """결과에 에피소드 정보가 포함되어 있는지 확인.

        Returns:
            에피소드 번호가 있으면 True, 그렇지 않으면 False.
        """
        return self.episode is not None

    def has_season_info(self) -> bool:
        """결과에 시즌 정보가 포함되어 있는지 확인.

        Returns:
            시즌 번호가 있으면 True, 그렇지 않으면 False.
        """
        return self.season is not None


__all__ = ["ParsingResult"]
