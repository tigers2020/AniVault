"""CLI helper modules.

Formatter/util only — no orchestration, no UseCase, no services.
Handler files (scan_handler, match_handler, organize_handler) own all orchestration.
"""

from __future__ import annotations

# Re-export log helpers
from .log import (
    collect_log_list_data,
    print_log_list,
)

# Re-export match helpers (output wrapper + formatters)
from .match import (
    collect_match_data,
    display_match_results,
    output_match_results,
)

# Re-export organize helpers (formatter/util only)
from .organize import (
    collect_organize_data,
    confirm_organization,
    print_dry_run_plan,
    print_execution_plan,
    print_organization_results,
)

# Re-export scan helpers (formatter/util only)
from .scan import (
    collect_scan_data,
    display_scan_results,
    file_metadata_to_dict,
)

# Re-export verify helpers
from .verify import (
    format_verify_result_for_json,
    print_all_components_result,
    print_tmdb_verification_result,
)

__all__ = [
    # Log helpers
    "collect_log_list_data",
    "print_log_list",
    # Match helpers
    "collect_match_data",
    "display_match_results",
    "output_match_results",
    # Organize helpers
    "collect_organize_data",
    "confirm_organization",
    "print_dry_run_plan",
    "print_execution_plan",
    "print_organization_results",
    # Scan helpers
    "collect_scan_data",
    "display_scan_results",
    "file_metadata_to_dict",
    # Verify helpers
    "format_verify_result_for_json",
    "print_all_components_result",
    "print_tmdb_verification_result",
]
