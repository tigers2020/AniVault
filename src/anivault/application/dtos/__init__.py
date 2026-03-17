"""Application DTOs for presentation layer contract.

Presentation consumes DTOs from this namespace only.
Domain entities are never passed to presentation.
"""

from anivault.application.dtos.match import (
    ManualSearchResultDTO,
    MatchResultItem,
    file_metadata_to_match_dto,
)
from anivault.application.dtos.organize import OrganizePlanItem, OrganizeResultItem, OrganizeScanInput
from anivault.application.dtos.scan import ScanResultItem, file_metadata_to_dto

__all__ = [
    "ManualSearchResultDTO",
    "MatchResultItem",
    "OrganizePlanItem",
    "OrganizeResultItem",
    "OrganizeScanInput",
    "ScanResultItem",
    "file_metadata_to_dto",
    "file_metadata_to_match_dto",
]
