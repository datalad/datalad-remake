from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
)
from urllib.parse import (
    unquote,
    urlparse,
)

from datalad.customremotes import RemoteError
from datalad_core.config import (
    ConfigManager,
    DataladBranchConfig,
    GitEnvironment,
    GlobalGitConfig,
    ImplementationDefaults,
    LocalGitConfig,
)
from datalad_next.annexremotes import SpecialRemote, super_main
from datalad_next.datasets import Dataset
from datalad_next.runners import (
    call_git_lines,
    call_git_success,
)

from datalad_remake import (
    PatternPath,
    priority_config_key,
    specification_dir,
    template_dir,
    url_scheme,
)
from datalad_remake.commands.make_cmd import (
    execute,
    get_file_dataset,
    provide_context,
)
from datalad_remake.utils.getconfig import (
    get_allow_untrusted_execution,
    get_trusted_keys,
)
from datalad_remake.utils.glob import resolve_patterns
from datalad_remake.utils.patched_env import patched_env
from datalad_remake.utils.verify import verify_file

if TYPE_CHECKING:
    from collections.abc import Iterable

    from annexremote import Master


lgr = logging.getLogger('datalad.remake.annexremotes.remake')


class RemakeRemote(SpecialRemote):
    def __init__(self, annex: Master):
        super().__init__(annex)
        self._config_manager: ConfigManager | None = None

    @property
    def config_manager(self):
        if self._config_manager is None:
            dataset_dir = self._get_dataset_dir()
            self._config_manager = ConfigManager(
                defaults=ImplementationDefaults(),
                sources={
                    'git-command': GitEnvironment(),
                    'git': LocalGitConfig(dataset_dir),
                    'git-global': GlobalGitConfig(),
                    'datalad-branch': DataladBranchConfig(dataset_dir),
                },
            )
        return self._config_manager

    def __del__(self):
        self.close()

    def close(self) -> None:
        pass

    def _check_url(self, url: str) -> bool:
        return url.startswith((f'URL--{url_scheme}:', f'{url_scheme}:'))

    def prepare(self):
        self.annex.debug('PREPARE')

    def initremote(self):
        self.annex.debug('INITREMOTE')

    def remove(self, key: str):
        self.annex.debug(f'REMOVE {key!r}')

    def transfer_store(self, key: str, local_file: str):
        self.annex.debug(f'TRANSFER STORE {key!r}, {local_file!r}')

    def claimurl(self, url: str) -> bool:
        self.annex.debug(f'CLAIMURL {url!r}')
        return self._check_url(url)

    def checkurl(self, url: str) -> bool:
        self.annex.debug(f'CHECKURL {url!r}')
        return self._check_url(url)

    def getcost(self) -> int:
        self.annex.debug('GETCOST')
        return 100

    def get_url_encoded_info(self, url: str) -> list[str]:
        parts = urlparse(url).query.split('&', 3)
        self.annex.debug(f'get_url_encoded_info: url: {url!r}, parts: {parts!r}')
        return parts

    def get_urls_for_key(self, key: str) -> list[str]:
        urls = self.annex.geturls(key, f'{url_scheme}:')
        self.annex.debug(f'get_urls_for_key: key: {key!r}, urls: {urls!r}')
        return urls

    def get_compute_info(
        self,
        key: str,
        trusted_key_ids: list[str] | None,
    ) -> tuple[dict[str, Any], Dataset]:
        def get_assigned_value(assignment: str) -> str:
            return assignment.split('=', 1)[1]

        # get all compute instruction URLs for the key and select the
        # prioritized one.
        compute_instructions = {}
        for url in self.get_urls_for_key(key):
            label, root_version, spec_name, this = (
                unquote(get_assigned_value(expr))
                for expr in self.get_url_encoded_info(url)
            )
            compute_instructions[label] = root_version, spec_name, this

        # Select the compute instruction with the highest priority
        for label in self._get_priorities():
            if label in compute_instructions:
                root_version, spec_name, this = compute_instructions[label]
                break
        else:
            # If no priority is configured, select the first instruction
            root_version, spec_name, this = next(iter(compute_instructions.values()))

        dataset = self._find_dataset(root_version)
        spec_path = dataset.pathobj / specification_dir / spec_name
        if trusted_key_ids is not None:
            verify_file(dataset.pathobj, spec_path, trusted_key_ids)

        # Ensure that the spec is actually present and read it
        dataset.get(spec_path, result_renderer='disabled')
        with open(spec_path, 'rb') as f:
            spec = json.load(f)

        method_path = dataset.pathobj / template_dir / spec['method']
        dataset.get(method_path, result_renderer='disabled')

        stdout = spec.get('stdout', None)

        return {
            'root_version': root_version,
            'this': PatternPath(this),
            'method': Path(spec['method']),
            'input': [PatternPath(path) for path in spec['input']],
            'output': [PatternPath(path) for path in spec['output']],
            'stdout': PatternPath(stdout) if stdout else None,
            'parameter': spec['parameter'],
        }, dataset

    def transfer_retrieve(self, key: str, file_name: str) -> None:
        self.annex.debug(f'TRANSFER RETRIEVE key: {key!r}, file_name: {file_name!r}')

        # Remove any `GIT_DIR` and `GIT_WORK_TREE` environment variables during
        # the computation. This is necessary to avoid interference with the
        # `Dataset.get` implementation in DataLad.
        with patched_env(remove=['GIT_DIR', 'GIT_WORK_TREE']):
            dataset_id = self.config_manager.get('datalad.dataset.id').value
            self.annex.debug(f'TRANSFER RETRIEVE dataset_id: {dataset_id!r}')
            self.annex.debug(
                'TRANSFER RETRIEVE get_allow_untrusted_execution: '
                f'{get_allow_untrusted_execution(dataset_id)}'
            )
            if get_allow_untrusted_execution(dataset_id):
                trusted_key_ids = None
                lgr.warning('datalad remake remote performs UNTRUSTED execution')
            else:
                trusted_key_ids = get_trusted_keys()

            compute_info, dataset = self.get_compute_info(key, trusted_key_ids)
            self.annex.debug(f'TRANSFER RETRIEVE compute_info: {compute_info!r}')

            # Perform the computation, and collect the results
            lgr.debug('Starting provision')
            self.annex.debug('Starting provision')
            with provide_context(
                dataset,
                compute_info['root_version'],
                compute_info['input'],
            ) as worktree:
                # Ensure that the method template is present, in case it is annexed.
                lgr.debug('Fetching method template')
                Dataset(worktree).get(
                    PatternPath(template_dir) / compute_info['method'],
                    result_renderer='disabled',
                )

                lgr.debug('Starting execution')
                self.annex.debug('Starting execution')
                execute(
                    worktree,
                    compute_info['method'],
                    compute_info['parameter'],
                    compute_info['output'],
                    compute_info['stdout'],
                    trusted_key_ids,
                )

                lgr.debug('Starting collection')
                self.annex.debug('Starting collection')
                self._collect(
                    worktree,
                    dataset,
                    compute_info['output'],
                    compute_info['stdout'],
                    compute_info['this'],
                    file_name,
                )
                lgr.debug('Leaving provision context')
                self.annex.debug('Leaving provision context')

    def checkpresent(self, key: str) -> bool:
        # See if at least one URL with the remake url-scheme is present
        return self.annex.geturls(key, f'{url_scheme}:') != []

    def _find_dataset(self, commit: str) -> Dataset:
        """Find the first enclosing dataset with the given commit"""
        # TODO: get version override from configuration
        start_dir = self._get_dataset_dir()
        current_dir = start_dir
        while current_dir != Path('/'):
            if (Path(current_dir) / '.git').is_dir():
                result = subprocess.run(
                    ['git', 'cat-file', '-t', commit],  # noqa: S607
                    stdout=subprocess.PIPE,
                    cwd=current_dir,
                    check=False,
                )
                if result.returncode == 0 and result.stdout.strip() == b'commit':
                    return Dataset(current_dir)
            current_dir = current_dir.parent
        msg = (
            f'Could not find dataset with commit {commit!r}, starting from '
            f'{start_dir}'
        )
        raise RemoteError(msg)

    def _collect(
        self,
        worktree: Path,
        dataset: Dataset,
        output_patterns: Iterable[PatternPath],
        stdout: PatternPath | None,
        this: PatternPath,
        this_destination: str,
    ) -> None:
        """Collect computation results for `this` (and all other outputs)"""

        # Get all outputs that were created during computation
        outputs = resolve_patterns(root_dir=worktree, patterns=output_patterns)

        # Collect all output files that have been created while creating
        # `this` file.
        for output in outputs:
            # Skip `this` file because it will be copied to the destination
            if output == this:
                continue
            is_annexed, dataset_path, file_path = self._is_annexed(dataset, output)
            self.annex.debug(
                f'_collect: _is_annexd({output}): {is_annexed}, {dataset_path}, {file_path}'
            )
            if is_annexed:
                self.annex.debug(
                    f'_collect: reinject: {worktree / output} -> {dataset_path}:{file_path}'
                )
                call_git_success(
                    ['annex', 'reinject', str(worktree / output), str(file_path)],
                    cwd=dataset_path,
                    capture_output=True,
                )

        # Collect possible stdout
        if stdout is not None:
            is_annexed, dataset_path, file_path = self._is_annexed(dataset, stdout)
            if is_annexed:
                self.annex.debug(
                    f'_collect: reinject: {worktree / stdout} -> {dataset_path}:{file_path}'
                )
                call_git_success(
                    ['annex', 'reinject', str(worktree / stdout), str(file_path)],
                    cwd=dataset_path,
                    capture_output=True,
                )
            else:
                shutil.copyfile(worktree / stdout, dataset.pathobj / stdout)

        # Collect `this` file. It has to be copied to the destination given
        # by git-annex. Git-annex will check its integrity.
        shutil.copyfile(worktree / this, this_destination)

    def _is_annexed(
        self, dataset: Dataset, file_path: PatternPath
    ) -> tuple[bool, Path, Path]:
        """Check whether file_path is annexed and return the dataset and intra dataset path"""
        dataset_path, in_dataset_path = get_file_dataset(dataset.pathobj / file_path)
        self.annex.debug(
            f'_is_annexed: {dataset}:{file_path} --> dataset_path: {dataset_path}, in_dataset_path: {in_dataset_path}'
        )
        result = call_git_lines(
            ['annex', 'whereis', str(in_dataset_path)],
            cwd=dataset_path,
        )
        self.annex.debug(f'_is_annexed: result {result}')
        return result != [], dataset_path, in_dataset_path

    def _get_priorities(self) -> list[str]:
        """Get configured priorities

        The priorities are search in the following locations in the order
        given below:
        1. local git-config entries
        2. global git-config entries
        3. `.datalad/config`-file in the dataset on which the remote operates.

        :return:
            list[str]: list of priorities, highest priority first. If no
            priorities are configured, an empty list is returned.
        """
        setting = self.config_manager.get(priority_config_key)
        if setting.value:
            return setting.value.split(',')
        return []

    def _get_dataset_dir(self) -> Path:
        return Path(self.annex.getgitdir()).parent.absolute()


def main():
    """cmdline entry point"""
    super_main(
        cls=RemakeRemote,
        remote_name='datalad-remake',
        description='Remake data based on datalad-remake specifications',
    )
