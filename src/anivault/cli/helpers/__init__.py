"""CLI helper modules.

This package contains helper functions extracted from CLI handlers
for better code organization and reusability.
"""

from __future__ import annotations

# Re-export match helpers
from .match import (
    collect_match_data,
    display_match_results,
    process_file_for_matching,
    run_match_pipeline,
)

# Re-export organize helpers
from .organize import (
    collect_organize_data,
    confirm_organization,
    execute_organization_plan,
    generate_enhanced_organization_plan,
    generate_organization_plan,
    get_scanned_files,
    perform_organization,
    print_dry_run_plan,
    print_execution_plan,
)

__all__ = [
    # Match helpers
    "collect_match_data",
    # Organize helpers
    "collect_organize_data",
    "confirm_organization",
    "display_match_results",
    "execute_organization_plan",
    "generate_enhanced_organization_plan",
    "generate_organization_plan",
    "get_scanned_files",
    "perform_organization",
    "print_dry_run_plan",
    "print_execution_plan",
    "process_file_for_matching",
    "run_match_pipeline",
]
