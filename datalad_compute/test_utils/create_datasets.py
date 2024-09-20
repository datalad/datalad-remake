import tempfile
from pathlib import Path

from datalad_next.datasets import Dataset


def create_subdatasets(parent_dataset: Dataset,
                       subdataset_levels: int = 2,
                       level_id: int = 0,
                       top_level_path: Path | None = None
                       ) -> list[tuple[Dataset, Path]]:
    """Create a hierarchy of subdatasets in the dataset `parent_dataset`.

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

    if top_level_path is None:
        top_level_path = parent_dataset.pathobj

    subdataset = Dataset(parent_dataset.pathobj / f'subds{level_id}')
    subdataset.create(result_renderer='disabled')
    child_datasets = create_subdatasets(
        subdataset,
        subdataset_levels - 1,
        level_id + 1,
        top_level_path)
    (subdataset.pathobj / f'a{level_id}.txt').write_text(f'a{level_id}\n')
    (subdataset.pathobj / f'b{level_id}.txt').write_text(f'b{level_id}\n')
    subdataset.save(result_renderer='disabled')
    return [(
        subdataset,
        subdataset.pathobj,
        subdataset.pathobj.relative_to(top_level_path))] + child_datasets


def create_ds_hierarchy(directory_name: str,
                        subdataset_levels: int = 2
                        ) -> list[tuple[Dataset, Path]]:
    dataset = Dataset(directory_name)
    dataset.create(force=True, result_renderer='disabled')
    subdatasets = create_subdatasets(dataset, subdataset_levels)
    (dataset.pathobj / 'a.txt').write_text('a\n')
    (dataset.pathobj / 'b.txt').write_text('b\n')
    dataset.save(result_renderer='disabled')
    return [(dataset, dataset.pathobj, Path('.'))] + subdatasets
