"""
A data provisioner that works with local git repositories.
Data is provisioned in a temporary worktree. All subdatasets
are currently also provisioned.
"""
from __future__ import annotations

import logging
import os
import stat
from contextlib import chdir
from glob import glob
from pathlib import Path
from typing import (
    Iterable,
    Generator,
)
from tempfile import TemporaryDirectory

from datalad.support.constraints import EnsureBool
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
from datalad_next.runners import call_git_lines, call_git_success

from ..commands.compute_cmd import read_list


lgr = logging.getLogger('datalad.compute.provision_cmd')


# decoration auto-generates standard help
@build_doc
# all commands must be derived from Interface
class Provision(ValidatedInterface):
    # first docstring line is used a short description in the cmdline help
    # the rest is put in the verbose help and manpage
    """Provision inputs for a compute command

    This command provides a temporary, partial copy of the dataset in a separate
    tree, called a "worktree". The worktree will contain all files that are
    specified by the input patterns. All necessary subdatasets will be
    installed. If a subdataset is locally available in the source dataset, it
    will be installed from there. Its main purpose is to provide an isolated
    environment for "compute" commands.
    """

    _validator_ = EnsureCommandParameterization(dict(
        dataset=EnsureDataset(installed=True),
        input=EnsureListOf(EnsureStr(min_len=1)),
        input_list=EnsureStr(min_len=1),
        tmp_dir=EnsurePath(is_mode=stat.S_ISDIR),
        delete=EnsureDataset(installed=True),
        no_globbing=EnsureBool(),
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
                "dataset (cannot be used with `-b`, `--branch`, `-i`,"
                "`--input`, `-I`, or `--input-list`)."),
        input=Parameter(
            args=('-i', '--input',),
            action='append',
            doc="An input file pattern (repeat for multiple inputs, "
                "file pattern support python globbing, globbing is done in the "
                "worktree and through all matching subdatasets, installing "
                "if necessary)."),
        input_list=Parameter(
            args=('-I', '--input-list',),
            doc="Name of a file that contains a list of input file patterns. "
                "Format is one file per line, relative path from `dataset`. "
                "Empty lines, i.e. lines that contain only newlines, and lines "
                "that start with '#' are ignored. Line content is stripped "
                "before used. This is useful if a large number of input file "
                "patterns should be provided."),
        worktree_dir=Parameter(
            args=('-w', '--worktree-dir',),
            doc="Path of the directory that should become the temporary "
                "worktree, defaults to `tempfile.TemporaryDirectory().name`."),
    )

    @staticmethod
    @datasetmethod(name='provision')
    @eval_results
    def __call__(dataset=None,
                 branch=None,
                 delete=None,
                 input=None,
                 input_list=None,
                 worktree_dir=None,
                 ):

        dataset : Dataset = dataset.ds if dataset else Dataset('.')
        if delete:
            if branch or input:
                raise ValueError(
                    'Cannot use `-d`, `--delete` with `-b`, `--branch`,'
                    ' `-i`, or `--input`')

            remove(dataset, delete.ds)
            yield get_status_dict(
                action='provision [delete]',
                path=delete.ds.path,
                status='ok',
                message=f'delete workspace: {delete.ds.path!r} from dataset {dataset}')
            return

        worktree_dir: Path = Path(worktree_dir or TemporaryDirectory().name)
        inputs = input or [] + read_list(input_list)
        yield from provide(dataset, worktree_dir, inputs, branch)


def remove(dataset: Dataset,
           worktree: Dataset
           ) -> None:
    worktree.drop(
        what='all',
        reckless='kill',
        recursive=True,
        result_renderer='disabled')
    prune_worktrees(dataset)
    call_git_success(
        ['branch', '-d', worktree.pathobj.name],
        cwd=dataset.pathobj)


def prune_worktrees(dataset: Dataset) -> None:
    call_git_lines(['worktree', 'prune'], cwd=dataset.pathobj)


