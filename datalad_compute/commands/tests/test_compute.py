from typing import Iterable

from datalad_next.datasets import Dataset
from datalad_next.tests.fixtures import datalad_cfg

from ... import template_dir
from datalad_compute.commands.tests.create_datasets import create_ds_hierarchy


test_method = """
inputs = ['name', 'file']
use_shell = 'true'
executable = 'echo'
arguments = ["Hello {name} > {file}"]
"""


output_pattern = ['a.txt']


def _drop_files(dataset: Dataset,
                files: Iterable[str]):
    for file in files:
        dataset.drop(file, reckless='availability', result_renderer='disabled')
        assert not (dataset.pathobj / file).exists()


def _check_content(dataset,
                   file_content: Iterable[tuple[str, str]]
                   ):
    for file, content in file_content:
        assert (dataset.pathobj / file).read_text() == content


def test_duplicated_computation(tmp_path, datalad_cfg, monkeypatch):

    datasets = create_ds_hierarchy(tmp_path, 'd1', 0)
    root_dataset = datasets[0][2]

    # add method template
    template_path = root_dataset.pathobj / template_dir
    template_path.mkdir(parents=True)
    (template_path / 'test_method').write_text(test_method)
    root_dataset.save(result_renderer='disabled')

    # run the same command twice
    _run_simple_computation(root_dataset)
    _run_simple_computation(root_dataset)


def test_speculative_computation(tmp_path, datalad_cfg, monkeypatch):

    datasets = create_ds_hierarchy(tmp_path, 'd2', 0)
    root_dataset = datasets[0][2]

    # add method template
    template_path = root_dataset.pathobj / template_dir
    template_path.mkdir(parents=True)
    (template_path / 'test_method').write_text(test_method)
    root_dataset.save(result_renderer='disabled')

    root_dataset.compute(
        template='test_method',
        parameter=['name=Robert', 'file=spec.txt'],
        output=['spec.txt'],
        url_only=True,
        result_renderer='disabled')

    # set annex security related variables to allow compute-URLs
    datalad_cfg.set('annex.security.allow-unverified-downloads', 'ACKTHPPT', scope='global')

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
