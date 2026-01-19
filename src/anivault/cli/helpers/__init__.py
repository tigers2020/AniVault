"""CLI helper modules.

This package contains helper functions extracted from CLI handlers
for better code organization and reusability.
"""

from __future__ import annotations

# Re-export log helpers
from .log import (
    collect_log_list_data,
    print_log_list,
)

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

# Re-export scan helpers
from .scan import (
    collect_scan_data,
    display_scan_results,
    enrich_metadata,
    run_scan_pipeline,
)

# Re-export verify helpers
from .verify import (
    collect_verify_data,
    print_tmdb_verification_result,
    verify_tmdb_connectivity,
)

__all__ = [
    # Match helpers
    "collect_match_data",
    # Organize helpers
    "collect_organize_data",
    # Scan helpers
    "collect_scan_data",
    "confirm_organization",
    "display_match_results",
    "display_scan_results",
    "enrich_metadata",
    "execute_organization_plan",
    "generate_enhanced_organization_plan",
    "generate_organization_plan",
    "get_scanned_files",
    "perform_organization",
    "print_dry_run_plan",
    "print_execution_plan",
    "process_file_for_matching",
    "run_match_pipeline",
    "run_scan_pipeline",
    "verify_tmdb_connectivity",
]
