from .coreprotocols import NoCapture as NoCapture
from .exception import CommandError as CommandError
from .nonasyncrunner import ThreadedRunner as ThreadedRunner, _ResultGenerator
from .protocol import GeneratorMixIn as GeneratorMixIn, WitlessProtocol as WitlessProtocol
from _typeshed import Incomplete
from os import PathLike
from queue import Queue
from typing import IO

lgr: Incomplete

class WitlessRunner:
    env: Incomplete
    cwd: Incomplete
    def __init__(self, cwd: str | PathLike | None = None, env: dict | None = None) -> None: ...
    def run(self, cmd: list | str, protocol: type[WitlessProtocol] | None = None, stdin: bytes | IO | Queue | None = None, cwd: PathLike | str | None = None, env: dict | None = None, timeout: float | None = None, exception_on_error: bool = True, **kwargs) -> dict | _ResultGenerator: ...
