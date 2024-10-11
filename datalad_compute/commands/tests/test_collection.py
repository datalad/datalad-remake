from pathlib import Path

from .create_datasets import create_ds_hierarchy
from .test_provision import get_file_list
from ..compute_cmd import collect


def test_collect(tmp_path):

    dataset = create_ds_hierarchy(tmp_path, 'ds1', 1)[0][2]

    worktree_dir = tmp_path / 'ds1_worktree'
    worktree_dir.mkdir(parents=True, exist_ok=False)
    worktree = dataset.provision(
        worktree_dir=worktree_dir,
        result_renderer='disabled')

    result_dir = worktree_dir / 'results' / 'sub-01'
    result_dir.mkdir(parents=True)
    (result_dir / 'a.txt').write_text('content: a\n')
    (result_dir / 'b.txt').write_text('content: b\n')

    result = collect(
        worktree=Path(worktree[0]['path']),
        dataset=dataset,
        output_pattern=['results/**']
    )
    assert result == {'results/sub-01/a.txt', 'results/sub-01/b.txt'}
    assert set(get_file_list(dataset.pathobj / 'results')) == {'sub-01/a.txt', 'sub-01/b.txt'}