def provide(dataset: Dataset,
            worktree_dir: Path,
            input_patterns: list[str],
            source_branch: str | None = None,
            ) -> Generator:
    """Provide paths defined by input_patterns in a temporary worktree

    Parameters
    ----------
    dataset: Dataset
        Dataset that should be provisioned
    worktree_dir: Path
        Path to a directory that should contain the provisioned worktree
    input_patterns: list[str]
        List of patterns that describe the input files
    source_branch: str | None
        Branch that should be provisioned, if None HEAD will be used [optional]

    Returns
    -------

    """

    lgr.debug('Provisioning dataset %s at %s', dataset, worktree_dir)

    worktree_dir.mkdir(parents=True, exist_ok=True)

    # Create a worktree
    args = ['worktree', 'add'] + [str(worktree_dir)] + (
        [source_branch]
        if source_branch
        else []
    )
    call_git_lines(args, cwd=dataset.pathobj)

    is_dirty = False
    for element in get_dirty_elements(dataset):
        is_dirty = True
        yield get_status_dict(
            action='provision',
            path=element['path'],
            status='error',
            state=element['state'],
            message=f'cannot provision {element["state"]} input: {element["path"]!r} from dataset {dataset}')
    if is_dirty:
        return

    worktree_dataset = Dataset(worktree_dir)

    # Get all input files in the worktree
    with chdir(worktree_dataset.path):
        for path in resolve_patterns(worktree_dataset, input_patterns):
            worktree_dataset.get(path)

    yield get_status_dict(
        action='provision',
        path=str(worktree_dir),
        status='ok',
        message=f'provisioned dataset: {dataset} in workspace: {worktree_dir!r}',)


def resolve_patterns(dataset: Dataset,
                     pattern_list: list[str]
                     ) -> set[Path]:
    """Resolve file patterns in the dataset

    This method will resolve relative path-patterns in the dataset. It will
    install all subdatasets that are matched by the patterns. Pattern are
    described as outline in `glob.glob`. The method support recursive globbing
    of zero or more directories with the pattern: `**`.

    Parameters
    ----------
    dataset : Dataset
        Dataset in which the patterns should be resolved.
    pattern_list : list[str]
        List of patterns thatThat should be resolved.

    Returns
    -------
    set[Path]
        Set of paths that match the patterns.
    """
    matches = set()
    for pattern in pattern_list:
        pattern_parts = pattern.split(os.sep)

        if pattern_parts[0] == '':
            lgr.warning('Ignoring absolute input pattern %s', pattern)
            continue

        matches.update(
            glob_pattern(
                dataset,
                Path(),
                pattern_parts,
                get_uninstalled_subdatasets(dataset)))
    return matches


def get_uninstalled_subdatasets(dataset: Dataset) -> set[Path]:
    """Get a list of the paths of all visible, non-installed subdatasets"""
    return set([
        Path(result['path']).relative_to(dataset.pathobj)
        for result in dataset.subdatasets(recursive=True, result_renderer='disabled')
        if result['state'] == 'absent'])


def glob_pattern(root: Dataset,
                 position: Path,
                 pattern: list[str],
                 uninstalled_subdatasets: set[Path],
                 ) -> set[Path]:
    """Glob a pattern in a dataset installing subdatasets if necessary

    Parameters
    ----------
    root: Dataset
        The dataset in which the pattern should be resolved.
    position: Path
        A relative path that denotes the position in the dataset from which a
        pattern is matched.
    pattern: list[str]
        The path-elements of the pattern. For example `['*', 'a', '*.txt']`
        represents the pattern `'*/a/*.txt'`.
    uninstalled_subdatasets: set[Path]
        A set that contains all currently known uninstalled subdatasets. This
        set will be updated in the method

    Returns
    -------
    set[Path]
        A set that contains all paths that match the pattern.
    """
    if not pattern:
        return {position}

    # If the pattern starts with `**` we have to glob the remainder of the
    # pattern from this position.
    if pattern[0] == '**':
        result = glob_pattern(
            root,
            position,
            pattern[1:],
            uninstalled_subdatasets)
    else:
        result = set()

    # Match all elements at the current position with the first part of the
    # pattern.
    for match in glob(
            '*' if pattern[0] == '**' else pattern[0],
            root_dir=root.pathobj / position
    ):
        match = position / match

        # If the match is a directory that is in uninstalled subdatasets,
        # install the dataset and updated uninstalled datasets before proceeding
        # with matching the pattern.
        if match.is_dir() and match in uninstalled_subdatasets:
            lgr.info('Installing subdataset %s to glob input', match)
            root.get(str(match), get_data=False, result_renderer='disabled')
            uninstalled_subdatasets.remove(match)
            uninstalled_subdatasets.update(get_uninstalled_subdatasets(root))

        # We have a match, try to match the remainder of the pattern.
        submatch_pattern = pattern if pattern[0] == '**' else pattern[1:]
        result.update(glob_pattern(root, match, submatch_pattern, uninstalled_subdatasets))
    return result


