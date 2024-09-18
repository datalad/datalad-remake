from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import (
    unquote,
    urlparse,
)

from annexremote import Master
from datalad.customremotes import RemoteError
from datalad_next.annexremotes import (
    SpecialRemote,
    super_main
)

from datalad_next.datasets import Dataset
from datalad_compute import url_scheme
from datalad_compute.commands.compute_cmd import (
    execute,
    provide,
    un_provide
)


class ComputeRemote(SpecialRemote):

    def __init__(self, annex: Master):
        super().__init__(annex)

    def __del__(self):
        self.close()

    def close(self) -> None:
        pass

    def _check_url(self, url: str) -> bool:
        return url.startswith(f'URL--{url_scheme}:') or url.startswith(f'{url_scheme}:')

    def prepare(self):
        self.annex.debug(f'PREPARE')

    def initremote(self):
        self.annex.debug(f'INITREMOTE')

    def remove(self, key: str):
        self.annex.debug(f'REMOVE {key!r}')

    def transfer_store(self, key: str, local_file: str):
        self.annex.debug(f'TRANSFER STORE')

    def claimurl(self, url: str) -> bool:
        self.annex.debug(f'CLAIMURL {url!r}')
        return self._check_url(url)

    def checkurl(self, url: str) -> bool:
        self.annex.debug(f'CHECKURL {url!r}')
        return self._check_url(url)

    def getcost(self) -> int:
        self.annex.debug(f'GETCOST')
        return 100

    def get_url_encoded_info(self, url: str) -> list[str]:
        parts = urlparse(url).query.split('&', 6)
        self.annex.debug(f'get_url_encoded_info: url: {url!r}, parts: {parts!r}')
        return parts

    def get_url_for_key(self, key: str) -> str:
        urls = self.annex.geturls(key, f'{url_scheme}:')
        self.annex.debug(f'get_url_for_key: key: {key!r}, urls: {urls!r}')
        return urls[0]

    def get_compute_info(self, key: str) -> dict[str, Any]:
        def get_assigned_value(assignment: str) -> str:
            return assignment.split('=', 1)[1]

        root_id, root_version, method, inputs, outputs, parameters, this \
            = self.get_url_encoded_info(self.get_url_for_key(key))

        return {
            'root_id': unquote(get_assigned_value(root_id)),
            'root_version': unquote(get_assigned_value(root_version)),
            'method': unquote(get_assigned_value(method)),
            'input': json.loads(unquote(get_assigned_value(inputs))),
            'output': json.loads(unquote(get_assigned_value(outputs))),
            'parameter': json.loads(unquote(get_assigned_value(parameters))),
            'this': unquote(get_assigned_value(this)),
        }

    def transfer_retrieve(self, key: str, file_name: str) -> None:
        self.annex.debug(f'TRANSFER RETRIEVE key: {key!r}, file_name: {file_name!r}')

        compute_info = self.get_compute_info(key)
        self.annex.debug(f'TRANSFER RETRIEVE compute_info: {compute_info!r}')

        # TODO: get version override from configuration
        dataset = self._find_dataset(compute_info['root_id'])

        # Perform the computation, and collect the results
        worktree = provide(dataset, compute_info['root_version'], compute_info['input'])
        execute(worktree, compute_info['method'], compute_info['parameter'], compute_info['output'])
        self._collect(worktree, dataset, compute_info['output'], compute_info['this'], file_name)
        un_provide(dataset, worktree)

    def checkpresent(self, key: str) -> bool:
        # See if at least one URL with the compute url-scheme is present
        return self.annex.geturls(key, f'{url_scheme}:') != []

    def _find_dataset(self,
                      root_id: str
                      ) -> Dataset:
        """Find the first enclosing dataset with the given root_id"""
        current_dir = Path(self.annex.getgitdir()) / '..'

        while current_dir != Path('/'):
            result = subprocess.run(
                [
                    'git', 'config', '-f',
                    str(current_dir/ '.datalad' / 'config'),
                    '--get', 'datalad.dataset.id'
                ],
                stdout=subprocess.PIPE)
            if result.returncode != 0:
                continue
            if result.stdout.decode().strip() == root_id:
                return Dataset(current_dir)
            current_dir = current_dir / '..'
        raise RemoteError(f'Could not find dataset {root_id!r}')

    def _collect(self,
                 worktree: Path,
                 dataset: Dataset,
                 outputs: list[str],
                 this: str,
                 this_destination: str,
                 ) -> None:
        """Collect computation results for `this` (and all other outputs) """

        # TODO: reap all other output files that are known to the annex
        shutil.copyfile(worktree / this, this_destination)


def main():
    """cmdline entry point"""
    super_main(
        cls=ComputeRemote,
        remote_name='compute',
        description="Access to computed data",
    )
