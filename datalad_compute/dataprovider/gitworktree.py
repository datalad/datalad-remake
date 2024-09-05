"""
A data provisioner that works with local git repositories.
Data is provisioned in a temporary worktree
Currently there is no support for subdatasets
"""
from __future__ import annotations

import subprocess
import tempfile
from argparse import ArgumentParser
from contextlib import chdir
from pathlib import Path


argument_parser = ArgumentParser()
argument_parser.add_argument('dataset', help='Path to source dataset')
argument_parser.add_argument(
    '-v', '--version',
    help='Version of the source (sha or tag). If not given the default branch '
         'will be used',
)
argument_parser.add_argument(
    '-p', '--pattern',
    action='append',
    help='File pattern of files that should be provisioned. If not given, the '
        'complete repository will be provisioned',
)


def provide(dataset: str,
            version: str | None,
            pattern: list[str] | None,
            ) -> Path:

    dataset = Path(dataset)
    worktree_dir = temporary_worktree(dataset)
    if version:
        with chdir(worktree_dir):
            subprocess.run(['git', 'checkout', version], check=True)
            if pattern:
                for p in pattern:
                    subprocess.run(['git', 'annex', 'get', p], check=True)
            else:
                subprocess.run(['git', 'annex', 'get'], check=True)
    return worktree_dir


def temporary_worktree(dataset: Path) -> Path:
    worktree_dir = tempfile.TemporaryDirectory().name
    with chdir(dataset):
        subprocess.run(['git', 'worktree', 'add', worktree_dir], check=True)
    return Path(worktree_dir)


def main():
    arguments = argument_parser.parse_args()
    provision_dir = provide(
        arguments.dataset,
        arguments.version,
        arguments.pattern,
    )
    print(provision_dir)


if __name__ == '__main__':
    main()
