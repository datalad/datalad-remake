from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import (
    unquote,
    urlparse,
)

from annexremote import Master
from datalad_next.annexremotes import (
    SpecialRemote,
    super_main
)

from datalad_compute import (
    template_dir,
    url_scheme,
)
from datalad_compute.utils.compute import compute


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

    def get_url_encoded_info(self, url: str) -> tuple[str, str, str]:
        parts = urlparse(url).query.split('&', 2)
        return parts[0], parts[1], parts[2]

    def get_url_for_key(self, key: str) -> str:
        urls = self.annex.geturls(key, f'{url_scheme}:')
        self.annex.debug(f'TRANSFER RETRIEVE urls({key!r}, "{url_scheme}"): {urls!r}')
        return urls[0]

    def get_compute_info(self, key: str) -> dict[str, Any]:
        def get_assignment_value(assignment: str) -> str:
            return assignment.split('=', 1)[1]

        dependencies, method, parameters = self.get_url_encoded_info(
            self.get_url_for_key(key)
        )
        return {
            'dependencies': get_assignment_value(dependencies),
            'method': Path(self.annex.getgitdir()).parent
                / template_dir
                / get_assignment_value(method),
            'parameter': {
                name: unquote(value)
                for name, value in map(lambda s: s.split('=', 1), parameters.split('&'))
            }
        }

    def transfer_retrieve(self, key: str, file_name: str) -> None:
        compute_info = self.get_compute_info(key)
        self.annex.debug(f'TRANSFER RETRIEVE {key!r}: compute_info: {compute_info!r}, file_name: {file_name!r}')
        compute(compute_info['method'], compute_info['parameter'], file_name)

    def checkpresent(self, key: str) -> bool:
        # See if at least one URL with the compute url-scheme is present
        return self.annex.geturls(key, f'{url_scheme}:') != []


def main():
    """cmdline entry point"""
    super_main(
        cls=ComputeRemote,
        remote_name='compute',
        description="Access to computed data",
    )
