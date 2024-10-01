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
from typing import Iterable

from datalad_next.datasets import Dataset
from datalad_next.runners import call_git_success

from datalad_compute.utils.glob import resolve_patterns
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
    help='File pattern that should be provisioned (relative from dataset '
         'root), at least one input has to be provided (use multiple times to '
         'define multiple inputs). Patterns are resolved by Python\'s globbing '
         'rules. They are resolved in the source dataset.',
)
argument_parser.add_argument(
    '-I', '--input-list',
    metavar='PATH',
    default=None,
    help='Path of a file that contains a list of input file patterns',
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


def provide(dataset_dir: str,
            temp_dir: str,
            source_branch: str | None = None,
            input_patterns: Iterable[str] | None = None,
            ) -> Path:

    lgr.debug('Provisioning dataset %s', dataset_dir)
    worktree_name = random_name()
    worktree_dir = Path(temp_dir) / worktree_name
    if not worktree_dir.exists():
        worktree_dir.mkdir(parents=True, exist_ok=True)

    # Resolve input file patterns in the original dataset
    input_files = resolve_patterns(dataset_dir, input_patterns)

    # Create a worktree
    with chdir(dataset_dir):
        args = ['worktree', 'add', '-b', worktree_name] + [str(worktree_dir)] + (
            [source_branch]
            if source_branch
            else []
        )
        call_git_success(args, capture_output=True)

    source_dataset = Dataset(dataset_dir)

    # get candidate environment variables for each subdataset
    env_vars = get_candidate_env_vars(source_dataset)

    # Get all input files in the worktree
    worktree_dataset = Dataset(worktree_dir)
    with chdir(worktree_dataset.path):
        stored_environ = dict(os.environ)
        os.environ.update(env_vars)
        for file in input_files:
            lgr.debug('Provisioning file %s', file)
            worktree_dataset.get(file, result_renderer='disabled')
        os.environ.clear()
        os.environ.update(stored_environ)

    return worktree_dir


def get_candidate_env_vars(dataset: Dataset, counter: int = 1) -> dict[str, str]:
    env_vars = {}
    for result in dataset.subdatasets(result_renderer='disabled'):
        env_vars[f'DATALAD_GET_SUBDATASET__SOURCE__CANDIDATE__100_{counter}'] = result['path']
        counter += 1
        subdataset = Dataset(result['path'])
        env_vars = {
            **env_vars,
            **get_candidate_env_vars(subdataset, counter)
        }
    return env_vars


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
