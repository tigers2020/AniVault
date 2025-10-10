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

# Re-export rollback helpers
from .rollback import (
    confirm_rollback,
    execute_rollback_plan,
    generate_rollback_plan,
    load_rollback_log,
    print_rollback_dry_run_plan,
    print_rollback_execution_plan,
    print_skipped_operations,
    validate_rollback_plan,
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
    # Rollback helpers
    "confirm_rollback",
    "display_match_results",
    "display_scan_results",
    "enrich_metadata",
    "execute_organization_plan",
    "execute_rollback_plan",
    "generate_enhanced_organization_plan",
    "generate_organization_plan",
    "generate_rollback_plan",
    "get_scanned_files",
    "load_rollback_log",
    "perform_organization",
    "print_dry_run_plan",
    "print_execution_plan",
    "print_rollback_dry_run_plan",
    "print_rollback_execution_plan",
    "print_skipped_operations",
    "process_file_for_matching",
    "run_match_pipeline",
    "run_scan_pipeline",
    "validate_rollback_plan",
    "verify_tmdb_connectivity",
]
