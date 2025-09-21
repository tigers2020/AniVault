"""
Configuration management for synchronization scheduler.

This module provides predefined configurations and utilities for setting up
different types of synchronization jobs.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from .sync_scheduler import SyncJobConfig, SyncJobType, SyncTrigger
from .sync_enums import SyncEntityType


@dataclass
class SyncSchedulerConfig:
    """Configuration for the synchronization scheduler."""
    check_interval_seconds: int = 30
    max_concurrent_jobs: int = 3
    job_timeout_seconds: int = 300
    retry_delay_seconds: int = 30
    max_retries: int = 3
    enable_startup_sync: bool = True
    enable_data_change_triggers: bool = True
    enable_error_recovery: bool = True


# Predefined job configurations
DEFAULT_CONSISTENCY_JOB_CONFIG = SyncJobConfig(
    job_id="consistency_validation",
    job_type=SyncJobType.CONSISTENCY_VALIDATION,
    interval_seconds=300,  # 5 minutes
    enabled=True,
    trigger_types=[SyncTrigger.SCHEDULED, SyncTrigger.STARTUP],
    priority=1,
    max_retries=3,
    retry_delay_seconds=60,
    timeout_seconds=600
)

DEFAULT_INCREMENTAL_SYNC_JOB_CONFIG = SyncJobConfig(
    job_id="incremental_sync",
    job_type=SyncJobType.INCREMENTAL_SYNC,
    interval_seconds=60,  # 1 minute
    enabled=True,
    trigger_types=[SyncTrigger.SCHEDULED, SyncTrigger.DATA_CHANGE, SyncTrigger.STARTUP],
    entity_types=[SyncEntityType.TMDB_METADATA, SyncEntityType.PARSED_FILES],
    priority=2,
    max_retries=3,
    retry_delay_seconds=30,
    timeout_seconds=300
)

DEFAULT_FULL_SYNC_JOB_CONFIG = SyncJobConfig(
    job_id="full_sync",
    job_type=SyncJobType.FULL_SYNC,
    interval_seconds=3600,  # 1 hour
    enabled=False,  # Disabled by default, enable manually when needed
    trigger_types=[SyncTrigger.MANUAL, SyncTrigger.ERROR_RECOVERY],
    entity_types=[SyncEntityType.TMDB_METADATA, SyncEntityType.PARSED_FILES],
    priority=3,
    max_retries=2,
    retry_delay_seconds=120,
    timeout_seconds=1800  # 30 minutes
)

# High-frequency incremental sync for critical data
HIGH_FREQUENCY_INCREMENTAL_SYNC_CONFIG = SyncJobConfig(
    job_id="high_freq_incremental_sync",
    job_type=SyncJobType.INCREMENTAL_SYNC,
    interval_seconds=30,  # 30 seconds
    enabled=False,  # Disabled by default due to high frequency
    trigger_types=[SyncTrigger.SCHEDULED, SyncTrigger.DATA_CHANGE],
    entity_types=[SyncEntityType.TMDB_METADATA],  # Only metadata, not files
    priority=1,
    max_retries=5,
    retry_delay_seconds=15,
    timeout_seconds=120
)

# Low-frequency full sync for maintenance
MAINTENANCE_FULL_SYNC_CONFIG = SyncJobConfig(
    job_id="maintenance_full_sync",
    job_type=SyncJobType.FULL_SYNC,
    interval_seconds=86400,  # 24 hours
    enabled=False,  # Disabled by default
    trigger_types=[SyncTrigger.SCHEDULED, SyncTrigger.MANUAL],
    entity_types=[SyncEntityType.TMDB_METADATA, SyncEntityType.PARSED_FILES],
    priority=5,
    max_retries=1,
    retry_delay_seconds=300,
    timeout_seconds=3600  # 1 hour
)


class SyncConfigManager:
    """Manager for synchronization configurations."""
    
    def __init__(self):
        """Initialize the configuration manager."""
        self.configs: Dict[str, SyncJobConfig] = {}
        self.scheduler_config = SyncSchedulerConfig()
    
    def add_predefined_configs(self) -> None:
        """Add all predefined job configurations."""
        self.configs.update({
            "consistency_validation": DEFAULT_CONSISTENCY_JOB_CONFIG,
            "incremental_sync": DEFAULT_INCREMENTAL_SYNC_JOB_CONFIG,
            "full_sync": DEFAULT_FULL_SYNC_JOB_CONFIG,
            "high_freq_incremental_sync": HIGH_FREQUENCY_INCREMENTAL_SYNC_CONFIG,
            "maintenance_full_sync": MAINTENANCE_FULL_SYNC_CONFIG
        })
    
    def get_config(self, config_name: str) -> Optional[SyncJobConfig]:
        """Get a configuration by name.
        
        Args:
            config_name: Name of the configuration
            
        Returns:
            Configuration or None if not found
        """
        return self.configs.get(config_name)
    
    def get_all_configs(self) -> Dict[str, SyncJobConfig]:
        """Get all configurations.
        
        Returns:
            Dictionary of all configurations
        """
        return self.configs.copy()
    
    def create_custom_config(
        self,
        job_id: str,
        job_type: SyncJobType,
        interval_seconds: int,
        enabled: bool = True,
        trigger_types: Optional[List[SyncTrigger]] = None,
        entity_types: Optional[List[SyncEntityType]] = None,
        priority: int = 3,
        max_retries: int = 3,
        retry_delay_seconds: int = 30,
        timeout_seconds: int = 300
    ) -> SyncJobConfig:
        """Create a custom job configuration.
        
        Args:
            job_id: Unique identifier for the job
            job_type: Type of synchronization job
            interval_seconds: Interval between executions
            enabled: Whether the job is enabled
            trigger_types: Types of triggers that can start the job
            entity_types: Types of entities to synchronize
            priority: Job priority (lower = higher priority)
            max_retries: Maximum number of retries
            retry_delay_seconds: Delay between retries
            timeout_seconds: Job timeout
            
        Returns:
            Created configuration
        """
        config = SyncJobConfig(
            job_id=job_id,
            job_type=job_type,
            interval_seconds=interval_seconds,
            enabled=enabled,
            trigger_types=trigger_types,
            entity_types=entity_types,
            priority=priority,
            max_retries=max_retries,
            retry_delay_seconds=retry_delay_seconds,
            timeout_seconds=timeout_seconds
        )
        
        self.configs[job_id] = config
        return config
    
    def update_config(self, config_name: str, **kwargs) -> bool:
        """Update an existing configuration.
        
        Args:
            config_name: Name of the configuration to update
            **kwargs: Fields to update
            
        Returns:
            True if configuration was updated, False if not found
        """
        if config_name not in self.configs:
            return False
        
        config = self.configs[config_name]
        
        # Update allowed fields
        allowed_fields = {
            'enabled', 'interval_seconds', 'trigger_types', 'entity_types',
            'priority', 'max_retries', 'retry_delay_seconds', 'timeout_seconds'
        }
        
        for field_name, value in kwargs.items():
            if field_name in allowed_fields:
                setattr(config, field_name, value)
        
        return True
    
    def remove_config(self, config_name: str) -> bool:
        """Remove a configuration.
        
        Args:
            config_name: Name of the configuration to remove
            
        Returns:
            True if configuration was removed, False if not found
        """
        if config_name in self.configs:
            del self.configs[config_name]
            return True
        return False
    
    def get_enabled_configs(self) -> Dict[str, SyncJobConfig]:
        """Get all enabled configurations.
        
        Returns:
            Dictionary of enabled configurations
        """
        return {name: config for name, config in self.configs.items() if config.enabled}
    
    def get_configs_by_type(self, job_type: SyncJobType) -> Dict[str, SyncJobConfig]:
        """Get configurations by job type.
        
        Args:
            job_type: Type of job to filter by
            
        Returns:
            Dictionary of configurations of the specified type
        """
        return {name: config for name, config in self.configs.items() if config.job_type == job_type}
    
    def get_configs_by_trigger(self, trigger: SyncTrigger) -> Dict[str, SyncJobConfig]:
        """Get configurations that support a specific trigger.
        
        Args:
            trigger: Trigger type to filter by
            
        Returns:
            Dictionary of configurations that support the trigger
        """
        return {
            name: config for name, config in self.configs.items()
            if trigger in config.trigger_types
        }


# Global configuration manager instance
_global_config_manager: Optional[SyncConfigManager] = None


def get_global_config_manager() -> SyncConfigManager:
    """Get the global configuration manager instance.
    
    Returns:
        Global SyncConfigManager instance
    """
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = SyncConfigManager()
        _global_config_manager.add_predefined_configs()
    return _global_config_manager


def get_predefined_config(config_name: str) -> Optional[SyncJobConfig]:
    """Get a predefined configuration by name.
    
    Args:
        config_name: Name of the predefined configuration
        
    Returns:
        Configuration or None if not found
    """
    config_manager = get_global_config_manager()
    return config_manager.get_config(config_name)


def create_quick_sync_setup(
    enable_consistency: bool = True,
    enable_incremental: bool = True,
    enable_full_sync: bool = False,
    custom_intervals: Optional[Dict[str, int]] = None
) -> List[SyncJobConfig]:
    """Create a quick setup of common sync configurations.
    
    Args:
        enable_consistency: Enable consistency validation
        enable_incremental: Enable incremental synchronization
        enable_full_sync: Enable full synchronization
        custom_intervals: Custom intervals for specific job types
        
    Returns:
        List of job configurations
    """
    configs = []
    custom_intervals = custom_intervals or {}
    
    if enable_consistency:
        config = DEFAULT_CONSISTENCY_JOB_CONFIG
        if 'consistency' in custom_intervals:
            config = SyncJobConfig(
                job_id=config.job_id,
                job_type=config.job_type,
                interval_seconds=custom_intervals['consistency'],
                enabled=config.enabled,
                trigger_types=config.trigger_types,
                priority=config.priority,
                max_retries=config.max_retries,
                retry_delay_seconds=config.retry_delay_seconds,
                timeout_seconds=config.timeout_seconds
            )
        configs.append(config)
    
    if enable_incremental:
        config = DEFAULT_INCREMENTAL_SYNC_JOB_CONFIG
        if 'incremental' in custom_intervals:
            config = SyncJobConfig(
                job_id=config.job_id,
                job_type=config.job_type,
                interval_seconds=custom_intervals['incremental'],
                enabled=config.enabled,
                trigger_types=config.trigger_types,
                entity_types=config.entity_types,
                priority=config.priority,
                max_retries=config.max_retries,
                retry_delay_seconds=config.retry_delay_seconds,
                timeout_seconds=config.timeout_seconds
            )
        configs.append(config)
    
    if enable_full_sync:
        config = DEFAULT_FULL_SYNC_JOB_CONFIG
        if 'full_sync' in custom_intervals:
            config = SyncJobConfig(
                job_id=config.job_id,
                job_type=config.job_type,
                interval_seconds=custom_intervals['full_sync'],
                enabled=config.enabled,
                trigger_types=config.trigger_types,
                entity_types=config.entity_types,
                priority=config.priority,
                max_retries=config.max_retries,
                retry_delay_seconds=config.retry_delay_seconds,
                timeout_seconds=config.timeout_seconds
            )
        configs.append(config)
    
    return configs
