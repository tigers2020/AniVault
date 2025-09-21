#!/usr/bin/env python3
"""
Example usage of the synchronization scheduler.

This script demonstrates how to set up and use the synchronization scheduler
for cache-database synchronization operations.
"""

import sys
import os
import time
import logging
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.sync_integration import initialize_sync_system, create_sync_callback
from core.sync_scheduler import SyncTrigger
from core.metadata_cache import MetadataCache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main example function."""
    print("AniVault Synchronization Scheduler Example")
    print("=" * 50)
    
    # Initialize metadata cache
    print("1. Initializing metadata cache...")
    metadata_cache = MetadataCache()
    
    # Create a custom callback for job results
    def custom_sync_callback(result):
        """Custom callback to handle sync job results."""
        if result.status.value == "success":
            print(f"✅ Job {result.job_id} completed: {result.records_processed} records processed")
        else:
            print(f"❌ Job {result.job_id} failed: {result.error_message}")
    
    # Create sync callback
    sync_callback = create_sync_callback(
        log_results=True,
        alert_on_failure=True,
        custom_handler=custom_sync_callback
    )
    
    # Initialize sync system
    print("2. Initializing synchronization system...")
    sync_manager = initialize_sync_system(
        metadata_cache=metadata_cache,
        enable_consistency=True,
        enable_incremental=True,
        enable_full_sync=False,
        custom_intervals={
            "consistency": 300,  # 5 minutes
            "incremental": 60    # 1 minute
        },
        start_scheduler=True
    )
    
    # Add callback
    sync_manager.add_callback(sync_callback)
    
    print("3. Synchronization system initialized!")
    print(f"   - Jobs configured: {len(sync_manager.sync_scheduler.jobs)}")
    print(f"   - Scheduler running: {sync_manager.sync_scheduler.running}")
    
    # Show job status
    print("\n4. Current job status:")
    job_status = sync_manager.get_all_job_status()
    for job_id, status in job_status.items():
        print(f"   - {job_id}: {status['job_type']} (enabled: {status['enabled']}, interval: {status['interval_seconds']}s)")
    
    # Add a custom job
    print("\n5. Adding custom high-frequency sync job...")
    sync_manager.add_custom_job(
        job_id="high_freq_metadata_sync",
        job_type="incremental_sync",
        interval_seconds=30,  # 30 seconds
        enabled=True,
        trigger_types=["scheduled", "data_change"],
        entity_types=["tmdb_metadata"],  # Only metadata, not files
        priority=1  # High priority
    )
    
    print("   Custom job added successfully!")
    
    # Demonstrate manual job execution
    print("\n6. Running jobs manually...")
    
    # Run incremental sync manually
    print("   Running incremental sync...")
    result = sync_manager.run_job_now("incremental_sync", SyncTrigger.MANUAL)
    if result:
        print(f"   Result: {result.status.value} - {result.records_processed} records processed")
    
    # Run consistency validation manually
    print("   Running consistency validation...")
    result = sync_manager.run_job_now("consistency_validation", SyncTrigger.MANUAL)
    if result:
        print(f"   Result: {result.status.value} - {result.conflicts_found} conflicts found")
    
    # Demonstrate job management
    print("\n7. Job management operations...")
    
    # Disable a job
    sync_manager.disable_job("high_freq_metadata_sync")
    print("   Disabled high-frequency sync job")
    
    # Enable a job
    sync_manager.enable_job("high_freq_metadata_sync")
    print("   Re-enabled high-frequency sync job")
    
    # Show updated status
    print("\n8. Updated job status:")
    job_status = sync_manager.get_all_job_status()
    for job_id, status in job_status.items():
        last_run = status['last_result']['status'] if status['last_result'] else 'Never'
        print(f"   - {job_id}: {status['job_type']} (last run: {last_run})")
    
    # Show scheduler information
    print("\n9. Scheduler information:")
    scheduler_info = sync_manager.get_scheduler_info()
    print(f"   - Status: {scheduler_info['status']}")
    print(f"   - Job count: {scheduler_info['job_count']}")
    print(f"   - Enabled jobs: {scheduler_info['enabled_jobs']}")
    print(f"   - Check interval: {scheduler_info['scheduler_config']['check_interval_seconds']}s")
    
    # Let the scheduler run for a bit
    print("\n10. Letting scheduler run for 10 seconds...")
    print("    (You should see periodic job executions in the logs)")
    
    try:
        time.sleep(10)
    except KeyboardInterrupt:
        print("\n    Interrupted by user")
    
    # Stop the scheduler
    print("\n11. Stopping scheduler...")
    sync_manager.stop_scheduler()
    print("    Scheduler stopped")
    
    print("\n✅ Example completed successfully!")
    print("\nKey features demonstrated:")
    print("  - Automatic job scheduling with configurable intervals")
    print("  - Multiple job types (consistency validation, incremental sync)")
    print("  - Manual job execution")
    print("  - Job management (enable/disable/remove)")
    print("  - Custom job creation")
    print("  - Callback system for job results")
    print("  - Comprehensive status monitoring")


if __name__ == "__main__":
    main()
