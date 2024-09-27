"""DataLad compute command"""

from __future__ import annotations

import contextlib
import glob
import json
import logging
import os
import shutil
import subprocess
from itertools import chain
from pathlib import Path
from typing import Iterable
from urllib.parse import quote

from datalad.support.exceptions import IncompleteResultsError
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
from datalad_next.runners import (
    call_git_oneline,
    call_git_success,
)
from hypothesis.strategies import recursive

from .. import (
    template_dir,
    url_scheme,
)
from ..utils.compute import compute


__docformat__ = 'restructuredtext'


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
        input=EnsureListOf(EnsureStr(min_len=1)),
        input_list=EnsureStr(min_len=1),
        output=EnsureListOf(EnsureStr(min_len=1), min_len=1),
        output_list=EnsureStr(min_len=1),
        parameter=EnsureListOf(EnsureStr(min_len=3)),
        parameter_list=EnsureStr(min_len=1),
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
            doc="Name of an input file pattern (repeat for multiple inputs), "
                "file pattern support python globbing"),
        input_list=Parameter(
            args=('-I', '--input-list',),
            doc="Name of a file that contains a list of input file patterns. "
                "Format is one file per line, relative path from `dataset`. "
                "Empty lines, i.e. lines that contain only newlines, and lines "
                "that start with '#' are ignored. Line content is stripped "
                "before used. This is useful if a large number of input file "
                "patterns should be provided."),
        output=Parameter(
            args=('-o', '--output',),
            action='append',
            doc="Name of an output file (repeat for multiple outputs)"),
        output_list=Parameter(
            args=('-O', '--output-list',),
            doc="Name of a file that contains a list of output file patterns. "
                "Format is one file per line, relative path from `dataset`. "
                "Empty lines, i.e. lines that contain only newlines, and lines "
                "that start with '#' are ignored. Line content is stripped "
                "before used. This is useful if a large number of output file "
                "patterns should be provided."),
        parameter=Parameter(
            args=('-p', '--parameter',),
            action='append',
            doc="Input parameter in the form <name>=<value> (repeat for "
                "multiple parameters)"),
        parameter_list=Parameter(
            args=('-P', '--parameter-list',),
            doc="Name of a file that contains a list of parameters. Format "
                "is one `<name>=<value>` string per line. "
                "Empty lines, i.e. lines that contain only newlines, and lines "
                "that start with '#' are ignored. Line content is stripped "
                "before used. This is useful if a large number of parameters "
                "should be provided."),
    )


    @staticmethod
    @datasetmethod(name='compute')
    @eval_results
    def __call__(dataset=None,
                 url_only=False,
                 template=None,
                 branch=None,
                 input=None,
                 input_list=None,
                 output=None,
                 output_list=None,
                 parameter=None,
                 parameter_list=None,
                 ):

        dataset : Dataset = dataset.ds if dataset else Dataset('.')

        input_pattern = (input or []) + read_list(input_list)
        output_pattern = (output or []) + read_list(output_list)
        parameter = (parameter or []) + read_list(parameter_list)

        if not url_only:
            worktree = provide(dataset, branch, input_pattern)
            execute(worktree, template, parameter, output_pattern)
            output_files = collect(worktree, dataset, output_pattern)
            un_provide(dataset, worktree)

        url_base = get_url(
            dataset,
            branch,
            template,
            parameter,
            input_pattern,
            output_pattern)

        for out in (output_pattern if url_only else output_files):
            url = add_url(dataset, out, url_base, url_only)
            yield get_status_dict(
                    action='compute',
                    path=dataset.pathobj / out,
                    status='ok',
                    message=f'added url: {url!r} to {out!r} in {dataset.pathobj}',)


