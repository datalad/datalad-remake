from annexremote import UnsupportedRequest as UnsupportedRequest
from annexremote import main as super_main
from datalad.customremotes import RemoteError as RemoteError, SpecialRemote as _SpecialRemote
from datalad_next.datasets import LeanAnnexRepo as LeanAnnexRepo
from typing import Any

__all__ = ['super_main', 'SpecialRemote']

class SpecialRemote(_SpecialRemote):
    def __init__(self, annex) -> None: ...
    @property
    def repo(self) -> LeanAnnexRepo: ...
    @property
    def remotename(self) -> str: ...
    def get_remote_gitcfg(self, remotetypename: str, name: str, default: Any | None = None, **kwargs): ...
