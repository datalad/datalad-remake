from __future__ import annotations

import tempfile
from contextlib import chdir

from datalad_next.datasets import Dataset
from datalad_next.runners import call_git_lines

from ..gitworktree import (
    provide,
    remove,
)


def create_subdatasets(parent_dataset: Dataset,
                       subdataset_levels: int = 2,
                       level_id: int = 0,
                       ):
    if subdataset_levels == 0:
        return

    subdataset = Dataset(parent_dataset.pathobj / f'subds{level_id}')
    subdataset.create(result_renderer='disabled')
    create_subdatasets(subdataset, subdataset_levels - 1, level_id + 1)
    (subdataset.pathobj / f'a{level_id}.txt').write_text(f'a{level_id}')
    (subdataset.pathobj / f'b{level_id}.txt').write_text(f'b{level_id}')
    subdataset.save(result_renderer='disabled')


def create_ds_hierarchy(subdataset_levels: int = 2):
    dataset = Dataset(tempfile.TemporaryDirectory().name)
    dataset.create(force=True, result_renderer='disabled')
    create_subdatasets(dataset, subdataset_levels)
    (dataset.pathobj / 'a.txt').write_text('a')
    (dataset.pathobj / 'b.txt').write_text('b')
    dataset.save(result_renderer='disabled')
    return dataset


def test_worktree_basic():
    dataset = create_ds_hierarchy(3)
    worktree = Dataset(provide(dataset.path))

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
    dataset.drop(reckless='kill', result_renderer='disabled')
