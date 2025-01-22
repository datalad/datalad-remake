from __future__ import annotations

import logging
from pathlib import PurePosixPath

lgr = logging.getLogger('datalad.remake')


class PatternPath(PurePosixPath):
    def __new__(cls, *args):
        pattern_path = PurePosixPath(*args)
        PatternPath.validate(pattern_path)
        return pattern_path

    @staticmethod
    def validate(path):
        if path.is_absolute():
            msg = f'PatternPath must be relative, got {path}'
            raise ValueError(msg)
        if '\\' in str(path):
            forward_str = str(path).replace('\\', '/')
            lgr.warning(
                f'PatternPath contains backslashes, did you mean `{forward_str}`?'
            )
