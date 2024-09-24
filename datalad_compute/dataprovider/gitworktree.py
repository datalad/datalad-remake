"""
A data provisioner that works with local git repositories.
Data is provisioned in a temporary worktree. All subdatasets
are currently also provisioned.
"""
from __future__ import annotations

import os
import random
import shutil
from argparse import ArgumentParser
from contextlib import chdir
from pathlib import Path

from datalad_next.datasets import Dataset
from datalad_next.runners import call_git_success


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
    '-t', '--temp-dir',
    metavar='PATH',
    default=os.getenv('TMP', '/tmp'),
    help='Path of the directory where temporary worktrees should be created. '
         'The  default is `$TMP` if set, otherwise `/tmp`.',
)


def remove(dataset: str,
           worktree: str
           ) -> None:

    shutil.rmtree(worktree)
    dataset = Dataset(dataset)
    prune_worktrees(dataset)


def prune_worktrees(dataset: Dataset) -> None:
    with chdir(dataset.path):
        call_git_success(['worktree', 'prune'])
    for result in dataset.subdatasets(result_renderer='disabled'):
        prune_worktrees(Dataset(result['path']))


def provide(dataset: str,
            temp_dir: str,
            branch: str | None = None,
            input_files: list[str] | None = None,
            ) -> Path:

    worktree_name = random_name()
    worktree_dir = Path(temp_dir) / worktree_name
    if not worktree_dir.exists():
        worktree_dir.mkdir(parents=True, exist_ok=True)

    # Get all datasets including subdatasets into the worktree
    provide_datasets(
        Dataset(dataset),
        worktree_dir=worktree_dir,
        branch_name=worktree_name,
        source_branch=branch,
    )

    # Fetch file content in the worktree
    work_dataset = Dataset(worktree_dir)
    with chdir(worktree_dir):
        for p in input_files or []:
            work_dataset.get(p, result_renderer='disabled')
    return worktree_dir


def provide_datasets(dataset: Dataset,
                     worktree_dir: Path,
                     branch_name: str | None,
                     source_branch: str | None = None,
                     ) -> None:

    with chdir(dataset.path):

        args = ['worktree', 'add'] + (
            ['-b', branch_name]
            if branch_name
            else []
        ) + [str(worktree_dir)] + (
                   [source_branch]
                   if source_branch
                   else []
               )
        call_git_success(args)

        for subdataset in dataset.subdatasets(result_renderer='disabled'):
            subdataset_path = Path(subdataset['path']).relative_to(dataset.pathobj)
            dataset.install(path=subdataset_path, result_renderer='disabled')
            provide_datasets(
                Dataset(subdataset_path),
                worktree_dir / subdataset_path,
                branch_name,
                None,   # Use default commit-ish for subdatasets
            )


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

    provision_dir = provide(
        arguments.dataset,
        arguments.temp_dir,
        arguments.branch,
        arguments.input,
    )
    print(provision_dir)


if __name__ == '__main__':
    main()
