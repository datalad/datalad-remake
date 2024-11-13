from __future__ import annotations

import sys
from glob import glob as system_glob
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING

from datalad_remake.utils.chdir import chdir

if TYPE_CHECKING:
    from collections.abc import Iterable


# Resolve input file patterns in the original dataset
def resolve_patterns(root_dir: str | Path, patterns: Iterable[str]) -> set[str]:
    return set(
        filter(
            lambda p: not (Path(root_dir) / p).is_dir(),
            chain.from_iterable(
                glob(pattern, root_dir=str(root_dir), recursive=True)
                for pattern in patterns
            ),
        )
    )


# Support kwarg `root_dir` in `glob` in python version < 3.10. If the minimal
# supported version is 3.11, the following code and its imports should be
# removed
if (3, 0) < sys.version_info < (3, 10):

    def glob(pathname, *, root_dir=None, dir_fd=None, recursive=False):
        if dir_fd is not None:
            msg = 'dir_fd is not supported'
            raise ValueError(msg)
        if root_dir is not None:
            if not Path(root_dir).is_dir():
                return []
            with chdir(root_dir):
                return system_glob(pathname, recursive=recursive)
        else:
            return system_glob(pathname, recursive=recursive)
else:
    glob = system_glob