def read_list(list_file: str | Path | None) -> list[str]:
    if list_file is None:
        return []
    return list(filter(
        lambda s: s != '' and not s.startswith('#'),
        [
            line.strip()
            for line in Path(list_file).read_text().splitlines(keepends=False)
        ]))


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
    success = call_git_success(
        ['-C', str(file_dataset_path), 'annex', 'addurl', url, '--file', file_path]
        + (['--relaxed'] if url_only else []),
        capture_output=True,)

    assert success, f'\naddurl failed:\nfile_dataset_path: {file_dataset_path}\nurl: {url!r}\nfile_path: {file_path!r}'
    return url


def get_file_dataset(file: Path) -> tuple[Path, Path]:
    """ Get dataset of file and relative path of file from the dataset

    Determine the path of the dataset that contains the file and the relative
    path of the file in this dataset."""
    top_level = Path(call_git_oneline(
        ['-C', str(file.parent), 'rev-parse', '--show-toplevel']
    ))
    return (
        Path(top_level),
        file.absolute().relative_to(top_level))


def provide(dataset: Dataset,
            branch: str | None,
            input_patterns: list[str],
            ) -> Path:

    lgr.debug('provide: %s %s %s', dataset, branch, input_patterns)

    args = ['provide-gitworktree', dataset.path, ] + (
        ['--branch', branch] if branch else []
    )
    args.extend(chain(*[('--input', i) for i in (input_patterns or [])]))
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

    # Get the subdatasets, directories, and files that are part of the output
    # space.
    create_output_space(Dataset(worktree), output)

    # Unlock output files in the worktree-directory
    unlock_files(Dataset(worktree), output)

    # Run the computation in the worktree-directory
    template_path = worktree / template_dir / template_name
    parameter_dict = {
        p.split('=', 1)[0]: p.split('=', 1)[1]
        for p in parameter
    }
    compute(worktree, template_path, parameter_dict)


def collect(worktree: Path,
            dataset: Dataset,
            output_patterns: list[str],
            ) -> Iterable[str]:

    lgr.debug(
        'collect: %s %s %s',
        str(worktree), dataset, repr(output_patterns))

    # Get the list of created output files based on the output patterns
    output_files = set(
        chain.from_iterable(
            glob.glob(pattern, root_dir=worktree, recursive=True)
            for pattern in output_patterns))

    # Unlock output files in the dataset-directory and copy the result
    unlock_files(dataset, output_files)
    for o in output_files:
        destination = dataset.pathobj / o
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(worktree / o, destination)

    # Save the dataset
    dataset.save(recursive=True, result_renderer='disabled')
    return output_files


def unlock_files(dataset: Dataset,
                 files: Iterable[str]
                 ) -> None:
    """Use datalad to resolve subdatasets and unlock files in the dataset."""
    # TODO: for some reason `dataset unlock` does not operate in the
    #  context of `dataset.pathobj`, so we need to change the working
    #  directory manually here.
    with contextlib.chdir(dataset.pathobj):
        for f in files:
            file = dataset.pathobj / f
            if not file.exists() and file.is_symlink():
                # `datalad unlock` does not "unlock" dangling symlinks, so we
                # mimic the behavior of `git annex unlock` here:
                link = os.readlink(file)
                file.unlink()
                file.write_text('/annex/objects/' + link.split('/')[-1] + '\n')
            elif file.is_symlink():
                dataset.unlock(file, result_renderer='disabled')


def create_output_space(dataset: Dataset,
                        files: list[str]
                        ) -> None:
    """Get all files that are part of the output space."""
    for f in files:
        try:
            dataset.get(f, result_renderer='disabled')
        except IncompleteResultsError:
            # The file does not yet exist. The computation should create it.
            # We create the directory here.
            (dataset.pathobj / f).parent.mkdir(parents=True, exist_ok=True)


def un_provide(dataset: Dataset,
               worktree: Path,
               ) -> None:

    lgr.debug('un_provide: %s %s', dataset, str(worktree))

    args = ['provide-gitworktree', dataset.path, '--delete', str(worktree)]
    subprocess.run(args, check=True)
