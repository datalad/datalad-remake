from __future__ import annotations

from pathlib import Path
from urllib.parse import (
    unquote,
    urlparse,
)

from annexremote import Master
from datalad_next.annexremotes import (
    SpecialRemote,
    super_main
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
        return url.startswith('URL--compute:') or url.startswith('compute:')

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

    def transfer_retrieve(self, key: str, file_name: str) -> None:
        self.annex.debug(f'TRANSFER RETRIEVE {key!r} {file_name!r}')

        urls = self.annex.geturls(key, 'compute:')
        self.annex.debug(f'TRANSFER RETRIEVE urls({key!r}, "compute"): {urls!r}')
        assert len(urls) == 1

        dependencies, method, parameters = urlparse(urls[0]).query.split('&', 2)
        compute_info = {
            'dependencies': dependencies.split('=', 1)[1],
            'method': Path(self.annex.getgitdir()).parent / '.datalad' / 'compute' / 'methods' / method.split('=', 1)[1],
            'parameter': {
                assignment.split('=')[0]: unquote(assignment.split('=')[1])
                for assignment in parameters.split('&')
            }
        }
        self.annex.debug(f'TRANSFER RETRIEVE {key!r}: compute_info: {compute_info!r}, file_name: {file_name!r}')
        compute(compute_info['method'], compute_info['parameter'], file_name)


    def checkpresent(self, key: str) -> bool:
        # See if any compute: URL is present
        return self.annex.geturls(key, 'compute:') != []


def main():
    """cmdline entry point"""
    super_main(
        cls=ComputeRemote,
        remote_name='compute',
        description="Access to computed data",
    )
