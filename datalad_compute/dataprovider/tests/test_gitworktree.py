from __future__ import annotations

from contextlib import chdir
from pathlib import Path
from typing import Iterable

from datalad_next.datasets import Dataset
from datalad_next.runners import call_git_lines


from ..gitworktree import (
    provide,
    remove,
)
from .create_datasets import create_ds_hierarchy


file_path_templates = [
    '{file}.txt',
    '{{ds_name}}_subds0/{file}0.txt',
    '{{ds_name}}_subds0/{{ds_name}}_subds1/{file}1.txt',
    '{{ds_name}}_subds0/{{ds_name}}_subds1/{{ds_name}}_subds2/{file}2.txt',
]


all_paths = [
    template.format(file=f)
    for template in file_path_templates
    for f in ['a', 'b']
]

a_paths = [
    path.format(file='a')
    for path in file_path_templates
]

b_paths = [
    path.format(file='b')
    for path in file_path_templates
]

all_paths = a_paths + b_paths


def test_worktree_basic(tmp_path):
    dataset = create_ds_hierarchy(tmp_path, 'ds1', 3)[0][2]
    worktree = Dataset(provide(
        dataset.path,
        str(tmp_path),
        input_patterns=[
            'a.txt', 'b.txt',
            'ds1_subds0/a0.txt', 'ds1_subds0/b0.txt',
            'ds1_subds0/ds1_subds1/a1.txt', 'ds1_subds0/ds1_subds1/b1.txt'
        ],
    ))

    r_orig = [r['gitmodule_url'] for r in dataset.subdatasets(recursive=True, result_renderer='disabled')]
    r_worktree = [r['gitmodule_url'] for r in worktree.subdatasets(recursive=True, result_renderer='disabled')]
    assert r_orig == r_worktree

    remove(dataset.path, worktree.path)

    def check_deleted_worktrees(ds: Dataset):
        with chdir(ds.path):
            for line in call_git_lines(['worktree', 'list']):
                directory = line.split()[0]
                assert directory == ds.path
        for sub_ds in ds.subdatasets(result_renderer='disabled'):
            check_deleted_worktrees(Dataset(sub_ds['path']))

    check_deleted_worktrees(dataset)
    dataset.drop(
        what='all',
        reckless='kill',
        recursive=True,
        result_renderer='disabled')


def test_worktree_globbing(tmp_path):
    dataset = create_ds_hierarchy(tmp_path, 'ds1', 3)[0][2]
    worktree = Dataset(provide(
        dataset.path,
        str(tmp_path),
        input_patterns=[
            '*.txt',
            '*_subds0/*.txt',
            '*_subds0/*_subds1/*.txt',
            '*_subds0/*_subds1/*_subds2/*.txt',
        ],
    ))

    worktree_set = set(get_file_list(worktree.pathobj))
    assert worktree_set == set(
        path.format(ds_name='ds1')
        for path in all_paths
    )
    remove(dataset.path, worktree.path)

    worktree = Dataset(provide(
        dataset.path,
        str(tmp_path),
        input_patterns=[
            'b*txt',
            '*_subds0/b*txt',
            '*_subds0/*_subds1/b*txt',
            '*_subds0/*_subds1/*_subds2/b*txt',
        ],
    ))

    worktree_set = set(get_file_list(worktree.pathobj))
    assert set(
        path.format(ds_name='ds1')
        for path in b_paths
    ).issubset(worktree_set)
    remove(dataset.path, worktree.path)

    dataset.drop(
        what='all',
        reckless='kill',
        recursive=True,
        result_renderer='disabled')


def get_file_list(root: Path,
                  path: Path|None = None,
                  prefix: Path|None = None
                  ) -> Iterable[str]:
    prefix = prefix or Path('')
    path = path or root
    for child in path.iterdir():
        if not child.name.startswith('.'):
            if child.is_dir():
                yield from get_file_list(root, child, prefix=prefix / child)
            else:
                yield str((prefix / child).relative_to(root))
