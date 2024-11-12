from pathlib import Path

from datalad_remake.commands.tests.create_datasets import (
    create_simple_computation_dataset,
)

template = """
parameters = ['line']

use_shell = 'true'

command = ["echo {line} >> 'a.txt'"]
"""


def test_input_is_output(tmp_path: Path):
    root_dataset = create_simple_computation_dataset(tmp_path, 'ds1', 0, template)

    line = 'the second line'
    root_dataset.make(
        template='test_method',
        parameter=[f'line={line}'],
        input=['a.txt'],
        output=['a.txt'],
        result_renderer='disabled',
        allow_untrusted_execution=True,
    )

    # check that the output is correct
    assert (root_dataset.pathobj / 'a.txt').read_text() == f'a\n{line}\n'

    # check that get works
    root_dataset.drop('a.txt', result_renderer='disabled')
    assert (root_dataset.pathobj / 'a.txt').exists() is False

    root_dataset.get('a.txt', result_renderer='disabled')
    assert (root_dataset.pathobj / 'a.txt').exists()
    assert (root_dataset.pathobj / 'a.txt').read_text() == f'a\n{line}\n'
