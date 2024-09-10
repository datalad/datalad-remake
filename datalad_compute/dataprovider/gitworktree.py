"""
A data provisioner that works with local git repositories.
Data is provisioned in a temporary worktree. All subdatasets
are currently also provisioned.
"""
from __future__ import annotations

import subprocess
import tempfile
from argparse import ArgumentParser
from contextlib import chdir
from pathlib import Path

from datalad.distribution.dataset import Dataset


argument_parser = ArgumentParser()
argument_parser.add_argument(
    'dataset',
    default='.',
    help='Path to source dataset (default: current directory)',
)
argument_parser.add_argument(
    '-b', '--branch',
    help='Branch (name, sha, or tag) that should be used. If not given the '
         'default branch will be used',
)
argument_parser.add_argument(
    '-i', '--input',
    action='append',
    help='Name of a file that should be provisioned (use multiple times to '
         'define multiple inputs). If not provided, the complete dataset, '
         'including all subdatasets, will be provisioned',
)


def provide(dataset: str,
            branch: str | None = None,
            input_files: list[str] | None = None,
            ) -> Path:

    worktree_dir = Path(tempfile.TemporaryDirectory().name)
    # Get all datasets including subdatasets into the worktree
    provide_datasets(
        Dataset(dataset),
        worktree_dir=worktree_dir,
        temp_branch=worktree_dir.name,
        source_branch=branch,
    )

    # Fetch file content
    with chdir(worktree_dir):
        if input_files:
            for p in input_files:
                subprocess.run(['datalad', 'get', p], check=True)
        else:
            subprocess.run(['datalad', 'get', '-r'], check=True)
    return worktree_dir


def provide_datasets(dataset: Dataset,
                     worktree_dir: Path,
                     temp_branch: str,
                     source_branch: str | None = None,
                     ) -> None:

    with chdir(dataset.path):
        args = ['git', 'worktree', 'add', '-b', temp_branch, str(worktree_dir)] + (
            [source_branch] if source_branch else []
        )

        subprocess.run(args, check=True)
        for subdataset in dataset.subdatasets():
            subdataset_path = Path(subdataset['path']).relative_to(dataset.pathobj)
            dataset.install(path=subdataset_path)
            provide_datasets(
                Dataset(subdataset_path),
                worktree_dir / subdataset_path,
                temp_branch,
            )


def main():
    arguments = argument_parser.parse_args()
    provision_dir = provide(
        arguments.dataset,
        arguments.branch,
        arguments.input,
    )
    print(provision_dir)


if __name__ == '__main__':
    main()
