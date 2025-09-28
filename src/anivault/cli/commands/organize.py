"""Organize command implementation."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
from rich.console import Console

from anivault.core.logging import get_logger

logger = get_logger(__name__)
console = Console()


@click.command()
@click.option(
    "--src",
    "-s",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Source directory containing files to organize",
)
@click.option(
    "--dst",
    "-d",
    type=click.Path(path_type=Path),
    help="Destination directory for organized files",
)
@click.option(
    "--input",
    "-i",
    type=click.Path(exists=True, path_type=Path),
    help="Input file with match results",
)
@click.option(
    "--plan",
    type=click.Path(path_type=Path),
    help="Output plan file for review before applying",
)
@click.option(
    "--from-plan",
    type=click.Path(exists=True, path_type=Path),
    help="Execute plan from file",
)
@click.option(
    "--apply",
    is_flag=True,
    help="Apply changes (default is dry-run)",
)
@click.option(
    "--naming-schema",
    default="{title} ({year})/Season {season:02d}",
    help="Naming schema for organized files",
)
@click.option(
    "--conflict-resolution",
    type=click.Choice(["skip", "overwrite", "rename"]),
    default="rename",
    help="How to handle file conflicts",
)
@click.option(
    "--preserve-structure",
    is_flag=True,
    help="Preserve original directory structure",
)
@click.option(
    "--json",
    is_flag=True,
    help="Output in JSON format (NDJSON)",
)
@click.pass_context
def organize(
    ctx: click.Context,
    src: Path,
    dst: Path,
    input: Optional[Path],
    plan: Optional[Path],
    from_plan: Optional[Path],
    apply: bool,
    naming_schema: str,
    conflict_resolution: str,
    preserve_structure: bool,
    json: bool,
) -> None:
    """Organize files based on TMDB metadata.

    This command organizes files into a structured directory layout
    based on TMDB metadata matches. By default, it runs in dry-run mode
    and requires --apply to make actual changes.
    """
    json_output = json or ctx.obj.get("json_output", False)

    try:
        # Validate inputs
        if from_plan and input:
            error_msg = "Cannot use both --from-plan and --input"
            if json_output:
                _output_json_error("E-ORGANIZE-CONFLICT", error_msg)
            else:
                console.print(f"[red]Error: {error_msg}[/red]")
            sys.exit(6)

        # Validate required options
        if not from_plan and (not src or not dst):
            error_msg = "Both --src and --dst are required when not using --from-plan"
            if json_output:
                _output_json_error("E-ORGANIZE-MISSING-OPTIONS", error_msg)
            else:
                console.print(f"[red]Error: {error_msg}[/red]")
            sys.exit(6)

        # Output organize start event
        if json_output:
            _output_json_event(
                "organize",
                "start",
                {
                    "source": str(src) if src else "from-plan",
                    "destination": str(dst) if dst else "from-plan",
                    "apply": apply,
                    "naming_schema": naming_schema,
                    "conflict_resolution": conflict_resolution,
                    "preserve_structure": preserve_structure,
                },
            )
        else:
            mode = "APPLY" if apply else "DRY-RUN"
            if from_plan:
                console.print(f"[blue]Organizing files from plan ({mode})[/blue]")
            else:
                console.print(f"[blue]Organizing files ({mode}): {src} -> {dst}[/blue]")

        # Load match results
        if from_plan:
            organization_plan = _load_plan_file(from_plan)
            # Skip plan generation, use loaded plan directly
        elif input:
            match_results = _load_match_results(input)
            # Generate organization plan
            organization_plan = _generate_organization_plan(
                match_results,
                src,
                dst,
                naming_schema,
                conflict_resolution,
                preserve_structure,
            )
        else:
            # Scan and match on the fly (simplified for now)
            match_results = _scan_and_match(src)
            # Generate organization plan
            organization_plan = _generate_organization_plan(
                match_results,
                src,
                dst,
                naming_schema,
                conflict_resolution,
                preserve_structure,
            )

        # Detect conflicts
        conflicts = _detect_conflicts(organization_plan)
        if conflicts["file_conflicts"] or conflicts["directory_conflicts"]:
            if json_output:
                _output_json_event("organize", "conflicts_detected", conflicts)
            else:
                console.print(
                    f"[yellow]Warning: {len(conflicts['file_conflicts'])} file conflicts detected[/yellow]"
                )
                console.print(
                    f"[yellow]Warning: {len(conflicts['directory_conflicts'])} directory conflicts detected[/yellow]"
                )

        # Output plan if requested
        if plan:
            _save_plan_file(organization_plan, plan)
            if not json_output:
                console.print(f"Organization plan saved to: {plan}")

        # Execute plan if apply is specified
        if apply:
            results = _execute_organization_plan(organization_plan, json_output)

            # Output results
            if json_output:
                _output_json_event("organize", "complete", results)
            else:
                console.print("[green]Organization completed![/green]")
                console.print(f"Files processed: {results['total_files']}")
                console.print(f"Files moved: {results['files_moved']}")
                console.print(f"Files skipped: {results['files_skipped']}")
                console.print(f"Errors: {results['errors']}")

                # Show rollback information
                if results.get("rollback_script"):
                    console.print(
                        f"[yellow]Rollback script generated: {results['rollback_script']}[/yellow]"
                    )
                    console.print(
                        f"[dim]To undo changes, run: python {results['rollback_script']}[/dim]"
                    )

                # Show log files
                if results.get("operation_log"):
                    console.print(
                        f"[blue]Operation log: {results['operation_log']}[/blue]"
                    )
                if results.get("rollback_log_file"):
                    console.print(
                        f"[blue]Rollback log: {results['rollback_log_file']}[/blue]"
                    )

                    # Verify rollback log integrity
                    rollback_log_path = Path(results["rollback_log_file"])
                    if rollback_log_path.exists():
                        verification_results = _verify_rollback_log_integrity(
                            rollback_log_path
                        )
                        if verification_results["integrity_score"] < 1.0:
                            console.print(
                                f"[yellow]⚠ Rollback log integrity: {verification_results['integrity_score']:.1%}[/yellow]"
                            )
                        else:
                            console.print(
                                f"[green]✓ Rollback log integrity: {verification_results['integrity_score']:.1%}[/green]"
                            )
        else:
            # Dry run - just show what would be done
            _show_dry_run_results(organization_plan, json_output)

        # Exit with appropriate code
        if organization_plan.get("errors", 0) > 0:
            sys.exit(10)  # Partial success
        else:
            sys.exit(0)  # Full success

    except Exception as e:
        logger.exception("Organize failed")
        if json_output:
            _output_json_error("E-ORGANIZE-FAIL", str(e))
        else:
            console.print(f"[red]Organize failed: {e}[/red]")
        sys.exit(1)


def _load_plan_file(plan_path: Path) -> Dict[str, Any]:
    """Load organization plan from file."""
    with open(plan_path, encoding="utf-8") as f:
        plan = json.load(f)

    # Validate plan schema
    _validate_plan_schema(plan)

    return plan


def _validate_plan_schema(plan: Dict[str, Any]) -> None:
    """Validate organization plan against schema."""
    required_fields = [
        "timestamp",
        "source",
        "destination",
        "naming_schema",
        "conflict_resolution",
        "preserve_structure",
        "operations",
    ]

    for field in required_fields:
        if field not in plan:
            raise ValueError(f"Missing required field in plan: {field}")

    # Validate operations
    if not isinstance(plan["operations"], list):
        raise ValueError("Operations must be a list")

    for i, operation in enumerate(plan["operations"]):
        if not isinstance(operation, dict):
            raise ValueError(f"Operation {i} must be a dictionary")

        required_op_fields = ["source", "destination", "action"]
        for field in required_op_fields:
            if field not in operation:
                raise ValueError(f"Missing required field in operation {i}: {field}")

        if operation["action"] not in ["move", "copy", "rename"]:
            raise ValueError(f"Invalid action in operation {i}: {operation['action']}")

    # Validate conflict resolution
    if plan["conflict_resolution"] not in ["skip", "overwrite", "rename"]:
        raise ValueError(f"Invalid conflict resolution: {plan['conflict_resolution']}")


def _load_match_results(input_path: Path) -> Dict[str, Any]:
    """Load match results from file."""
    with open(input_path, encoding="utf-8") as f:
        return json.load(f)


def _scan_and_match(src: Path) -> Dict[str, Any]:
    """Scan and match files (simplified implementation)."""
    # Import scanner and matcher modules
    from anivault.scanner.file_scanner import scan_directory_with_stats

    # Scan directory
    file_iterator, stats = scan_directory_with_stats(src)

    # Convert iterator to list of file info
    files = []
    for entry in file_iterator:
        files.append(
            {
                "path": entry.path,
                "name": entry.name,
                "size": entry.stat().st_size if entry.is_file() else 0,
                "is_file": entry.is_file(),
                "is_dir": entry.is_dir(),
            }
        )

    # For now, return scan results without actual matching
    # In a real implementation, this would call the matcher
    return {
        "files": files,
        "stats": stats,
        "matches": [],
    }


def _generate_organization_plan(
    match_results: Dict[str, Any],
    src: Path,
    dst: Path,
    naming_schema: str,
    conflict_resolution: str,
    preserve_structure: bool,
) -> Dict[str, Any]:
    """Generate organization plan."""
    plan = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": str(src),
        "destination": str(dst),
        "naming_schema": naming_schema,
        "conflict_resolution": conflict_resolution,
        "preserve_structure": preserve_structure,
        "operations": [],
        "errors": 0,
    }

    # Process each file from scan results
    files = match_results.get("files", [])
    for file_info in files:
        if not file_info.get("is_file", False):
            continue

        # For now, create a simple organization plan without TMDB matching
        # In a real implementation, this would use TMDB metadata
        file_path = Path(file_info["path"])
        filename = file_path.name

        # Extract basic info from filename (simplified)
        # This is a placeholder - in real implementation, use anitopy + TMDB
        title = "Unknown"
        year = "Unknown"
        season = 1

        # Try to extract title from filename (basic approach)
        if "_" in filename:
            parts = filename.split("_")
            if len(parts) >= 2:
                title = parts[0].replace("_", " ").replace("-", " ")
                # Look for year pattern
                for part in parts:
                    if part.isdigit() and len(part) == 4:
                        year = part
                        break

        # Sanitize title for filesystem
        sanitized_title = _sanitize_filename(title)

        # Generate destination path using naming schema
        formatted_name = naming_schema.format(
            title=sanitized_title,
            year=year,
            season=season,
        )

        # Create destination path
        dest_path = dst / formatted_name / file_path.name

        # Add operation to plan
        operation = {
            "source": str(file_path),
            "destination": str(dest_path),
            "action": "move",
            "metadata": {
                "title": title,
                "year": year,
                "season": season,
                "filename": filename,
            },
        }
        plan["operations"].append(operation)

    return plan


def _generate_destination_path(
    file_info: Dict[str, Any],
    tmdb_match: Dict[str, Any],
    dst: Path,
    naming_schema: str,
) -> Path:
    """Generate destination path for a file."""
    # Extract metadata
    title = tmdb_match.get("title", "Unknown")
    year = (
        tmdb_match.get("first_air_date", "").split("-")[0]
        if tmdb_match.get("first_air_date")
        else "Unknown"
    )
    season = file_info.get("season", 1)
    episode = file_info.get("episode_number", "")

    # Handle special episodes (Season 0)
    if file_info.get("episode_title", "").lower() in ["special", "ova", "ona", "movie"]:
        season = 0

    # Sanitize title for filesystem
    sanitized_title = _sanitize_filename(title)

    # Format naming schema with episode support
    if episode:
        # Multi-episode support
        if "-" in episode:
            # Range episode (e.g., "01-03")
            ep_start, ep_end = episode.split("-", 1)
            episode_token = f"E{ep_start.zfill(2)}-E{ep_end.zfill(2)}"
        else:
            # Single episode
            episode_token = f"E{episode.zfill(2)}"

        # Include episode in naming schema
        formatted_name = naming_schema.format(
            title=sanitized_title,
            year=year,
            season=season,
            episode=episode_token,
        )
    else:
        # No episode info
        formatted_name = naming_schema.format(
            title=sanitized_title,
            year=year,
            season=season,
        )

    # Create destination path
    dest_dir = dst / formatted_name
    filename = Path(file_info.get("path", "")).name

    # Sanitize the entire path
    dest_path = _sanitize_path(dest_dir / filename)

    # Handle long paths on Windows
    dest_path = _handle_long_path(dest_path)

    return dest_path


def _sanitize_filename(filename: str) -> str:
    """Sanitize filename for filesystem compatibility."""
    import re
    import unicodedata

    # Normalize Unicode characters
    filename = unicodedata.normalize("NFC", filename)

    # Replace problematic characters
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)

    # Replace control characters
    filename = re.sub(r"[\x00-\x1f\x7f-\x9f]", "_", filename)

    # Replace reserved names (Windows)
    reserved_names = [
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    ]
    if filename.upper() in reserved_names:
        filename = f"_{filename}"

    # Remove trailing dots and spaces
    filename = filename.rstrip(". ")

    # Remove leading/trailing whitespace
    filename = filename.strip()

    # Handle empty filename
    if not filename:
        filename = "unnamed"

    # Limit length (Windows path limit)
    if len(filename) > 200:  # Leave room for extension
        filename = filename[:200]

    return filename


def _sanitize_path(path: Path) -> Path:
    """Sanitize entire path for filesystem compatibility."""
    parts = []

    for part in path.parts:
        sanitized_part = _sanitize_filename(part)
        parts.append(sanitized_part)

    return Path(*parts)


def _handle_long_path(path: Path) -> Path:
    """Handle Windows long path limitations."""
    # Convert to Windows long path format if needed
    if len(str(path)) > 260:
        # Use UNC path format for long paths
        if not str(path).startswith("\\\\?\\"):
            path = Path(f"\\\\?\\{path.absolute()}")

    return path


def _save_plan_file(plan: Dict[str, Any], plan_path: Path) -> None:
    """Save organization plan to file."""
    # Ensure plan directory exists
    plan_path.parent.mkdir(parents=True, exist_ok=True)

    # Add metadata to plan
    plan["schema_version"] = "1.0"
    plan["generated_by"] = "AniVault CLI"
    plan["total_operations"] = len(plan["operations"])

    # Write plan file atomically
    temp_path = plan_path.with_suffix(plan_path.suffix + ".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)

    # Atomic rename
    temp_path.replace(plan_path)


def _execute_organization_plan(
    plan: Dict[str, Any], json_output: bool
) -> Dict[str, Any]:
    """Execute organization plan with comprehensive rollback logging."""
    results = {
        "total_files": len(plan["operations"]),
        "files_moved": 0,
        "files_skipped": 0,
        "errors": 0,
        "rollback_log": [],
        "operation_log": [],
    }

    # Create rollback log file with timestamp
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    rollback_log_path = Path(f"rollback_{timestamp}.jsonl")
    operation_log_path = Path(f"operation_{timestamp}.jsonl")

    # Initialize operation log with plan metadata
    operation_log_entry = {
        "operation_id": f"plan_{timestamp}",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "operation": "plan_execution_start",
        "plan_metadata": {
            "source": plan.get("source", ""),
            "destination": plan.get("destination", ""),
            "naming_schema": plan.get("naming_schema", ""),
            "conflict_resolution": plan.get("conflict_resolution", "rename"),
            "total_operations": len(plan["operations"]),
        },
        "status": "started",
    }

    # Write initial operation log
    with open(operation_log_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(operation_log_entry) + "\n")

    for i, operation in enumerate(plan["operations"]):
        operation_id = f"op_{timestamp}_{i:04d}"

        try:
            source = Path(operation["source"])
            destination = Path(operation["destination"])

            # Pre-operation logging
            pre_op_log = {
                "operation_id": operation_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "operation": "pre_validation",
                "source": str(source),
                "destination": str(destination),
                "action": operation.get("action", "move"),
                "status": "validating",
            }

            # Sanitize paths
            source = _sanitize_path(source)
            destination = _sanitize_path(destination)

            # Handle long paths
            source = _handle_long_path(source)
            destination = _handle_long_path(destination)

            # Check if source exists
            if not source.exists():
                logger.warning("Source file does not exist: %s", source)
                pre_op_log["status"] = "skipped"
                pre_op_log["reason"] = "source_not_found"
                results["files_skipped"] += 1

                # Log skipped operation
                with open(operation_log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(pre_op_log) + "\n")
                continue

            # Get file metadata before operation
            file_stat = source.stat()
            file_hash = _calculate_file_hash(source)
            file_size = file_stat.st_size

            # Handle conflicts
            original_destination = destination
            if destination.exists():
                conflict_resolution = plan.get("conflict_resolution", "rename")
                destination = _resolve_conflict(destination, conflict_resolution)
                pre_op_log["conflict_resolved"] = True
                pre_op_log["original_destination"] = str(original_destination)
                pre_op_log["resolved_destination"] = str(destination)

            # Create destination directory
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Pre-operation validation complete
            pre_op_log["status"] = "validated"
            pre_op_log["file_hash"] = file_hash
            pre_op_log["file_size"] = file_size
            pre_op_log["final_destination"] = str(destination)

            # Log pre-operation
            with open(operation_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(pre_op_log) + "\n")

            # Execute the operation
            operation_log = {
                "operation_id": operation_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "operation": "file_move",
                "source": str(source),
                "destination": str(destination),
                "file_hash": file_hash,
                "file_size": file_size,
                "status": "executing",
            }

            # Move file
            source.rename(destination)
            results["files_moved"] += 1

            # Post-operation logging
            operation_log["status"] = "completed"
            operation_log["completion_time"] = datetime.utcnow().isoformat() + "Z"

            # Log successful operation
            with open(operation_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(operation_log) + "\n")

            # Create rollback entry
            rollback_entry = {
                "operation_id": operation_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "action": "rollback_move",
                "source": str(destination),  # Current location
                "destination": str(source),  # Original location
                "file_hash": file_hash,
                "file_size": file_size,
                "original_operation": "move",
                "original_source": str(source),
                "original_destination": str(destination),
            }
            results["rollback_log"].append(rollback_entry)

            # Write rollback log entry
            with open(rollback_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rollback_entry) + "\n")

        except Exception as e:
            logger.exception("Failed to move file: %s", operation["source"])

            # Log failed operation
            error_log = {
                "operation_id": operation_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "operation": "file_move",
                "source": str(operation.get("source", "")),
                "destination": str(operation.get("destination", "")),
                "status": "failed",
                "error": str(e),
                "error_type": type(e).__name__,
            }

            with open(operation_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(error_log) + "\n")

            results["errors"] += 1

    # Log plan completion
    completion_log = {
        "operation_id": f"plan_{timestamp}_complete",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "operation": "plan_execution_complete",
        "results": {
            "total_files": results["total_files"],
            "files_moved": results["files_moved"],
            "files_skipped": results["files_skipped"],
            "errors": results["errors"],
        },
        "status": "completed",
    }

    with open(operation_log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(completion_log) + "\n")

    # Generate rollback script if there were successful operations
    if results["files_moved"] > 0:
        rollback_script_path = Path(f"rollback_{timestamp}.py")
        _generate_rollback_script(results["rollback_log"], rollback_script_path)
        results["rollback_script"] = str(rollback_script_path)

    results["operation_log"] = str(operation_log_path)
    results["rollback_log_file"] = str(rollback_log_path)

    return results


def _resolve_conflict(destination: Path, conflict_resolution: str) -> Path:
    """Resolve file conflicts with advanced strategies."""
    if conflict_resolution == "skip":
        raise FileExistsError(f"File already exists: {destination}")
    if conflict_resolution == "overwrite":
        return destination
    if conflict_resolution == "rename":
        return _generate_unique_filename(destination)
    raise ValueError(f"Unknown conflict resolution: {conflict_resolution}")


def _generate_unique_filename(destination: Path) -> Path:
    """Generate a unique filename to avoid conflicts."""
    if not destination.exists():
        return destination

    # Try different naming strategies
    strategies = [
        lambda p, i: p.parent / f"{p.stem}_{i}{p.suffix}",  # filename_1.ext
        lambda p, i: p.parent / f"{p.stem} ({i}){p.suffix}",  # filename (1).ext
        lambda p, i: p.parent / f"{p.stem}.{i}{p.suffix}",  # filename.1.ext
    ]

    for strategy in strategies:
        counter = 1
        while destination.exists():
            destination = strategy(destination, counter)
            counter += 1
            if counter > 1000:  # Prevent infinite loops
                break

        if not destination.exists():
            break

    return destination


def _detect_conflicts(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Detect potential conflicts in the organization plan."""
    conflicts = {
        "file_conflicts": [],
        "directory_conflicts": [],
        "permission_issues": [],
    }

    # Check for file conflicts
    destination_paths = {}
    for operation in plan["operations"]:
        dest_path = operation["destination"]

        if dest_path in destination_paths:
            conflicts["file_conflicts"].append(
                {
                    "destination": dest_path,
                    "sources": [destination_paths[dest_path], operation["source"]],
                }
            )
        else:
            destination_paths[dest_path] = operation["source"]

    # Check for directory conflicts
    directories = set()
    for operation in plan["operations"]:
        dest_dir = Path(operation["destination"]).parent
        if dest_dir in directories:
            conflicts["directory_conflicts"].append(str(dest_dir))
        else:
            directories.add(dest_dir)

    return conflicts


