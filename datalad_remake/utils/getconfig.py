from __future__ import annotations

from datalad_core.config import (
    ConfigManager,
    get_manager,
)

from datalad_remake import (
    allow_untrusted_execution_key,
    trusted_keys_config_key,
)


def get_trusted_keys(config_manager: ConfigManager | None = None) -> list[str]:
    value = get_protected_config(trusted_keys_config_key, config_manager)
    if value is None:
        return []
    return [key.strip() for key in value.split(',')]


def get_allow_untrusted_execution(
    dataset_id: str,
    config_manager: ConfigManager | None = None
) -> bool:
    """Get an allow-untrusted-execution indicator for a dataset."""
    value = get_protected_config(
        allow_untrusted_execution_key + dataset_id,
        config_manager,
    )
    return value == 'true'


def get_protected_config(
    config_key: str,
    config_manager: ConfigManager | None = None
) -> str:
    if config_manager is None:
        config_manager = get_manager()
    return config_manager.get_from_protected_sources(config_key).value
