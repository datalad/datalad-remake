"""This module unifies the use of `load` from `toml` and `tomllib`

The module and its application can be removed in favor of `tomllib`, if
the minimal supported python version is 3.11
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


if (3, 0) < sys.version_info < (3, 11):
    import toml

    def toml_load(path: Path) -> dict:
        with open(path) as file:
            return toml.load(file)
else:
    import tomllib

    def toml_load(path: Path) -> dict:
        with open(path, 'rb') as file:
            return tomllib.load(file)