def get_dirty_elements(dataset: Dataset) -> Generator:
    """Get all dirty elements in the dataset"""
    for result in dataset.status(recursive=True):
        if result['type'] == 'file' and result['state'] != 'clean':
            yield result


def install_required_locally_available_datasets(root_dataset: Dataset,
                                                input_files: list[Path],
                                                worktree: Dataset,
                                                ) -> None:
    """Ensure that local and locally changed subdatasets can be provisioned.

    If subdatasets are only available within the root dataset, either because
    they are not published or because they are locally modified, the provision
    has to use those.

    This means we have to adapt cloning candidates before trying to install
    a subdataset. This is done by:

    - Determining which subdatasets are installed in the root dataset
    - Determining which of those subdatasets are required by the input files
    - Adjust the `.gitmodules` files and install the required local datasets
    - All other datasets are installed as usual, e.g. via `datalad get`.
    """

    # Determine which subdatasets are installed in the root dataset
    subdataset_info = get_subdataset_info(root_dataset)

    # Determine which subdatasets are required by the input files
    required_subdatasets = determine_required_subdatasets(
        subdataset_info,
        input_files)

    install_locally_available_subdatasets(
        root_dataset,
        required_subdatasets,
        worktree)


def get_subdataset_info(dataset: Dataset) -> Iterable[tuple[Path, Path, Path]]:
    results = dataset.subdatasets(
        recursive=True,
        result_renderer='disabled')
    return [
        (
            Path(result['path']),
            Path(result['parentds']),
            Path(result['path']).relative_to(dataset.pathobj)
        )
        for result in results
        if result['state'] == 'present'
    ]


def determine_required_subdatasets(subdataset_info: Iterable[tuple[Path, Path, Path]],
                                   input_files: list[Path],
                                   ) -> set[tuple[Path, Path, Path]]:
    required_set = set()
    for file in input_files:
        # if the path can be expressed as relative to the subdataset path.
        # the subdataset is required, and so are all subdatasets above it.
        for subdataset_path, parent_path, path_from_root in subdataset_info:
            try:
                file.relative_to(path_from_root)
                required_set.add((subdataset_path, parent_path, path_from_root))
            except ValueError:
                pass
    return required_set


def install_locally_available_subdatasets(source_dataset: Dataset,
                                          required_subdatasets: set[tuple[Path, Path, Path]],
                                          worktree: Dataset,
                                          ) -> None:
    """Install the required subdatasets from the source dataset in the worktree.
    """
    todo = [Path('.')]
    while todo:
        current_root = todo.pop()
        for subdataset_path, parent_path, path_from_root in required_subdatasets:
            if not current_root == parent_path.relative_to(source_dataset.pathobj):
                continue
            # Set the URL to the full source path
            args = ['-C', str(worktree.pathobj / current_root),
                    'submodule', 'set-url', '--',
                    str(subdataset_path.relative_to(parent_path)),
                    'file://' + str(source_dataset.pathobj / path_from_root)]
            call_git_lines(args)
            worktree.get(
                path_from_root,
                get_data=False,
                result_renderer='disabled')
            todo.append(path_from_root)
