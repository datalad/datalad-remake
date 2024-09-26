from __future__ import annotations

from pathlib import Path

from datalad_next.datasets import Dataset
from datalad_next.runners import call_git_success

from datalad_compute import url_scheme


def update_config_for_compute(dataset: Dataset):
    # set annex security related variables to allow compute-URLs
    dataset.configuration(
        action='set',
        scope='local',
        recursive=True,
        spec=[
            ('annex.security.allowed-url-schemes', url_scheme),
            ('annex.security.allowed-ip-addresses', 'all'),
            ('annex.security.allow-unverified-downloads', 'ACKTHPPT')])


def add_compute_remote(dataset: Dataset):
    call_git_success([
        '-C', dataset.path,
        'annex', 'initremote', 'compute',
        'type=external', 'externaltype=compute',
        'encryption=none'])


def create_ds_hierarchy(tmp_path: Path,
                        name: str,
                        subdataset_levels: int = 2
                        ) -> list[tuple[str, Path, Dataset]]:

    # Create root dataset
    root_dataset = Dataset(tmp_path / name)
    root_dataset.create(force=True, result_renderer='disabled')
    (root_dataset.pathobj / 'a.txt').write_text('a\n')
    (root_dataset.pathobj / 'b.txt').write_text('b\n')
    root_dataset.save()
    datasets = [(name, tmp_path / name, root_dataset)]

    # Create subdatasets
    for level in range(subdataset_levels):
        subdataset_path = tmp_path / f'{name}_subds{level}'
        subdataset = Dataset(subdataset_path)
        subdataset.create(force=True, result_renderer='disabled')
        (subdataset.pathobj / f'a{level}.txt').write_text(f'a{level}\n')
        (subdataset.pathobj / f'b{level}.txt').write_text(f'b{level}\n')
        subdataset.save()
        datasets.append((f'{name}_subds{level}', subdataset_path, subdataset))

    # Link the datasets
    for index in range(len(datasets) - 2, -1, -1):
        dataset, subdataset = datasets[index:index+2]
        print(index)
        print(dataset)
        print(subdataset)
        dataset[2].install(
            path=subdataset[0],
            source='file://' + subdataset[2].path,
        )
        dataset[2].save()

    root_dataset.get(recursive=True)
    update_config_for_compute(root_dataset)

    # Add compute remotes to the root dataset and all subdatasets
    add_compute_remote(root_dataset)
    subdataset_path = Path()
    for index in range(subdataset_levels):
        subdataset_path /= f'{name}_subds{index}'
        add_compute_remote(Dataset(root_dataset.pathobj / subdataset_path))

    return datasets
