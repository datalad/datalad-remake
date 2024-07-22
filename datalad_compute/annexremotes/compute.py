from __future__ import annotations

from base64 import urlsafe_b64decode
from pathlib import Path
from urllib.parse import urlparse

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

    def _compute(self, compute_info, file_name: str) -> None:
        template = Path(self.annex.getgitdir()).parent / '.datalad' / 'compute' / 'methods' / compute_info['method']
        arguments = {
            assignment.split('=')[0]: assignment.split('=')[1]
            for assignment in compute_info['parameter'].split(';')
        }
        if compute_info.get('dependencies', 'none') != 'none':
            dependencies = {
                spec.split(':')[0]: spec.split(':')[1]
                for spec in compute_info['dependencies'].split(';')
                if spec
            }
        else:
            dependencies = dict()
        self.annex.debug(f'COMPUTE calling compute with: {template!r} {arguments!r} {file_name!r}')
        compute(template, arguments, file_name)

    def transfer_retrieve(self, key: str, file_name: str) -> None:
        self.annex.debug(f'TRANSFER RETRIEVE {key!r} {file_name!r}')
        urls = self.annex.geturls(key, 'compute:')
        self.annex.debug(f'TRANSFER RETRIEVE urls({key!r}, "compute"): {urls!r}')

        parsed_urls = [urlparse(url) for url in urls]

        # assure a single ID
        ids = set(parts.netloc for parts in parsed_urls)
        assert len(ids) == 1, f"Expected a single ID, got {ids}"

        # we need "method", "parameter", and "dependencies" data
        categories = ('method', 'parameter', 'dependencies')
        compute_info = {
            category: urlsafe_b64decode(parts.path.split('/')[2]).strip().decode()
            for category in categories
            for parts in parsed_urls if parts.path.startswith(f'/{category}/')
        }
        assert tuple(compute_info.keys()) == categories, \
            f"Expected 'method', 'parameter', and 'dependencies', got {compute_info.keys()}"

        self.annex.debug(f'TRANSFER RETRIEVE {key!r}: compute_info: {compute_info!r}, file_name: {file_name!r}')
        self._compute(compute_info, file_name)

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
