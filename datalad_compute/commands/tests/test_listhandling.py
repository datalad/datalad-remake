import tempfile
from pathlib import Path
from datalad_compute.commands.compute_cmd import read_list

from hypothesis import given
from hypothesis.strategies import lists, text


def test_empty_list_reading():
    assert read_list(None) == []


@given(lists(text('abcdefghijklmnopqrstuvwxyz _', min_size=1)))
def test_list_reading(word_list):
    with tempfile.TemporaryDirectory() as temp_dir:
        _test_wordlist(Path(temp_dir), word_list)


def _test_wordlist(tmp_path: Path,
                   word_list: list[str],
                   ) -> None:
    list_file = tmp_path / 'list.txt'
    list_file.write_text('\n'.join(word_list))
    assert read_list(str(list_file)) == word_list
    assert read_list(list_file) == word_list
