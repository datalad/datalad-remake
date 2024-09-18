"""DataLad demo command"""

from __future__ import annotations

__docformat__ = 'restructuredtext'

import contextlib
import json
import logging
import shutil
import subprocess
from itertools import chain
from pathlib import Path
from tempfile import template
from urllib.parse import quote

from datalad_next.commands import (
    EnsureCommandParameterization,
    ValidatedInterface,
    Parameter,
    build_doc,
    datasetmethod,
    eval_results,
    get_status_dict,
)
from datalad_next.constraints import (
    EnsureDataset,
    EnsureListOf,
    EnsureStr,
)
from datalad_next.datasets import Dataset
from datalad_next.runners import call_git_oneline, call_git_success, iter_subproc
from datalad_compute import (
    template_dir,
    url_scheme,
)
from datalad_compute.utils.compute import compute
from datasalad.runners import iter_subproc
from datasalad.itertools import (
    itemize,
    load_json,
)
from more_itertools import intersperse


lgr = logging.getLogger('datalad.compute.compute_cmd')


# decoration auto-generates standard help
@build_doc
# all commands must be derived from Interface
class Compute(ValidatedInterface):
    # first docstring line is used a short description in the cmdline help
    # the rest is put in the verbose help and manpage
    """Specify a computation and optionally execute it
    """

    _validator_ = EnsureCommandParameterization(dict(
        dataset=EnsureDataset(installed=True),
        input=EnsureListOf(EnsureStr(min_len=1), min_len=1),
        output=EnsureListOf(EnsureStr(min_len=1), min_len=1),
        parameter=EnsureListOf(EnsureStr(min_len=3)),
    ))

    # parameters of the command, must be exhaustive
    _params_ = dict(
        dataset=Parameter(
            args=('-d', '--dataset'),
            doc="Dataset to be used as a configuration source. Beyond "
            "reading configuration items, this command does not interact with "
            "the dataset."),
        url_only=Parameter(
            args=('-u', '--url-only'),
            action="store_true",
            doc="Don't perform the computation, register an URL-key "
            "instead. A `git annex get <file>` will trigger the computation"),
        template=Parameter(
            args=('template',),
            doc="Name of the computing template (template should be present "
                "in $DATASET/.datalad/compute/methods)"),
        branch=Parameter(
            args=('-b', '--branch',),
            doc="Branch (or commit) that should be used for computation, if "
                "not specified HEAD will be used"),
        input=Parameter(
            args=('-i', '--input',),
            action='append',
            doc="Name of an input file (repeat for multiple inputs)"),
        output=Parameter(
            args=('-o', '--output',),
            action='append',
            doc="Name of an output file (repeat for multiple outputs)"),
        parameter=Parameter(
            args=('-p', '--parameter',),
            action='append',
            doc="Input parameter in the form <name>=<value> (repeat for "
                "multiple parameters)"),
    )


    @staticmethod
    @datasetmethod(name='compute')
    @eval_results
    def __call__(dataset=None,
                 url_only=False,
                 template=None,
                 branch=None,
                 input=None,
                 output=None,
                 parameter=None,
                 ):

        dataset : Dataset = dataset.ds if dataset else Dataset()

        if not url_only:
            worktree = provide(dataset, branch, input)
            execute(worktree, template, parameter, output)
            collect(worktree, dataset, output)
            un_provide(dataset, worktree)

        url_base = get_url(dataset, branch, template, parameter, input, output)

        for out in output:
            url = add_url(dataset, out, url_base, url_only)
            yield get_status_dict(
                    action='compute',
                    path=dataset.pathobj / out,
                    status='ok',
                    message=f'added url: {url!r} to {out!r} in {dataset.pathobj}',)


