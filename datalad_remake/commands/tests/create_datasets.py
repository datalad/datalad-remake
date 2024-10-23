from __future__ import annotations

from pathlib import Path

from datalad_next.datasets import Dataset
from datalad_next.runners import call_git_success

from datalad_remake import template_dir


def update_config_for_remake(dataset: Dataset):
    # set annex security related variables to allow remake-URLs
    dataset.configuration(
        action='set',
        scope='local',
        recursive=True,
        spec=[('annex.security.allow-unverified-downloads', 'ACKTHPPT')],
        result_renderer='disabled',
    )


def add_remake_remote(dataset: Dataset):
    call_git_success(
        [
            '-C',
            dataset.path,
            'annex',
            'initremote',
            'remake',
            'type=external',
            'externaltype=datalad-remake',
            'encryption=none',
        ],
        capture_output=True,
    )


def create_ds_hierarchy(
    tmp_path: Path, name: str, subdataset_levels: int = 2
) -> list[tuple[str, Path, Dataset]]:
    # Create root dataset
    root_dataset = Dataset(tmp_path / name)
    root_dataset.create(force=True, result_renderer='disabled')
    (root_dataset.pathobj / 'a.txt').write_text('a\n')
    (root_dataset.pathobj / 'b.txt').write_text('b\n')
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
    update_config_for_remake(root_dataset)

    # Add datalad-remake remotes to the root dataset and all subdatasets
    add_remake_remote(root_dataset)
    subdataset_path = Path()
    for index in range(subdataset_levels):
        subdataset_path /= f'{name}_subds{index}'
        add_remake_remote(Dataset(root_dataset.pathobj / subdataset_path))

    return datasets


def create_simple_computation_dataset(
    tmp_path: Path,
    dataset_name: str,
    subdataset_levels: int,
    test_method: str,
) -> Dataset:
    datasets = create_ds_hierarchy(tmp_path, dataset_name, subdataset_levels)
    root_dataset = datasets[0][2]

    # add method template
    template_path = root_dataset.pathobj / template_dir
    template_path.mkdir(parents=True)
    (template_path / 'test_method').write_text(test_method)
    root_dataset.save(result_renderer='disabled')

    return root_dataset
