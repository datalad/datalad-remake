"""
A data provisioner that works with local git repositories.
Data is provisioned in a temporary worktree. All subdatasets
are currently also provisioned.
"""
from __future__ import annotations

import logging
import os
import random
import shutil
from argparse import ArgumentParser
from contextlib import chdir
from pathlib import Path
from urllib.parse import urlparse

from datalad_next.datasets import Dataset
from datalad_next.runners import call_git_success

from ..commands.compute_cmd import read_list


lgr = logging.getLogger('datalad.compute.dataprovider.gitworktree')

argument_parser = ArgumentParser()
argument_parser.add_argument(
    'dataset',
    default='.',
    help='Path to source dataset (default: current directory)',
)
argument_parser.add_argument(
    '-d', '--delete',
    metavar='WORKTREE',
    help='Delete the temporary worktree WORKTREE that belongs the the '
         'dataset (cannot be used with `-b`, `--branch`, `-i`, or `--input`)',
)
argument_parser.add_argument(
    '-b', '--branch',
    help='Branch (name, sha, or tag) of `dataset` that should be provisioned. '
         'If not given the default branch will be used',
)
argument_parser.add_argument(
    '-i', '--input',
    action='append',
    metavar='PATH',
    help='Path of a file that should be provisioned (relative from dataset '
         'root), at least one input has tp be provided (use multiple times to '
         'define multiple inputs)',
)
argument_parser.add_argument(
    '-I', '--input-list',
    metavar='PATH',
    default=None,
    help='Path of a file that contains a list of input paths',
)
argument_parser.add_argument(
    '-t', '--temp-dir',
    metavar='PATH',
    default=os.getenv('TMP', '/tmp'),
    help='Path of the directory where temporary worktrees should be created. '
         'The  default is `$TMP` if set, otherwise `/tmp`.',
)


def remove(dataset: str,
           worktree: str
           ) -> None:
    remove_subdatasets(worktree)
    shutil.rmtree(worktree)
    dataset = Dataset(dataset)
    prune_worktrees(dataset)


def remove_subdatasets(worktree: str):
    dataset = Dataset(worktree)
    for subdataset_info in dataset.subdatasets(result_renderer='disabled'):
        dataset.drop(
            subdataset_info['path'],
            recursive=True,
            reckless='kill',
            what='all',
            result_renderer='disabled')


def prune_worktrees(dataset: Dataset) -> None:
    with chdir(dataset.path):
        call_git_success(
            ['worktree', 'prune'],
            capture_output=True)

    for result in dataset.subdatasets(result_renderer='disabled'):
        prune_worktrees(Dataset(result['path']))


def ensure_absolute_gitmodule_urls(original_dataset: Dataset,
                                   dataset: Dataset
                                   ) -> None:
    sub_datasets = dataset.subdatasets(result_renderer='disabled')
    for subdataset in sub_datasets:
        name, location_spec = subdataset['gitmodule_name'], subdataset['gitmodule_url']
        parse_result = urlparse(location_spec)
        if parse_result.scheme == '':
            if not Path(location_spec).is_absolute():
                args = ['submodule', 'set-url', name, original_dataset.path]
                call_git_success(args, cwd=dataset.path, capture_output=True)
    dataset.save(result_renderer='disabled')


def provide(dataset_dir: str,
            temp_dir: str,
            source_branch: str | None = None,
            input_files: list[str] | None = None,
            ) -> Path:

    lgr.debug('Provisioning dataset %s', dataset_dir)
    worktree_name = random_name()
    worktree_dir = Path(temp_dir) / worktree_name
    if not worktree_dir.exists():
        worktree_dir.mkdir(parents=True, exist_ok=True)

    # Create a worktree
    with chdir(dataset_dir):
        args = ['worktree', 'add', '-b', worktree_name] + [str(worktree_dir)] + (
            [source_branch]
            if source_branch
            else []
        )
        call_git_success(args, capture_output=True)

    worktree_dataset = Dataset(worktree_dir)
    # Ensure that all subdatasets have absolute URLs
    ensure_absolute_gitmodule_urls(Dataset(dataset_dir), worktree_dataset)
    # Get all input files in the worktree
    with chdir(worktree_dataset.path):
        for file in input_files or []:
            lgr.debug('Provisioning file %s', file)
            worktree_dataset.get(file, result_renderer='disabled')

    return worktree_dir


def random_name() -> str:
    return 'tmp_' + ''.join(
        random.choices('abcdefghijklmnopqrstuvwxyz', k=10))


def main():
    arguments = argument_parser.parse_args()
    if arguments.delete:

        if arguments.branch or arguments.input:
            raise ValueError(
                'Cannot use `-d`, `--delete` with `-b`, `--branch`,'
                ' `-i`, or `--input`')

        remove(arguments.dataset, arguments.delete)
        return

    inputs = arguments.input or [] + read_list(arguments.input_list)

    provision_dir = provide(
        arguments.dataset,
        arguments.temp_dir,
        arguments.branch,
        inputs,
    )
    print(provision_dir)


if __name__ == '__main__':
    main()
