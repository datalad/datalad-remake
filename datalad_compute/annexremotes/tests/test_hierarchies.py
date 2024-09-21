
from datalad.api import get as datalad_get
from datalad_next.runners import call_git_success
from datalad_next.tests.fixtures import datalad_cfg

from ... import (
    template_dir,
    url_scheme,
)
from ...test_utils.create_datasets import create_ds_hierarchy


test_method = """
inputs = ['first', 'second', 'third']
use_shell = 'true'
executable = 'echo'
arguments = [
    "content: {first} > 'a.txt';",
    "echo content: {second} > 'b.txt';",
    "echo content: {third} > 'new.txt';",
    "echo content: {first} > 'subds0/a0.txt';",
    "echo content: {second} > 'subds0/b0.txt';",
    "echo content: {third} > 'subds0/new.txt';",
    "echo content: {first} > 'subds0/subds1/a1.txt';",
    "echo content: {second} > 'subds0/subds1/b1.txt';",
    "echo content: {third} > 'subds0/subds1/new.txt';",
    "echo content: {first} > 'subds0/subds1/subds2/a2.txt';",
    "echo content: {second} > 'subds0/subds1/subds2/b2.txt';",
    "echo content: {third} > 'subds0/subds1/subds2/new.txt';",
]
"""


output = [
    'a.txt', 'b.txt', 'new.txt',
    'subds0/a0.txt', 'subds0/b0.txt', 'subds0/new.txt',
    'subds0/subds1/a1.txt', 'subds0/subds1/b1.txt', 'subds0/subds1/new.txt',
    'subds0/subds1/subds2/a2.txt', 'subds0/subds1/subds2/b2.txt', 'subds0/subds1/subds2/new.txt',
]


def test_end_to_end(tmp_path, datalad_cfg, monkeypatch):

    datasets = create_ds_hierarchy(str(tmp_path), 3)
    root_dataset = datasets[0][0]

    # add method template
    template_path = root_dataset.pathobj / template_dir
    template_path.mkdir(parents=True)
    (template_path / 'test_method').write_text(test_method)
    root_dataset.save(result_renderer='disabled')

    # set annex security related variables to allow compute-URLs
    datalad_cfg.set('annex.security.allowed-url-schemes', url_scheme, scope='global')
    datalad_cfg.set('annex.security.allowed-ip-addresses', 'all', scope='global')
    datalad_cfg.set('annex.security.allow-unverified-downloads', 'ACKTHPPT', scope='global')

    # add a compute remotes to all datasets
    for _, dataset_path, _ in datasets:
        call_git_success([
            '-C', str(dataset_path),
            'annex', 'initremote', 'compute',
            'type=external', 'externaltype=compute',
            'encryption=none'])

    # run compute command
    root_dataset.compute(
        template='test_method',
        parameter=[
            'first=first',
            'second=second',
            'third=third',
        ],
        output=output)

    # check computation success
    for file, content in zip(output, ['first', 'second', 'third'] * 4):
        assert (root_dataset.pathobj / file).read_text() == f'content: {content}\n'

    # Drop all computed content
    for file in output:
        root_dataset.drop(file)

    # check that all files are dropped
    for file in output:
        assert not (root_dataset.pathobj / file).exists()

    # Go to the subdataset `subds0/subds1` and fetch the content of `a1.txt`
    # from a compute remote.
    monkeypatch.chdir(root_dataset.pathobj / 'subds0' / 'subds1')
    datalad_get('a1.txt')

    # check that all files are calculated
    for file, content in zip(output, ['first', 'second', 'third'] * 4):
        assert (root_dataset.pathobj / file).read_text() == f'content: {content}\n'

    # Drop all computed content
    for file in output:
        root_dataset.drop(file)

    monkeypatch.chdir(root_dataset.pathobj)
    datalad_get('subds0/subds1/a1.txt')

    # check that all files are calculated
    for file, content in zip(output, ['first', 'second', 'third'] * 4):
        assert (root_dataset.pathobj / file).read_text() == f'content: {content}\n'
