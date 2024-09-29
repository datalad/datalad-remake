from collections.abc import Iterable

from datalad.api import get as datalad_get
from datalad_next.datasets import Dataset
from datalad_next.tests.fixtures import datalad_cfg

from ... import (
    template_dir,
    url_scheme,
)
from datalad_compute.dataprovider.tests.create_datasets import create_ds_hierarchy


test_method = """
inputs = ['first', 'second', 'third']
use_shell = 'true'
executable = 'echo'
arguments = [
    "content: {first} > 'a.txt';",
    "mkdir -p 'd2_subds0/d2_subds1/d2_subds2';",
    "echo content: {second} > 'b.txt';",
    "echo content: {third} > 'new.txt';",
    "echo content: {first} > 'd2_subds0/a0.txt';",
    "echo content: {second} > 'd2_subds0/b0.txt';",
    "echo content: {third} > 'd2_subds0/new.txt';",
    "echo content: {first} > 'd2_subds0/d2_subds1/a1.txt';",
    "echo content: {second} > 'd2_subds0/d2_subds1/b1.txt';",
    "echo content: {third} > 'd2_subds0/d2_subds1/new.txt';",
    "echo content: {first} > 'd2_subds0/d2_subds1/d2_subds2/a2.txt';",
    "echo content: {second} > 'd2_subds0/d2_subds1/d2_subds2/b2.txt';",
    "echo content: {third} > 'd2_subds0/d2_subds1/d2_subds2/new.txt';",
]
"""


output = [
    'a.txt', 'b.txt', 'new.txt',
    'd2_subds0/a0.txt', 'd2_subds0/b0.txt', 'd2_subds0/new.txt',
    'd2_subds0/d2_subds1/a1.txt', 'd2_subds0/d2_subds1/b1.txt', 'd2_subds0/d2_subds1/new.txt',
    'd2_subds0/d2_subds1/d2_subds2/a2.txt', 'd2_subds0/d2_subds1/d2_subds2/b2.txt', 'd2_subds0/d2_subds1/d2_subds2/new.txt',
]

test_file_content = [
    (file, content)
    for file, content in
    zip(output, ['content: first\n', 'content: second\n', 'content: third\n'] * 4)
]


def _drop_files(dataset: Dataset,
                files: Iterable[str]):
    for file in files:
        dataset.drop(file, result_renderer='disabled')
        assert not (dataset.pathobj / file).exists()


def _check_content(dataset,
                   file_content: Iterable[tuple[str, str]]
                   ):
    for file, content in file_content:
        assert (dataset.pathobj / file).read_text() == content


def test_end_to_end(tmp_path, datalad_cfg, monkeypatch):

    datasets = create_ds_hierarchy(tmp_path, 'd2', 3)
    root_dataset = datasets[0][2]

    # add method template
    template_path = root_dataset.pathobj / template_dir
    template_path.mkdir(parents=True)
    (template_path / 'test_method').write_text(test_method)
    root_dataset.save(result_renderer='disabled')

    # set annex security related variables to allow compute-URLs
    datalad_cfg.set('annex.security.allowed-url-schemes', url_scheme, scope='global')
    datalad_cfg.set('annex.security.allowed-ip-addresses', 'all', scope='global')
    datalad_cfg.set('annex.security.allow-unverified-downloads', 'ACKTHPPT', scope='global')

    # run compute command
    root_dataset.compute(
        template='test_method',
        parameter=[
            'first=first',
            'second=second',
            'third=third',
        ],
        output=output,
        result_renderer='disabled')

    # check computation success
    _check_content(root_dataset, test_file_content)

    # Drop all computed content
    _drop_files(root_dataset, output)

    # Go to the subdataset `d2_subds0/d2_subds1` and fetch the content of `a1.txt`
    # from a compute remote.
    monkeypatch.chdir(root_dataset.pathobj / 'd2_subds0' / 'd2_subds1')
    datalad_get('a1.txt')

    # check that all files are computed
    _check_content(root_dataset, test_file_content)

    _drop_files(root_dataset, output)

    # check get in subdatasets
    monkeypatch.chdir(root_dataset.pathobj)
    datalad_get('d2_subds0/d2_subds1/a1.txt')

    _check_content(root_dataset, test_file_content)
