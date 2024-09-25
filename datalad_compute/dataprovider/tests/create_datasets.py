from __future__ import annotations

from pathlib import Path

from datalad_next.datasets import Dataset


def create_subdatasets(tmp_path: Path,
                       parent_dataset: Dataset,
                       subdataset_levels: int = 2,
                       level_id: int = 0,
                       top_level_path: Path | None = None,
                       relative_subdataset_path: Path = None,
                       ) -> list[tuple[Dataset, Path]]:
    """Create a hierarchy of subdatasets in the dataset `parent_dataset`.

    Individual datasets are created in the temporary directory `tmp_path` and
    installed in the parent_dataset.

    The subdatasets are created in the directories `subds{level_id}`, where
    `level_id` is an integer counter starting at `0`. Each subdataset has two
    annexed files `a{level_id}.txt` and `b{level_id}.txt`.

    `subdataset_levels` determines the depth of the hierarchy. If, for example,
    `subdataset_levels` is 3, the following subdatasets are created:

      - parent_dataset/subds0
      - parent_dataset/subds0/subds1
      - parent_dataset/subds0/subds1/subds2
    """
    if subdataset_levels == 0:
        return []

    if relative_subdataset_path is None:
        relative_subdataset_path = Path(f'subds{level_id}')
    else:
        relative_subdataset_path /= Path(f'subds{level_id}')

    if top_level_path is None:
        top_level_path = parent_dataset.pathobj

    # Create a dataset in the tempaorary directory
    subdataset = Dataset(tmp_path / f'subds{level_id}')
    subdataset.create(result_renderer='disabled')
    (subdataset.pathobj / f'a{level_id}.txt').write_text(f'a{level_id}\n')
    (subdataset.pathobj / f'b{level_id}.txt').write_text(f'b{level_id}\n')

    child_datasets = create_subdatasets(
        tmp_path,
        subdataset,
        subdataset_levels - 1,
        level_id + 1,
        top_level_path,
        relative_subdataset_path)

    subdataset.save(result_renderer='disabled')

    # Install the dataset in the parent dataset
    parent_dataset.install(
        path=f'subds{level_id}',
        source='file://' + subdataset.path,

    )#result_renderer='disabled')

    parent_dataset.save(result_renderer='disabled')


    return [(
        subdataset,
        subdataset.pathobj,
        relative_subdataset_path)] + child_datasets


def create_ds_hierarchy(tmp_path: Path,
                        directory_name: str,
                        subdataset_levels: int = 2
                        ) -> list[tuple[Dataset, Path]]:
    dataset = Dataset(directory_name)
    dataset.create(force=True, result_renderer='disabled')
    subdatasets = create_subdatasets(tmp_path, dataset, subdataset_levels)
    (dataset.pathobj / 'a.txt').write_text('a\n')
    (dataset.pathobj / 'b.txt').write_text('b\n')
    dataset.save(result_renderer='disabled')
    return [(dataset, dataset.pathobj, Path('.'))] + subdatasets
