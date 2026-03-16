"""Application DTOs for presentation layer contract.

Presentation consumes DTOs from this namespace only.
Domain entities are never passed to presentation.
"""

from anivault.application.dtos.match import ManualSearchResultDTO
from anivault.application.dtos.organize import OrganizePlanItem, OrganizeResultItem, OrganizeScanInput

__all__ = [
    "ManualSearchResultDTO",
    "OrganizePlanItem",
    "OrganizeResultItem",
    "OrganizeScanInput",
]
