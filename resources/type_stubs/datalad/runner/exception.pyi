import os
from _typeshed import Incomplete
from typing import Any

lgr: Incomplete

class CommandError(RuntimeError):
    cmd: Incomplete
    msg: Incomplete
    code: Incomplete
    stdout: Incomplete
    stderr: Incomplete
    cwd: Incomplete
    kwargs: Incomplete
    def __init__(self, cmd: str | list[str] = '', msg: str = '', code: int | None = None, stdout: str | bytes = '', stderr: str | bytes = '', cwd: str | os.PathLike | None = None, **kwargs: Any) -> None: ...
    def to_str(self, include_output: bool = True) -> str: ...
