from datalad_next.datasets import Dataset
from datalad_next.tests.fixtures import datalad_cfg

from datalad_compute.commands.tests.create_datasets import (
    create_simple_computation_dataset,
)


test_method = """
inputs = ['name', 'file']
use_shell = 'true'
executable = 'echo'
arguments = ["Hello {name} > {file}"]
"""

output_pattern = ['a.txt']


def test_duplicated_computation(tmp_path, datalad_cfg, monkeypatch):

    root_dataset = create_simple_computation_dataset(
        tmp_path, 'ds1', 0, test_method)

    # run the same command twice
    _run_simple_computation(root_dataset)
    _run_simple_computation(root_dataset)


def test_speculative_computation(tmp_path, datalad_cfg, monkeypatch):

    root_dataset = create_simple_computation_dataset(
        tmp_path, 'ds1', 0, test_method)

    root_dataset.compute(
        template='test_method',
        parameter=['name=Robert', 'file=spec.txt'],
        output=['spec.txt'],
        url_only=True,
        result_renderer='disabled')

    # set annex security related variables to allow compute-URLs
    datalad_cfg.set('annex.security.allow-unverified-downloads', 'ACKTHPPT', scope='global')

    # Perform the speculative computation
    root_dataset.get('spec.txt')
    assert (root_dataset.pathobj / 'spec.txt').read_text() == 'Hello Robert\n'


def _run_simple_computation(root_dataset: Dataset):
    root_dataset.compute(
        template='test_method',
        parameter=['name=Robert', 'file=a.txt'],
        output=['a.txt'],
        result_renderer='disabled')

    # check that the output is correct
    assert (root_dataset.pathobj / 'a.txt').read_text() == 'Hello Robert\n'
