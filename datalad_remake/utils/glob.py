from __future__ import annotations

import sys
from glob import glob as system_glob
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING

from datalad_remake import PatternPath
from datalad_remake.utils.chdir import chdir

if TYPE_CHECKING:
    from collections.abc import Iterable


# Resolve input file patterns in the original dataset
def resolve_patterns(
    root_dir: str | Path,
    patterns: Iterable[PatternPath],
    *,
    recursive: bool = True,
) -> set[PatternPath]:
    return set(
        map(
            PatternPath,
            filter(
                # This expression works because a `PatternPath` instance can be
                # safely appended to a system path via `/`. The result is a system
                # path where the last parts are the parts of the `PatternPath`
                # instance.
                lambda p: not (Path(root_dir) / p).is_dir(),
                chain.from_iterable(
                    glob(
                        # Convert `PatternPath` instance to a platform path and then
                        # to a string, which is required by the `glob` function.
                        str(Path(pattern)),
                        root_dir=root_dir,
                        recursive=recursive,
                    )
                    for pattern in patterns
                ),
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
