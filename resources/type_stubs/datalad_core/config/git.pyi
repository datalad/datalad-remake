import abc
from _typeshed import Incomplete
from collections.abc import Hashable
from datalad_core.config.item import ConfigItem as ConfigItem
from datalad_core.consts import DATALAD_BRANCH_CONFIG_RELPATH as DATALAD_BRANCH_CONFIG_RELPATH
from datalad_core.runners import CommandError as CommandError, call_git as call_git, call_git_oneline as call_git_oneline, iter_git_subproc as iter_git_subproc
from datasalad.settings import CachingSource, Setting as Setting
from os import PathLike

lgr: Incomplete

class GitConfig(CachingSource, metaclass=abc.ABCMeta):
    def __init__(self) -> None: ...
    def __contains__(self, key: Hashable) -> bool: ...

class SystemGitConfig(GitConfig): ...
class GlobalGitConfig(GitConfig): ...

class LocalGitConfig(GitConfig):
    def __init__(self, path: PathLike) -> None: ...

class WorktreeGitConfig(GitConfig):
    def __init__(self, path: PathLike) -> None: ...

class DataladBranchConfig(LocalGitConfig):
    def __init__(self, path: PathLike) -> None: ...
    @property
    def is_writable(self): ...

cfg_k_regex: Incomplete
cfg_kv_regex: Incomplete
