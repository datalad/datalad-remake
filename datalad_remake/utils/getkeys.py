from __future__ import annotations

from datalad_core.config import (
    ConfigManager,
    get_manager,
)

from datalad_remake import trusted_keys_config_key


def get_trusted_keys(config_manager: ConfigManager | None = None) -> list[str]:
    if config_manager is None:
        config_manager = get_manager()

    trusted_key_items = config_manager.get_from_protected_sources(
        trusted_keys_config_key
    )
    if trusted_key_items.value is None:
        return []
    return [key.strip() for key in trusted_key_items.value.split(',')]
