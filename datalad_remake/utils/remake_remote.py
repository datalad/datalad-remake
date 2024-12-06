from __future__ import annotations

import logging

from datalad_next.datasets import Dataset

from datalad_remake import auto_remote_name

logger = logging.getLogger('datalad.remake.utils.remake_remote')


def add_remake_remote(
    dataset_root: str,
    *,
    allow_untrusted_execution: bool = False,
):
    aue = 'true' if allow_untrusted_execution else 'false'
    options = [
        'type=external',
        'externaltype=datalad-remake',
        'encryption=none',
        'autoenable=true',
        f'allow-untrusted-execution={aue}',
    ]

    # Create a `Dataset`-instance to use the `AnnexRepo`-methods for special
    # remote handling.
    dataset = Dataset(dataset_root)

    # If no `datalad-remake` remote exists, create a new one. Do not touch
    # existing `datalad-remake` remotes.
    if not get_remake_auto_remote(dataset):
        dataset.repo.init_remote(auto_remote_name, options)
    else:
        logger.info(
            'Found already existing `datalad-remake` remote in %s. '
            'Leaving it unmodified, please check its configuration.',
            dataset_root,
        )

    # Update the configuration to allow unverified downloads from the remake
    # remote. This is necessary for prospective computation.
    update_config_for_remake(dataset_root, auto_remote_name)


def get_remake_auto_remote(dataset: Dataset) -> list:
    return [
        remote_info
        for remote_info in dataset.repo.get_special_remotes().values()
        if remote_info['type'] == 'external'
        and remote_info['externaltype'] == 'datalad-remake'
    ]


def update_config_for_remake(dataset_root: str, remote_name: str) -> None:
    # set annex security related variables to allow remake-URLs in prospective
    # computation
    dataset = Dataset(dataset_root)
    dataset.configuration(
        action='set',
        scope='local',
        spec=[
            (
                f'remote.{remote_name}.annex-security-allow-unverified-downloads',
                'ACKTHPPT',
            ),
        ],
        result_renderer='disabled',
    )
