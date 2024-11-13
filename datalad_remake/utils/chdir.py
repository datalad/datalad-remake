"""This module implements a chdir context manager

The module can be removed when the minimal supported
python version is 3.11
"""

import contextlib
import sys
from pathlib import Path
from typing import (
    Any,
    cast,
)

__all__ = ['chdir']

if (3, 0) < sys.version_info < (3, 11):
    _dir_stack = []

    @contextlib.contextmanager
    def chdir(path: Path):
        import os

        _dir_stack.append(Path.cwd())
        os.chdir(path)
        try:
            yield
        finally:
            os.chdir(_dir_stack.pop())
else:
    chdir = cast(Any, contextlib.chdir)
