from __future__ import annotations

import pytest

from ..patternpath import PatternPath


def test_absolute_path():
    with pytest.raises(ValueError, match='PatternPath must be relative'):
        PatternPath('/absolute/path')


def test_backlash_path(monkeypatch):
    warnings = []

    def warning(message):
        warnings.append(message)

    monkeypatch.setattr('datalad_remake.utils.patternpath.lgr.warning', warning)
    PatternPath('a\\b')
    assert len(warnings) == 1
    assert 'a/b' in warnings[0]
