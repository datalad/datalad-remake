from collections.abc import Generator, Hashable
from datalad_core.config.item import ConfigItem as ConfigItem
from datalad_core.config.utils import get_gitconfig_items_from_env as get_gitconfig_items_from_env, set_gitconfig_items_in_env as set_gitconfig_items_in_env
from datasalad.settings import Setting as Setting, WritableMultivalueSource

class GitEnvironment(WritableMultivalueSource):
    item_type = ConfigItem
    def overrides(self, overrides: dict[Hashable, Setting | tuple[Setting, ...]]) -> Generator[None]: ...
