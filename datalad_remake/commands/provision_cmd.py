"""
A data provisioner that works with local git repositories.
Data is provisioned in a temporary worktree. All subdatasets
are currently also provisioned.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from re import Match
from tempfile import TemporaryDirectory
from typing import (
    TYPE_CHECKING,
    ClassVar,
    cast,
)

from datalad_next.commands import (
    EnsureCommandParameterization,
    Parameter,
    ValidatedInterface,
    build_doc,
    datasetmethod,
    eval_results,
    get_status_dict,
)
from datalad_next.constraints import (
    AnyOf,
    DatasetParameter,
    EnsureDataset,
    EnsureListOf,
    EnsurePath,
    EnsureStr,
)
from datalad_next.datasets import Dataset
from datalad_next.runners import call_git_lines, call_git_success

from datalad_remake import PatternPath
from datalad_remake.utils.chdir import chdir
from datalad_remake.utils.glob import glob
from datalad_remake.utils.platform import on_windows
from datalad_remake.utils.read_list import read_list

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable

lgr = logging.getLogger('datalad.remake.provision_cmd')

drive_letter_matcher = re.compile('^[A-Z]:')


# decoration auto-generates standard help
@build_doc
# all commands must be derived from Interface
class Provision(ValidatedInterface):
    # first docstring line is used a short description in the cmdline help
    # the rest is put in the verbose help and manpage
    """Provision inputs for a `make` command

    This command provides a temporary, partial copy of the dataset in a separate
    tree, called a "worktree". The worktree will contain all files that are
    specified by the input patterns. All necessary subdatasets will be
    installed. If a subdataset is locally available in the source dataset, it
    will be installed from there. Its main purpose is to provide an isolated
    environment for `make` commands.
    """

    _validator_ = EnsureCommandParameterization(
        {
            'dataset': EnsureDataset(installed=True),
            'input': EnsureListOf(EnsureStr(min_len=1)),
            'input_list': EnsurePath(),
            'delete': EnsureDataset(installed=True),
            'worktree_dir': AnyOf(EnsurePath(), EnsureStr(min_len=1)),
        }
    )

    # parameters of the command, must be exhaustive
    _params_: ClassVar[dict[str, Parameter]] = {
        'dataset': Parameter(
            args=('-d', '--dataset'),
            doc='Dataset to be used as a configuration source. Beyond '
            'reading configuration items, this command does not interact with '
            'the dataset.',
        ),
        'branch': Parameter(
            args=(
                '-b',
                '--branch',
            ),
            doc='Branch (or commit) that should be provisioned, if '
            'not specified HEAD will be used',
        ),
        'delete': Parameter(
            args=('--delete',),
            doc='Delete the temporary worktree WORKTREE that belongs the the '
            'dataset (cannot be used with `-b`, `--branch`, `-i`,'
            '`--input`, `-I`, or `--input-list`).',
        ),
        'input': Parameter(
            args=(
                '-i',
                '--input',
            ),
            action='append',
            doc='An input file pattern (repeat for multiple inputs, '
            'file pattern support python globbing, globbing is done in the '
            'worktree and through all matching subdatasets, installing '
            'if necessary).',
        ),
        'input_list': Parameter(
            args=(
                '-I',
                '--input-list',
            ),
            doc='Name of a file that contains a list of input file patterns. '
            'Format is one file per line, relative path from `dataset`. '
            'Empty lines, i.e. lines that contain only newlines, and lines '
            "that start with '#' are ignored. Line content is stripped "
            'before used. This is useful if a large number of input file '
            'patterns should be provided.',
        ),
        'worktree_dir': Parameter(
            args=(
                '-w',
                '--worktree-dir',
            ),
            doc='Path of the directory that should become the temporary '
            'worktree, defaults to `tempfile.TemporaryDirectory().name`.',
        ),
    }

    @staticmethod
    @datasetmethod(name='provision')
    @eval_results
    def __call__(
        dataset: DatasetParameter | None = None,
        branch: str | None = None,
        delete: DatasetParameter | None = None,
        input: list[str] | None = None,  # noqa: A002
        input_list: Path | None = None,
        worktree_dir: str | Path | None = None,
    ):
        ds: Dataset = dataset.ds if dataset else Dataset('.')
        if delete:
            if branch or input:
                msg = (
                    'Cannot use `-d`, `--delete` with `-b`, `--branch`,'
                    ' `-i`, or `--input`'
                )
                raise ValueError(msg)

            remove(ds, delete.ds)
            yield get_status_dict(
                action='provision [delete]',
                path=delete.ds.path,
                status='ok',
                message=f'delete workspace: {delete.ds.path!r} from dataset {ds!r}',
            )
            return

        resolved_worktree_dir: Path = Path(worktree_dir or TemporaryDirectory().name)
        inputs = input or [*read_list(input_list)]
        yield from provide(
            dataset=ds,
            input_patterns=[PatternPath(inp) for inp in inputs],
            source_branch=branch,
            worktree_dir=resolved_worktree_dir,
        )


def remove(dataset: Dataset, worktree: Dataset) -> None:
    worktree.drop(
        what='all', reckless='kill', recursive=True, result_renderer='disabled'
    )
    prune_worktrees(dataset)
    call_git_success(['branch', '-d', worktree.pathobj.name], cwd=dataset.pathobj)


def prune_worktrees(dataset: Dataset) -> None:
    call_git_lines(['worktree', 'prune'], cwd=dataset.pathobj)


def provide(
    dataset: Dataset,
    input_patterns: list[PatternPath],
    source_branch: str | None = None,
    worktree_dir: str | Path | None = None,
) -> Generator:
    """Provide paths defined by input_patterns in a temporary worktree

    Parameters
    ----------
    dataset: Dataset
        Dataset that should be provisioned.
    input_patterns: list[PatternPath]
        List of patterns that describe the input files.
    source_branch: str | None
        Branch that should be provisioned, if `None` HEAD will be used.
    worktree_dir: Path | None
        Path to a directory that should contain the provisioned worktree or
        `None`. If `None` a temporary directory will be created.

    Returns
    -------
    Generator
        A generator that yields either a single result with the directory in
        which the dataset was provisioned, or one or more error-results.
    """
    resolved_worktree_dir: Path = Path(
        worktree_dir or TemporaryDirectory().name
    ).absolute()

    lgr.debug('Provisioning dataset %s at %s', dataset, resolved_worktree_dir)

    if on_windows:
        # Create a worktree via `git clone` and check out the requested commit
        args = ['clone', '.', str(resolved_worktree_dir)]
        call_git_lines(args, cwd=dataset.pathobj)
        if source_branch:
            args = ['checkout', source_branch]
            call_git_lines(args, cwd=resolved_worktree_dir)
    else:
        # Create a worktree via `git worktree`
        args = (
            ['worktree', 'add']
            + [str(resolved_worktree_dir)]
            + ([source_branch] if source_branch else [])
        )
        call_git_lines(args, cwd=dataset.pathobj)

    worktree_dataset = Dataset(resolved_worktree_dir)

    # Get all input files in the worktree
    with chdir(worktree_dataset.path):
        for path in resolve_patterns(dataset, worktree_dataset, input_patterns):
            worktree_dataset.get(path, result_renderer='disabled')

    yield get_status_dict(
        action='provision',
        path=str(resolved_worktree_dir),
        status='ok',
        message=f'provisioned dataset: {dataset} in workspace: {worktree_dir!r}',
    )


def resolve_patterns(
    dataset: Dataset,
    worktree: Dataset,
    pattern_list: list[PatternPath],
) -> set[PatternPath]:
    """Resolve file patterns in the dataset

    This method will resolve relative path-patterns in the dataset. It will
    install all subdatasets that are matched by the patterns. Pattern are
    described as outlined in `glob.glob`. The method support recursive globbing
    of zero or more directories with the pattern: `**`.

    Parameters
    ----------
    dataset: Dataset,
        Dataset that should be provisioned.
    worktree : Dataset
        Worktree dataset, in which the patterns should be resolved.
    pattern_list : list[PatternPath]
        List of patterns that should be resolved.

    Returns
    -------
    set[PatternPath]
        Set of paths that match the patterns.
    """
    matches = set()
    for pattern in pattern_list:
        pattern_parts = pattern.parts

        if pattern_parts[0] == '':
            lgr.warning('Ignoring absolute input pattern %s', pattern)
            continue

        matches.update(
            glob_pattern(
                worktree,
                PatternPath(),
                pattern_parts,
                get_uninstalled_subdatasets(worktree),
                get_locally_available_subdatasets(dataset),
            )
        )
    return matches


def get_uninstalled_subdatasets(dataset: Dataset) -> set[PatternPath]:
    """Get relative paths of all visible, non-installed subdatasets"""
    return {
        PatternPath(*Path(result['path']).relative_to(dataset.pathobj).parts)
        for result in dataset.subdatasets(recursive=True, result_renderer='disabled')
        if result['state'] == 'absent'
    }


def glob_pattern(
    root: Dataset,
    position: PatternPath,
    pattern: tuple[str, ...],
    uninstalled_subdatasets: set[PatternPath],
    locally_available_subdatasets: Iterable[tuple[Path, PatternPath, PatternPath]],
) -> set[PatternPath]:
    """Glob a pattern in a dataset installing subdatasets if necessary

    Parameters
    ----------
    root: Dataset
        The dataset in which the pattern should be resolved.
    position: Path
        A relative path that denotes the position in the dataset from which a
        pattern is matched.
    pattern: tuple[str, ...]
        The path-elements of the pattern. For example `['*', 'a', '*.txt']`
        represents the pattern `'*/a/*.txt'` (NOTE: all patterns are denoted
        in Posix convention, i.e. they use `'/'` as separator).
    uninstalled_subdatasets: set[Path]
        A set that contains all currently known uninstalled subdatasets. This
        set will be updated in the method.
    locally_available_subdatasets: set[Path]
        A set that contains all datasets that are available in the dataset for
        which the worktree is created.

    Returns
    -------
    set[PatternPath]
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
            uninstalled_subdatasets,
            locally_available_subdatasets,
        )
    else:
        result = set()

    # Match all elements at the current position with the first part of the
    # pattern.
    for rec_match in glob(
        '*' if pattern[0] == '**' else pattern[0],
        root_dir=root.pathobj / position,
    ):
        match = position / PatternPath(*Path(rec_match).parts)
        system_match = Path(*position.parts) / rec_match

        # If the match is a directory that is in uninstalled subdatasets,
        # install the dataset and updated uninstalled datasets before proceeding
        # with matching the pattern.
        if system_match.is_dir() and match in uninstalled_subdatasets:
            lgr.info('Installing subdataset %s to glob input', match)
            install_subdataset(
                root, match, uninstalled_subdatasets, locally_available_subdatasets
            )

        # We have a match, try to match the remainder of the pattern.
        submatch_pattern = pattern if pattern[0] == '**' else pattern[1:]
        result.update(
            glob_pattern(
                root,
                match,
                submatch_pattern,
                uninstalled_subdatasets,
                locally_available_subdatasets,
            )
        )

    return result


