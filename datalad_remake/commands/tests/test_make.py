from unittest.mock import MagicMock
from urllib.parse import urlparse

from datalad_core.config import ConfigItem
from datalad_next.datasets import Dataset
from datalad_next.tests import skip_if_on_windows

import datalad_remake.commands.make_cmd
from datalad_remake import (
    PatternPath,
    allow_untrusted_execution_key,
)
from datalad_remake.commands.make_cmd import get_url
from datalad_remake.commands.tests.create_datasets import (
    create_simple_computation_dataset,
)

xtest_method = """
parameters = ['name', 'file']
command = ["echo", "Hello {name}" > {file}"]
"""

test_method = """
parameters = ['name', 'file']
command = ["pwsh", "-c", "Write-Output Hello {name} > {file}"]
"""


output_pattern = ['a.txt']


#@skip_if_on_windows
def test_duplicated_computation(tmp_path):
    root_dataset = create_simple_computation_dataset(tmp_path, 'ds1', 0, test_method)

    # run the same command twice
    _run_simple_computation(root_dataset)
    _run_simple_computation(root_dataset)


#@skip_if_on_windows
def test_speculative_computation(tmp_path, cfgman):
    root_dataset = create_simple_computation_dataset(tmp_path, 'ds1', 0, test_method)

    root_dataset.make(
        template='test_method',
        parameter=['name=Robert', 'file=spec.txt'],
        output=['spec.txt'],
        prospective_execution=True,
        result_renderer='disabled',
    )

    with cfgman.overrides(
        {
            # Allow the special remote to execute untrusted operations on this
            # dataset
            allow_untrusted_execution_key + root_dataset.id: ConfigItem('true'),
        }
    ):
        # Perform the speculative computation
        root_dataset.get('spec.txt', result_renderer='disabled')
    assert (root_dataset.pathobj / 'spec.txt').read_text() == 'Hello Robert\n'


def _run_simple_computation(root_dataset: Dataset):
    root_dataset.make(
        template='test_method',
        label='simple',
        parameter=['name=Robert', 'file=a.txt'],
        output=['a.txt'],
        result_renderer='disabled',
        allow_untrusted_execution=True,
    )

    # check that the output is correct
    assert (root_dataset.pathobj / 'a.txt').read_text() == 'Hello Robert\n'


def test_label_url(monkeypatch):
    root_dataset = MagicMock()
    root_dataset.repo.get_hexsha = lambda: b'1234'
    monkeypatch.setattr(
        datalad_remake.commands.make_cmd, 'write_spec', lambda *_: '4567'
    )
    url, _ = get_url(
        dataset=root_dataset,
        branch=None,
        template_name=test_method,
        parameters={'name': 'Robert', 'file': 'a.txt'},
        input_pattern=[PatternPath('a.txt')],
        output_pattern=[PatternPath('b.txt')],
        label='label1',
    )
    parts = urlparse(url).query.split('&')
    assert 'label=label1' in parts
