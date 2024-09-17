"""
A data provisioner that works with local git repositories.
Data is provisioned in a temporary worktree
Currently there is no support for subdatasets
"""
from __future__ import annotations

import contextlib
import subprocess
import tempfile
from argparse import ArgumentParser
from contextlib import chdir
from pathlib import Path

from datalad_compute import template_dir
from datalad_compute.utils.compute import compute


argument_parser = ArgumentParser()
argument_parser.add_argument(
    'dataset',
    help='Path to provisioned dataset'
)
argument_parser.add_argument(
    'template',
    help='Name of the computing template (template should be present '
         'in $DATASET/.datalad/compute/methods)'
)
argument_parser.add_argument(
    '-p', '--parameter',
    action='append',
    help='Parameter for the execution in the form <name>=<value> (repeat for '
         'multiple parameters)',
)
argument_parser.add_argument(
    '-o', '--output',
    action='append',
    help='Files that will be written or modified by the template execution',
)


def unlock(dataset: Path, outputs: list[str] | None) -> None:
    with contextlib.chdir(dataset):
        for output in outputs:
            if Path(output).exists():
                subprocess.run(['git', 'annex', 'unlock', output], check=True)


def execute(dataset: Path,
            method: str | None,
            parameters: list[str] | None,
            outputs: list[str] | None,
            ) -> None:

    unlock(dataset, outputs)
    compute(
        template_path=dataset / template_dir / method,
        compute_arguments={
            parameter.split('=', 1)[0]: parameter.split('=', 1)[1]
            for parameter in parameters
        },
    )


def temporary_worktree(dataset: Path) -> Path:
    worktree_dir = tempfile.TemporaryDirectory().name
    with chdir(dataset):
        subprocess.run(['git', 'worktree', 'add', worktree_dir], check=True)
    return Path(worktree_dir)


def main():
    arguments = argument_parser.parse_args()
    execute(
        Path(arguments.dataset),
        arguments.template,
        arguments.parameter,
        arguments.output,
    )


if __name__ == '__main__':
    main()