def get_dirty_elements(dataset: Dataset) -> Generator:
    """Get all dirty elements in the dataset"""
    for result in dataset.status(recursive=True):
        if result['type'] == 'file' and result['state'] != 'clean':
            yield result


def install_subdataset(
    worktree: Dataset,
    subdataset_path: PatternPath,
    uninstalled_subdatasets: set[PatternPath],
    locally_available_datasets: Iterable[tuple[Path, PatternPath, PatternPath]],
) -> None:
    """Install a subdataset, prefer locally available subdatasets"""
    local_subdataset = [
        dataset_info
        for dataset_info in locally_available_datasets
        if dataset_info[2] == subdataset_path
    ]

    if local_subdataset:
        absolute_path, parent_ds_path, path_from_root = local_subdataset[0]
        # Set the URL to the full source path
        submodule_name = str(path_from_root.relative_to(parent_ds_path))
        args = [
            '-C',
            str(worktree.pathobj / parent_ds_path),
            'submodule',
            'set-url',
            '--',
            submodule_name,
            absolute_path.as_uri(),
        ]
        call_git_lines(args)
        args = [
            '-C',
            str(worktree.pathobj / parent_ds_path),
            'config',
            '-f',
            '.gitmodules',
            '--replace-all',
            f'submodule.{submodule_name}.datalad-url',
            absolute_path.as_uri(),
        ]
        call_git_lines(args)
    worktree.get(str(subdataset_path), get_data=False, result_renderer='disabled')
    uninstalled_subdatasets.remove(subdataset_path)
    uninstalled_subdatasets.update(get_uninstalled_subdatasets(worktree))


