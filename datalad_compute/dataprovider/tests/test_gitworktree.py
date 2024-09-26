from __future__ import annotations

from contextlib import chdir

from datalad_next.datasets import Dataset
from datalad_next.runners import call_git_lines

from ..gitworktree import (
    provide,
    remove,
)
from .create_datasets import create_ds_hierarchy


def test_worktree_basic(tmp_path):
    dataset = create_ds_hierarchy(tmp_path, 'ds1', 3)[0][2]
    worktree = Dataset(provide(
        dataset.path,
        str(tmp_path),
        input_files=[
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
