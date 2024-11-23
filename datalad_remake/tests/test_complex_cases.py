from pathlib import Path

from datalad_remake import template_dir
from datalad_remake.commands.tests.create_datasets import (
    create_simple_computation_dataset,
)

template = """
parameters = ['line']
command = ["bash", "-c", "echo {line} >> 'a.txt'"]
"""

template_c1 = """
parameters = ['line']
command = ["bash", "-c", "cat a.txt > c1.txt;  echo {line} >> c1.txt"]
"""

template_c2 = """
parameters = ['line']
command = ["bash", "-c", "cat c1.txt > c2.txt; echo {line} >> c2.txt"]
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


def test_chain_dependency(tmp_path: Path):
    # c2.txt -> c1.txt -> a.txt
    # Create a simple dataset that can create c1.txt from a.txt
    root_dataset = create_simple_computation_dataset(
        tmp_path, 'ds1', 0, template_c1, 'create_c1'
    )

    # add method that can create c2.txt from c1.txt
    (root_dataset.pathobj / template_dir / 'create_c2').write_text(template_c2)
    root_dataset.save(result_renderer='disabled')

    # Create c1.txt
    c1_line = 'the second line'
    root_dataset.make(
        template='create_c1',
        parameter=[f'line={c1_line}'],
        input=['a.txt'],
        output=['c1.txt'],
        result_renderer='disabled',
        allow_untrusted_execution=True,
    )

    # Create c2.txt
    c2_line = 'the third line'
    root_dataset.make(
        template='create_c2',
        parameter=[f'line={c2_line}'],
        input=['c1.txt'],
        output=['c2.txt'],
        result_renderer='disabled',
        allow_untrusted_execution=True,
    )

    # check that the output is correct
    assert (root_dataset.pathobj / 'c1.txt').read_text() == f'a\n{c1_line}\n'
    assert (root_dataset.pathobj / 'c2.txt').read_text() == f'a\n{c1_line}\n{c2_line}\n'

    # drop c1.txt and c2.txt and check that get c2.works
    for file in ['c1.txt', 'c2.txt']:
        root_dataset.drop(file, result_renderer='disabled')
        assert (root_dataset.pathobj / file).exists() is False

    root_dataset.get('c2.txt', result_renderer='disabled')
    assert (root_dataset.pathobj / 'c2.txt').read_text() == f'a\n{c1_line}\n{c2_line}\n'