def get_url(dataset: Dataset,
            branch: str | None,
            template_name: str,
            parameters: dict[str, str],
            input_files: list[str],
            output_files: list[str],
            ) -> str:

    branch = dataset.repo.get_hexsha() if branch is None else branch
    return (
        f'{url_scheme}:///'
        + f'?root_id={quote(dataset.id)}'
        + f'&default_root_version={quote(branch)}'
        + f'&method={quote(template_name)}'
        + f'&input={quote(json.dumps(input_files))}'
        + f'&output={quote(json.dumps(output_files))}'
        + f'&params={quote(json.dumps(parameters))}'
    )


def add_url(dataset: Dataset,
            file_path: str,
            url_base: str,
            url_only: bool
            ) -> str:

    lgr.debug(
        'add_url: %s %s %s %s',
        str(dataset), str(file_path), url_base, repr(url_only))

    # Build the file-specific URL and store it in the annex
    url = url_base + f'&this={quote(file_path)}'
    file_dataset_path, file_path = get_file_dataset(dataset.pathobj / file_path)
    call_git_success(
        ['-C', str(file_dataset_path), 'annex', 'addurl', url, '--file', file_path]
        + (['--relaxed'] if url_only else []))
    return url


def get_file_dataset(file: Path) -> [Path, Path]:
    """ Get dataset of file and relative path of file from the dataset

    Determine the dataset that contains the file and the relative path of the
    file in this dataset."""
    top_level = Path(call_git_oneline(
        ['-C', str(file.parent), 'rev-parse', '--show-toplevel']
    ))
    return (
        Path(top_level),
        file.absolute().relative_to(top_level))


def provide(dataset: Dataset,
            branch: str | None,
            input: list[str],
            ) -> Path:

    lgr.debug('provide: %s %s %s', dataset, branch, input)

    args = ['provide-gitworktree', dataset.path, ] + (
        ['--branch', branch] if branch else []
    )
    args.extend(chain(*[('--input', i) for i in input]))
    stdout = subprocess.run(args, stdout=subprocess.PIPE, check=True).stdout
    return Path(stdout.splitlines()[-1].decode())


def execute(worktree: Path,
            template_name: str,
            parameter: list[str],
            output: list[str],
            ) -> None:

    lgr.debug(
        'execute: %s %s %s %s', str(worktree),
        template_name, repr(parameter), repr(output))

    assert_annexed(worktree, output)

    # Unlock output files in the worktree-directory
    for o in output:
        call_git_success(
            ['-C', str(worktree), 'annex', 'unlock', o],
            capture_output=True)

    # Run the computation in the worktree-directory
    template_path = worktree / template_dir / template_name
    parameter_dict = {
        p.split('=', 1)[0]: p.split('=', 1)[1]
        for p in parameter
    }
    compute(worktree, template_path, parameter_dict)


def assert_annexed(worktree: Path,
                   files: list[str]
                   ) -> None:

    present_files = list(filter(lambda f: Path(f).exists(), files))
    with contextlib.chdir(worktree):
        with iter_subproc(['git', 'annex', 'info', '--json', '--batch', '-z'],
                          inputs=(file.encode() + b'\x00' for file in present_files),
                          bufsize=0) as results:
            not_annexed = tuple(filter(
                lambda r: r['success'] == False,
                load_json(itemize(results, sep=b'\n'))))
            if not_annexed:
                raise ValueError(
                    f'Output files are not annexed: ' + ', '.join(
                        map(lambda na: na['file'], not_annexed)))


def collect(worktree: Path,
            dataset: Dataset,
            output: list[str],
            ) -> None:

    lgr.debug('collect: %s %s %s', str(worktree), dataset, repr(output))

    # Unlock output files in the dataset-directory and copy the result
    for o in output:
        dest = dataset.pathobj / o
        call_git_success(
            ['-C', dataset.path, 'annex', 'unlock', str(dest)],
            capture_output=True)
        shutil.copyfile(worktree / o, dest)

    # Save the dataset
    dataset.save()


def un_provide(dataset: Dataset,
               worktree: Path,
               ) -> None:

    lgr.debug('un_provide: %s %s', dataset, str(worktree))

    args = ['provide-gitworktree', dataset.path, '--delete', str(worktree)]
    subprocess.run(args, check=True)
