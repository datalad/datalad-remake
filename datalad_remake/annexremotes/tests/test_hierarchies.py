from collections.abc import Iterable
from pathlib import Path

import pytest
from datalad_core.config import ConfigItem
from datalad_core.tests.fixtures import cfgman  # noqa: F401
from datalad.distribution.get import Get as datalad_Get
from datalad_next.datasets import Dataset
from datalad_next.tests import skip_if_on_windows

from datalad_remake import allow_untrusted_execution_key
from datalad_remake.commands.tests.create_datasets import (
    create_simple_computation_dataset,
)

script = (
    "echo content: {first} > 'a.txt';"
    "mkdir -p 'd2_subds0/d2_subds1/d2_subds2';"
    "echo content: {second} > 'b.txt';"
    "echo content: {third} > 'new.txt';"
    "echo content: {first} > 'd2_subds0/a0.txt';"
    "echo content: {second} > 'd2_subds0/b0.txt';"
    "echo content: {third} > 'd2_subds0/new.txt';"
    "echo content: {first} > 'd2_subds0/d2_subds1/a1.txt';"
    "echo content: {second} > 'd2_subds0/d2_subds1/b1.txt';"
    "echo content: {third} > 'd2_subds0/d2_subds1/new.txt';"
    "echo content: {first} > 'd2_subds0/d2_subds1/d2_subds2/a2.txt';"
    "echo content: {second} > 'd2_subds0/d2_subds1/d2_subds2/b2.txt';"
    "echo content: {third} > 'd2_subds0/d2_subds1/d2_subds2/new.txt'"
)

test_method = '\n'.join(
    [
        "parameters = ['first', 'second', 'third']",
        'command = ["bash", "-c", "' + script + '"]',
    ]
)

output_pattern_static = [
    'a.txt',
    'b.txt',
    'new.txt',
    'd2_subds0/a0.txt',
    'd2_subds0/b0.txt',
    'd2_subds0/new.txt',
    'd2_subds0/d2_subds1/a1.txt',
    'd2_subds0/d2_subds1/b1.txt',
    'd2_subds0/d2_subds1/new.txt',
    'd2_subds0/d2_subds1/d2_subds2/a2.txt',
    'd2_subds0/d2_subds1/d2_subds2/b2.txt',
    'd2_subds0/d2_subds1/d2_subds2/new.txt',
]


output_pattern_glob = [
    '*.txt',
    'd2_subds0/*.txt',
    'd2_subds0/d2_subds1/*.txt',
    'd2_subds0/d2_subds1/d2_subds2/*.txt',
]


test_file_content = list(
    zip(  # noqa: B905, remove this comment when the minimum python version is 3.10
        output_pattern_static,
        ['content: first\n', 'content: second\n', 'content: third\n'] * 4,
    )
)


def _drop_files(dataset: Dataset, files: Iterable[str]):
    for file in files:
        dataset.drop(file, reckless='availability', result_renderer='disabled')
        assert not (dataset.pathobj / file).exists()


def _check_content(dataset, file_content: Iterable[tuple[str, str]]):
    for file, content in file_content:
        assert (dataset.pathobj / file).read_text() == content


@skip_if_on_windows
@pytest.mark.parametrize('output_pattern', [output_pattern_static, output_pattern_glob])
def test_end_to_end(tmp_path, cfgman, monkeypatch, output_pattern):
    root_dataset = create_simple_computation_dataset(tmp_path, 'd2', 3, test_method)

    # run `make` command
    results = root_dataset.make(
        template='test_method',
        parameter=[
            'first=first',
            'second=second',
            'third=third',
        ],
        output=output_pattern,
        result_renderer='disabled',
        allow_untrusted_execution=True,
    )

    collected_output = [
        str(Path(result['path']).relative_to(root_dataset.pathobj))
        for result in results
    ]
    assert set(collected_output) == set(output_pattern_static)

    # check computation success
    _check_content(root_dataset, test_file_content)

    # Go to the subdataset `d2_subds0/d2_subds1` and fetch the content of `a1.txt`
    # from a datalad-remake remote.
    with cfgman.overrides(
        {
            # Allow the special remote to execute untrusted operations on the
            # dataset `root_dataset/d2_subds0/d2_subds1`
            allow_untrusted_execution_key
            + Dataset(root_dataset.pathobj / 'd2_subds0' / 'd2_subds1').id: ConfigItem('true'),
        }
    ):
        # Drop all computed content
        _drop_files(root_dataset, collected_output)

        monkeypatch.chdir(root_dataset.pathobj / 'd2_subds0' / 'd2_subds1')
        datalad_Get()('a1.txt')
        # check that all known files that were computed are added to the annex
        _check_content(root_dataset, test_file_content)

        _drop_files(root_dataset, collected_output)

        monkeypatch.chdir(root_dataset.pathobj)
        datalad_Get()('d2_subds0/d2_subds1/a1.txt')
        _check_content(root_dataset, test_file_content)
