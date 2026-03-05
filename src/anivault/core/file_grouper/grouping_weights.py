"""Default grouping weights from config."""

from __future__ import annotations

from anivault.config import load_settings
from anivault.config.models.matching_weights import MatchingWeights


def get_default_weights_from_config() -> dict[str, float]:
    """Get default matcher weights from MatchingWeights configuration.

    Returns:
        Dictionary mapping matcher component_name to weight.
    """
    try:
        settings = load_settings()
        weights = settings.matching_weights
        return {
            "title": weights.grouping_title_weight,
            "hash": weights.grouping_hash_weight,
            "season": weights.grouping_season_weight,
        }
    except (ImportError, AttributeError):
        default_weights = MatchingWeights()
        return {
            "title": default_weights.grouping_title_weight,
            "hash": default_weights.grouping_hash_weight,
            "season": default_weights.grouping_season_weight,
        }
