from __future__ import annotations

from pathlib import Path


def read_list(list_file: str | Path | None) -> list[str]:
    if list_file is None:
        return []
    return list(
        filter(
            lambda s: s != '' and not s.startswith('#'),
            [
                line.strip()
                for line in Path(list_file).read_text().splitlines(keepends=False)
            ],
        )
    )
