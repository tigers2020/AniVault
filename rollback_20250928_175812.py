#!/usr/bin/env python3
"""Rollback script generated on 2025-09-28T17:58:12.527838Z
This script will reverse the file organization operations performed by AniVault CLI.
Run this script to restore files to their original locations.
"""

import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path


def calculate_file_hash(file_path: Path) -> str:
    """Calculate MD5 hash of a file for verification."""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return ""


def verify_file_integrity(file_path: Path, expected_hash: str) -> bool:
    """Verify file integrity using hash comparison."""
    if not file_path.exists():
        return False

    if not expected_hash:
        return True  # No hash to compare

    actual_hash = calculate_file_hash(file_path)
    return actual_hash == expected_hash


def create_backup(file_path: Path) -> Path:
    """Create a backup of a file before rollback."""
    backup_path = file_path.with_suffix(file_path.suffix + ".rollback_backup")
    counter = 1
    while backup_path.exists():
        backup_path = file_path.with_suffix(
            f"{file_path.suffix}.rollback_backup_{counter}"
        )
        counter += 1

    shutil.copy2(file_path, backup_path)
    return backup_path


def main():
    rollback_operations = [
        {
            "operation_id": "op_20250928_175812_0000",
            "timestamp": "2025-09-28T17:58:12.523966Z",
            "action": "rollback_move",
            "source": "test_output\\Attack (Unknown)\\Season 01\\Attack_on_Titan_S01E01_1080p.mkv",
            "destination": "test_files\\Attack_on_Titan_S01E01_1080p.mkv",
            "file_hash": "ed2491c22ab84c855b93c43f31cbeca5",
            "file_size": 36,
            "original_operation": "move",
            "original_source": "test_files\\Attack_on_Titan_S01E01_1080p.mkv",
            "original_destination": "test_output\\Attack (Unknown)\\Season 01\\Attack_on_Titan_S01E01_1080p.mkv",
        },
        {
            "operation_id": "op_20250928_175812_0001",
            "timestamp": "2025-09-28T17:58:12.526737Z",
            "action": "rollback_move",
            "source": "test_output\\One (Unknown)\\Season 01\\One_Piece_S01E01_720p.mkv",
            "destination": "test_files\\One_Piece_S01E01_720p.mkv",
            "file_hash": "8c289635946168f475e23a76170cd5e4",
            "file_size": 40,
            "original_operation": "move",
            "original_source": "test_files\\One_Piece_S01E01_720p.mkv",
            "original_destination": "test_output\\One (Unknown)\\Season 01\\One_Piece_S01E01_720p.mkv",
        },
    ]

    print("AniVault Rollback Script")
    print("Generated: 2025-09-28T17:58:12.527866Z")
    print(f"Operations to rollback: {len(rollback_operations)}")
    print("-" * 50)

    success_count = 0
    error_count = 0
    skipped_count = 0
    backup_count = 0

    # Create rollback log
    rollback_log_path = Path("rollback_execution.jsonl")

    for i, operation in enumerate(rollback_operations):
        operation_id = operation.get("operation_id", f"rollback_{i:04d}")
        source = Path(operation["source"])  # Current location
        destination = Path(operation["destination"])  # Original location
        expected_hash = operation.get("file_hash", "")
        file_size = operation.get("file_size", 0)

        rollback_entry = {
            "operation_id": operation_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": "rollback_attempt",
            "source": str(source),
            "destination": str(destination),
            "expected_hash": expected_hash,
            "status": "attempting",
        }

        try:
            # Check if source file exists
            if not source.exists():
                print(f"⚠ [{i + 1:3d}] Source not found: {source}")
                rollback_entry["status"] = "skipped"
                rollback_entry["reason"] = "source_not_found"
                skipped_count += 1

                with open(rollback_log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rollback_entry) + "\n")
                continue

            # Verify file integrity if hash is available
            if expected_hash and not verify_file_integrity(source, expected_hash):
                print(f"⚠ [{i + 1:3d}] File integrity check failed: {source}")
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
                print(
                    f"ℹ [{i + 1:3d}] Destination exists, backed up: {existing_backup}"
                )

            # Move file back to original location
            source.rename(destination)

            # Verify the move was successful
            if destination.exists() and verify_file_integrity(
                destination, expected_hash
            ):
                print(f"✓ [{i + 1:3d}] Rolled back: {source.name} -> {destination}")
                rollback_entry["status"] = "completed"
                success_count += 1
            else:
                print(f"✗ [{i + 1:3d}] Rollback verification failed: {destination}")
                rollback_entry["status"] = "failed"
                rollback_entry["reason"] = "verification_failed"
                error_count += 1

        except Exception as e:
            print(f"✗ [{i + 1:3d}] Failed to rollback {source.name}: {e}")
            rollback_entry["status"] = "failed"
            rollback_entry["error"] = str(e)
            rollback_entry["error_type"] = type(e).__name__
            error_count += 1

        # Log rollback attempt
        with open(rollback_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rollback_entry) + "\n")

    # Summary
    print("-" * 50)
    print("Rollback Summary:")
    print(f"  ✓ Successful: {success_count}")
    print(f"  ⚠ Skipped: {skipped_count}")
    print(f"  ✗ Errors: {error_count}")
    print(f"  💾 Backups created: {backup_count}")
    print(f"  📝 Log file: {rollback_log_path}")

    if backup_count > 0:
        print("\n💡 Backup files created with .rollback_backup extension")
        print("   You can delete these after verifying the rollback was successful")

    # Exit with appropriate code
    if error_count > 0:
        print(f"\n⚠ Rollback completed with {error_count} errors")
        sys.exit(1)
    else:
        print("\n✓ Rollback completed successfully")
        sys.exit(0)


if __name__ == "__main__":
    main()