def get_locally_available_subdatasets(
    dataset: Dataset,
) -> Iterable[tuple[Path, PatternPath, PatternPath]]:
    """Get all locally available subdatasets in the dataset `dataset

    A subdataset is locally available if it is:

    1. installed in the dataset, or
    2. it is not installed in the dataset, but its submodule-URL is a relative
       path.
    3. it is not installed in the dataset, but its submodule-URL is an absolute
       path.

    In case 1.) the install-URL is the file-URL of the subdataset in `dataset`.
    In case 2.) the install-URL is the origin of the dataset joined by the
    relative submodule-URL
    In case 3.) the install-URL is the submodule-URL.
    """
    results = dataset.subdatasets(recursive=True, result_renderer='disabled')
    installed_subdatasets = [
        (
            # Absolute OS-specific path of the subdataset
            Path(result['path']),
            # Relative path of the parent dataset in the root dataset
            PatternPath(*Path(result['parentds']).relative_to(dataset.pathobj).parts),
            # Relative path of the subdataset in the root dataset
            PatternPath(*Path(result['path']).relative_to(dataset.pathobj).parts),
        )
        for result in results
        if result['state'] == 'present'
    ]
    local_subdatasets = [
        (
            # Absolute OS-specific path of the subdataset
            Path(resolve_relative_module_url(dataset, result)),
            PatternPath(*Path(result['parentds']).relative_to(dataset.pathobj).parts),
            PatternPath(*Path(result['path']).relative_to(dataset.pathobj).parts),
        )
        for result in results
        if result['state'] == 'absent'
        and result['gitmodule_url'].startswith(('./', '../'))
    ]
    return installed_subdatasets + local_subdatasets