def _calculate_file_hash(file_path: Path) -> str:
    """Calculate file hash for rollback verification."""
    import hashlib

    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)

    return hash_md5.hexdigest()


def _show_dry_run_results(plan: Dict[str, Any], json_output: bool) -> None:
    """Show dry run results."""
    if json_output:
        _output_json_event(
            "organize",
            "dry_run",
            {
                "total_operations": len(plan["operations"]),
                "operations": plan["operations"],
            },
        )
    else:
        console.print(
            f"[yellow]Dry run - {len(plan['operations'])} operations would be performed[/yellow]"
        )
        for operation in plan["operations"][:5]:  # Show first 5
            console.print(f"  {operation['source']} -> {operation['destination']}")
        if len(plan["operations"]) > 5:
            console.print(f"  ... and {len(plan['operations']) - 5} more")


def _output_json_event(phase: str, event: str, fields: Dict[str, Any]) -> None:
    """Output event in JSON format."""
    event_data = {
        "phase": phase,
        "event": event,
        "ts": datetime.utcnow().isoformat() + "Z",
        "fields": fields,
    }
    print(json.dumps(event_data))


def _output_json_error(error_code: str, message: str) -> None:
    """Output error in JSON format."""
    error_data = {
        "phase": "error",
        "event": "error",
        "ts": datetime.utcnow().isoformat() + "Z",
        "fields": {
            "error_code": error_code,
            "message": message,
            "level": "ERROR",
        },
    }
    print(json.dumps(error_data))


