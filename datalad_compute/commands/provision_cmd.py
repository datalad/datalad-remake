"""
A data provisioner that works with local git repositories.
Data is provisioned in a temporary worktree. All subdatasets
are currently also provisioned.
"""
from __future__ import annotations

import logging
import random
import shutil
import stat
from contextlib import chdir
from pathlib import Path
from typing import Iterable
from tempfile import TemporaryDirectory

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
    EnsureStr, EnsurePath,
)
from datalad_next.datasets import Dataset
from datalad_next.runners import call_git_lines

from datalad_compute.utils.glob import resolve_patterns
from ..commands.compute_cmd import read_list


__docformat__ = 'restructuredtext'


lgr = logging.getLogger('datalad.compute.provision_cmd')


# decoration auto-generates standard help
@build_doc
# all commands must be derived from Interface
class Provision(ValidatedInterface):
    # first docstring line is used a short description in the cmdline help
    # the rest is put in the verbose help and manpage
    """Provision inputs for a compute command
    """

    _validator_ = EnsureCommandParameterization(dict(
        dataset=EnsureDataset(installed=True),
        input=EnsureListOf(EnsureStr(min_len=1)),
        input_list=EnsureStr(min_len=1),
        tmp_dir=EnsurePath(is_mode=stat.S_ISDIR),
        delete=EnsurePath(lexists=True, is_mode=stat.S_ISDIR),
    ))

    # parameters of the command, must be exhaustive
    _params_ = dict(
        dataset=Parameter(
            args=('-d', '--dataset'),
            doc="Dataset to be used as a configuration source. Beyond "
                "reading configuration items, this command does not interact with "
                "the dataset."),
        branch=Parameter(
            args=('-b', '--branch',),
            doc="Branch (or commit) that should be provisioned, if "
                "not specified HEAD will be used"),
        delete=Parameter(
            args=('--delete',),
            doc="Delete the temporary worktree WORKTREE that belongs the the "
                "dataset (cannot be used with `-b`, `--branch`, `-i`, or "
                "`--input`)"),
        input=Parameter(
            args=('-i', '--input',),
            action='append',
            doc="An input file pattern (repeat for multiple inputs, "
                "file pattern support python globbing, globbing is expanded "
                "in the source dataset"),
        input_list=Parameter(
            args=('-I', '--input-list',),
            doc="Name of a file that contains a list of input file patterns. "
                "Format is one file per line, relative path from `dataset`. "
                "Empty lines, i.e. lines that contain only newlines, and lines "
                "that start with '#' are ignored. Line content is stripped "
                "before used. This is useful if a large number of input file "
                "patterns should be provided."),
        temp_dir=Parameter(
            args=('-t', '--temp-dir',),
            doc="Path of the directory where temporary worktrees should be "
                "created. The  default is `$TMP` if set, otherwise `/tmp`."),
    )

    @staticmethod
    @datasetmethod(name='compute')
    @eval_results
    def __call__(dataset=None,
                 branch=None,
                 delete=None,
                 input=None,
                 input_list=None,
                 temp_dir=None,
                 ):

        dataset : Dataset = dataset.ds if dataset else Dataset('.')
        if delete:
            if branch or input:
                raise ValueError(
                    'Cannot use `-d`, `--delete` with `-b`, `--branch`,'
                    ' `-i`, or `--input`')

            remove(dataset, delete)
            yield get_status_dict(
                action='provision [delete]',
                path=delete,
                status='ok',
                message=f'delete workspace: {delete!r} from dataset {dataset}',)

        temp_dir: Path = temp_dir or Path(TemporaryDirectory().name)
        inputs = input or [] + read_list(input_list)
        provision_dir = provide(dataset, temp_dir, branch, inputs)
        yield get_status_dict(
            action='provision',
            path=str(provision_dir),
            status='ok',
            message=f'provisioned dataset: {dataset} in workspace: {provision_dir!r}',)


def remove(dataset: Dataset,
           worktree: str
           ) -> None:
    remove_subdatasets(worktree)
    shutil.rmtree(worktree)
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
    call_git_lines(['worktree', 'prune'], cwd=dataset.pathobj)
    for result in dataset.subdatasets(result_renderer='disabled'):
        prune_worktrees(Dataset(result['path']))


def provide(dataset: Dataset,
            worktree_dir: Path,
            source_branch: str | None = None,
            input_patterns: Iterable[str] | None = None,
            ) -> Path:

    lgr.debug('Provisioning dataset %s at %s', dataset, worktree_dir)

    worktree_dir.mkdir(parents=True, exist_ok=True)
    worktree_name = worktree_dir.parts[-1]

    # Resolve input file patterns in the original dataset
    input_files = resolve_patterns(dataset.path, input_patterns)

    # Create a worktree
    args = ['worktree', 'add', '-b', worktree_name] + [str(worktree_dir)] + (
        [source_branch]
        if source_branch
        else []
    )
    call_git_lines(args, cwd=dataset.pathobj)

    # Get all input files in the worktree
    worktree_dataset = Dataset(worktree_dir)
    with chdir(worktree_dataset.path):
        for file in input_files:
            lgr.debug('Provisioning file %s', file)
            worktree_dataset.get(file, result_renderer='disabled')

    return worktree_dir