def resolve_relative_module_url(
    dataset: Dataset, submodule_info: dict[str, str]
) -> str:
    """Resolve the relative path in a submodule URL"""

    if submodule_info['gitmodule_url'].startswith(('./', '../')):
        # If the submodule URL is a relative path, it has to be resolved against
        # the origin its parent dataset.
        return get_parent_dataset_origin(dataset, submodule_info)
    return submodule_info['gitmodule_url'].replace('file://', '')


def get_parent_dataset_origin(dataset: Dataset, submodule_info: dict) -> str:
    """Get an absolute remote_url of the parent dataset"""

    remote_url = get_remote_url(dataset)

    # If the remote_url is an absolute or relative path, resolve it against
    # the parent dataset's path.
    if Path(remote_url).is_absolute():
        # This is an absolute file-URL, append the submodule-URL
        return str(
            (Path(remote_url) / submodule_info['gitmodule_url']).resolve().absolute()
        )

    if remote_url.startswith(('./', '../')):
        # This is a relative file-URL, create an absolute path based on the
        # dataset path, the relative URL and the submodule-URL.
        return str(
            (dataset.pathobj / remote_url / submodule_info['gitmodule_url'])
            .resolve()
            .absolute()
        )

    # This is a fully qualified URL, return it.
    return submodule_info['gitmodule_url']


def get_remote_url(dataset: Dataset) -> str:
    # Collect all remote URLs
    remotes = {
        cast(Match[str], re.match(r'^remote\.(.*)\.url', k))[1]: dataset.config.get(
            cast(Match[str], re.match(r'^remote\.(.*)\.url', k))[0]
        )
        for k in dataset.config.keys()  # noqa SIM118
        if re.match(r'^remote\.(.*)\.url', k)
    }

    # Look for file URLs, return the first (that might not be correct in any
    # case, because we need a remote that has the current sha).
    for remote, url in remotes.items():
        if is_file_url(url):
            lgr.debug('get_remote_url: using remote %s with URL %s', remote, url)
            return url

    # If there are no remotes, return the path of the dataset
    return dataset.path


def is_file_url(url: str) -> bool:
    starts_with_drive_letter = (
        drive_letter_matcher.match(url) is not None if on_windows else False
    )
    return url.startswith(('/', './', '../')) or starts_with_drive_letter