def _generate_rollback_script(
    rollback_log: List[Dict[str, Any]], output_path: Path
) -> None:
    """Generate comprehensive rollback script from rollback log."""
    script_content = f"""#!/usr/bin/env python3
\"\"\"Rollback script generated on {datetime.utcnow().isoformat()}Z
This script will reverse the file organization operations performed by AniVault CLI.
Run this script to restore files to their original locations.
\"\"\"

import json
import sys
import hashlib
import shutil
from pathlib import Path
from datetime import datetime

def calculate_file_hash(file_path: Path) -> str:
    \"\"\"Calculate MD5 hash of a file for verification.\"\"\"
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return ""

def verify_file_integrity(file_path: Path, expected_hash: str) -> bool:
    \"\"\"Verify file integrity using hash comparison.\"\"\"
    if not file_path.exists():
        return False

    if not expected_hash:
        return True  # No hash to compare

    actual_hash = calculate_file_hash(file_path)
    return actual_hash == expected_hash

def create_backup(file_path: Path) -> Path:
    \"\"\"Create a backup of a file before rollback.\"\"\"
    backup_path = file_path.with_suffix(file_path.suffix + ".rollback_backup")
    counter = 1
    while backup_path.exists():
        backup_path = file_path.with_suffix(f"{{file_path.suffix}}.rollback_backup_{{counter}}")
        counter += 1

    shutil.copy2(file_path, backup_path)
    return backup_path

def main():
    rollback_operations = {json.dumps(rollback_log, indent=2)}

    print(f"AniVault Rollback Script")
    print(f"Generated: {datetime.utcnow().isoformat()}Z")
    print(f"Operations to rollback: {{len(rollback_operations)}}")
    print("-" * 50)

    success_count = 0
    error_count = 0
    skipped_count = 0
    backup_count = 0

    # Create rollback log
    rollback_log_path = Path("rollback_execution.jsonl")

    for i, operation in enumerate(rollback_operations):
        operation_id = operation.get("operation_id", f"rollback_{{i:04d}}")
        source = Path(operation["source"])  # Current location
        destination = Path(operation["destination"])  # Original location
        expected_hash = operation.get("file_hash", "")
        file_size = operation.get("file_size", 0)

        rollback_entry = {{
            "operation_id": operation_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": "rollback_attempt",
            "source": str(source),
            "destination": str(destination),
            "expected_hash": expected_hash,
            "status": "attempting"
        }}

        try:
            # Check if source file exists
            if not source.exists():
                print(f"⚠ [{{i+1:3d}}] Source not found: {{source}}")
                rollback_entry["status"] = "skipped"
                rollback_entry["reason"] = "source_not_found"
                skipped_count += 1

                with open(rollback_log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rollback_entry) + "\\n")
                continue

            # Verify file integrity if hash is available
            if expected_hash and not verify_file_integrity(source, expected_hash):
                print(f"⚠ [{{i+1:3d}}] File integrity check failed: {{source}}")
                rollback_entry["status"] = "warning"
                rollback_entry["reason"] = "integrity_check_failed"
                rollback_entry["expected_hash"] = expected_hash
                rollback_entry["actual_hash"] = calculate_file_hash(source)

            # Create backup of current file
            backup_path = create_backup(source)
            backup_count += 1
            rollback_entry["backup_path"] = str(backup_path)

            # Create destination directory
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Check if destination already exists
            if destination.exists():
                # Create backup of existing file
                existing_backup = create_backup(destination)
                rollback_entry["destination_backup"] = str(existing_backup)
                print(f"ℹ [{{i+1:3d}}] Destination exists, backed up: {{existing_backup}}")

            # Move file back to original location
            source.rename(destination)

            # Verify the move was successful
            if destination.exists() and verify_file_integrity(destination, expected_hash):
                print(f"✓ [{{i+1:3d}}] Rolled back: {{source.name}} -> {{destination}}")
                rollback_entry["status"] = "completed"
                success_count += 1
            else:
                print(f"✗ [{{i+1:3d}}] Rollback verification failed: {{destination}}")
                rollback_entry["status"] = "failed"
                rollback_entry["reason"] = "verification_failed"
                error_count += 1

        except Exception as e:
            print(f"✗ [{{i+1:3d}}] Failed to rollback {{source.name}}: {{e}}")
            rollback_entry["status"] = "failed"
            rollback_entry["error"] = str(e)
            rollback_entry["error_type"] = type(e).__name__
            error_count += 1

        # Log rollback attempt
        with open(rollback_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rollback_entry) + "\\n")

    # Summary
    print("-" * 50)
    print(f"Rollback Summary:")
    print(f"  ✓ Successful: {{success_count}}")
    print(f"  ⚠ Skipped: {{skipped_count}}")
    print(f"  ✗ Errors: {{error_count}}")
    print(f"  💾 Backups created: {{backup_count}}")
    print(f"  📝 Log file: {{rollback_log_path}}")

    if backup_count > 0:
        print(f"\\n💡 Backup files created with .rollback_backup extension")
        print(f"   You can delete these after verifying the rollback was successful")

    # Exit with appropriate code
    if error_count > 0:
        print(f"\\n⚠ Rollback completed with {{error_count}} errors")
        sys.exit(1)
    else:
        print(f"\\n✓ Rollback completed successfully")
        sys.exit(0)

if __name__ == "__main__":
    main()
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(script_content)

    # Make script executable on Unix systems
    try:
        import stat

        output_path.chmod(output_path.stat().st_mode | stat.S_IEXEC)
    except:
        pass  # Windows doesn't need executable permissions


def _verify_rollback_log_integrity(rollback_log_path: Path) -> Dict[str, Any]:
    """Verify the integrity of a rollback log file."""
    verification_results = {
        "log_file": str(rollback_log_path),
        "exists": False,
        "valid_entries": 0,
        "invalid_entries": 0,
        "total_entries": 0,
        "errors": [],
        "integrity_score": 0.0,
    }

    if not rollback_log_path.exists():
        verification_results["errors"].append("Rollback log file does not exist")
        return verification_results

    verification_results["exists"] = True

    try:
        with open(rollback_log_path, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                verification_results["total_entries"] += 1

                try:
                    entry = json.loads(line)

                    # Validate required fields
                    required_fields = [
                        "operation_id",
                        "timestamp",
                        "action",
                        "source",
                        "destination",
                    ]
                    missing_fields = [
                        field for field in required_fields if field not in entry
                    ]

                    if missing_fields:
                        verification_results["invalid_entries"] += 1
                        verification_results["errors"].append(
                            f"Line {line_num}: Missing fields {missing_fields}"
                        )
                        continue

                    # Validate file paths exist in rollback context
                    source_path = Path(entry["source"])
                    destination_path = Path(entry["destination"])

                    if not source_path.exists():
                        verification_results["errors"].append(
                            f"Line {line_num}: Source file not found: {source_path}"
                        )

                    if (
                        destination_path.parent.exists()
                        and not destination_path.exists()
                    ):
                        # This is expected for rollback - destination should not exist yet
                        pass

                    verification_results["valid_entries"] += 1

                except json.JSONDecodeError as e:
                    verification_results["invalid_entries"] += 1
                    verification_results["errors"].append(
                        f"Line {line_num}: Invalid JSON - {e}"
                    )
                    continue
                except Exception as e:
                    verification_results["invalid_entries"] += 1
                    verification_results["errors"].append(
                        f"Line {line_num}: Validation error - {e}"
                    )
                    continue

        # Calculate integrity score
        if verification_results["total_entries"] > 0:
            verification_results["integrity_score"] = (
                verification_results["valid_entries"]
                / verification_results["total_entries"]
            )

    except Exception as e:
        verification_results["errors"].append(f"Failed to read rollback log: {e}")

    return verification_results


def _generate_rollback_verification_report(verification_results: Dict[str, Any]) -> str:
    """Generate a human-readable rollback verification report."""
    report = []
    report.append("=" * 60)
    report.append("AniVault Rollback Log Verification Report")
    report.append("=" * 60)
    report.append(f"Log File: {verification_results['log_file']}")
    report.append(f"File Exists: {'Yes' if verification_results['exists'] else 'No'}")
    report.append(f"Total Entries: {verification_results['total_entries']}")
    report.append(f"Valid Entries: {verification_results['valid_entries']}")
    report.append(f"Invalid Entries: {verification_results['invalid_entries']}")
    report.append(f"Integrity Score: {verification_results['integrity_score']:.2%}")
    report.append("")

    if verification_results["errors"]:
        report.append("Issues Found:")
        for i, error in enumerate(verification_results["errors"], 1):
            report.append(f"  {i}. {error}")
    else:
        report.append("✓ No issues found - rollback log is valid")

    report.append("=" * 60)
    return "\n".join(report)
