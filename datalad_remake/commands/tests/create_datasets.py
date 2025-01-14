from __future__ import annotations

from pathlib import Path

from datalad_next.datasets import Dataset

from datalad_remake import (
    template_dir,
    trusted_keys_config_key,
)
from datalad_remake.utils.remake_remote import add_remake_remote


def create_ds_hierarchy(
    tmp_path: Path,
    name: str,
    subdataset_levels: int = 2,
    signing_key: str | None = None,
) -> list[tuple[str, Path, Dataset]]:
    # Create root dataset
    root_dataset = Dataset(tmp_path / name)
    root_dataset.create(force=True, result_renderer='disabled')
    (root_dataset.pathobj / 'a.txt').write_text('a\n')
    (root_dataset.pathobj / 'b.txt').write_text('b\n')
    _enable_verification(root_dataset, signing_key)
    root_dataset.save(result_renderer='disabled')
    datasets = [(name, tmp_path / name, root_dataset)]

    # Create subdatasets
    for level in range(subdataset_levels):
        subdataset_path = tmp_path / f'{name}_subds{level}'
        subdataset = Dataset(subdataset_path)
        subdataset.create(force=True, result_renderer='disabled')
        (subdataset.pathobj / f'a{level}.txt').write_text(f'a{level}\n')
        (subdataset.pathobj / f'b{level}.txt').write_text(f'b{level}\n')
        subdataset.save(result_renderer='disabled')
        _enable_verification(subdataset, signing_key)
        datasets.append((f'{name}_subds{level}', subdataset_path, subdataset))

    # Link the datasets
    for index in range(len(datasets) - 2, -1, -1):
        dataset, subdataset = datasets[index : index + 2]
        dataset[2].install(
            path=subdataset[0],
            source=Path(subdataset[2].path).as_uri(),
            result_renderer='disabled',
        )
        dataset[2].save(result_renderer='disabled')

    root_dataset.get(recursive=True, result_renderer='disabled')

    # Modify subdatasets that are installed in the root dataset
    if subdataset_levels > 0:
        (root_dataset.pathobj / f'{name}_subds0' / 'm0.txt').write_text('m0\n')
        root_dataset.save(recursive=True, result_renderer='disabled')

    # Add datalad-remake remotes to the root dataset and all subdatasets
    add_remake_remote(root_dataset.path)
    subdataset_path = Path()
    for index in range(subdataset_levels):
        subdataset_path /= f'{name}_subds{index}'
        add_remake_remote(str(root_dataset.pathobj / subdataset_path))

    return datasets


def _enable_verification(dataset: Dataset, key: str | None):
    if key is not None:
        dataset.config.set('commit.gpgsign', 'true', scope='local')
        dataset.config.set('user.signingkey', key, scope='local')
        dataset.config.set(trusted_keys_config_key, key, scope='global')


def create_simple_computation_dataset(
    tmp_path: Path,
    dataset_name: str,
    subdataset_levels: int,
    test_method: str,
    test_method_name: str = 'test_method',
) -> Dataset:
    datasets = create_ds_hierarchy(tmp_path, dataset_name, subdataset_levels)
    root_dataset = datasets[0][2]

    # add method template
    template_path = root_dataset.pathobj / template_dir
    template_path.mkdir(parents=True)
    (template_path / test_method_name).write_text(test_method)
    root_dataset.save(result_renderer='disabled')

    return root_dataset
