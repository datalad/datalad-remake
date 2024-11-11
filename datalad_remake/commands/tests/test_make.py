from datalad_next.datasets import Dataset
from datalad_next.tests import skip_if_on_windows

from datalad_remake.commands.tests.create_datasets import (
    create_simple_computation_dataset,
)

test_method = """
parameters = ['name', 'file']
use_shell = 'true'
command = ["echo Hello {name} > {file}"]
"""

output_pattern = ['a.txt']


@skip_if_on_windows
def test_duplicated_computation(tmp_path):
    root_dataset = create_simple_computation_dataset(tmp_path, 'ds1', 0, test_method)

    # run the same command twice
    _run_simple_computation(root_dataset)
    _run_simple_computation(root_dataset)


@skip_if_on_windows
def test_speculative_computation(tmp_path, datalad_cfg):
    root_dataset = create_simple_computation_dataset(tmp_path, 'ds1', 0, test_method)

    root_dataset.make(
        template='test_method',
        parameter=['name=Robert', 'file=spec.txt'],
        output=['spec.txt'],
        prospective_execution=True,
        result_renderer='disabled',
    )

    # set annex security related variables to allow datalad-remake-URLs
    # in speculative make commands
    datalad_cfg.set(
        'annex.security.allow-unverified-downloads', 'ACKTHPPT', scope='global'
    )

    # Perform the speculative computation
    root_dataset.get('spec.txt', result_renderer='disabled')
    assert (root_dataset.pathobj / 'spec.txt').read_text() == 'Hello Robert\n'


def _run_simple_computation(root_dataset: Dataset):
    root_dataset.make(
        template='test_method',
        parameter=['name=Robert', 'file=a.txt'],
        output=['a.txt'],
        result_renderer='disabled',
        allow_untrusted_execution=True,
    )

    # check that the output is correct
    assert (root_dataset.pathobj / 'a.txt').read_text() == 'Hello Robert\n'
