from __future__ import annotations

from glob import glob
from itertools import chain
from pathlib import Path
from typing import Iterable


# Resolve input file patterns in the original dataset
def resolve_patterns(root_dir: str | Path,
                     patterns: Iterable[str]
                     ) -> set[str]:
    return set(
        chain.from_iterable(
            glob(pattern, root_dir=str(root_dir), recursive=True)
            for pattern in patterns))
