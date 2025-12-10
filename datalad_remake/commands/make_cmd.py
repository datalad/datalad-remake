"""DataLad make command"""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import quote

from datalad.support.exceptions import IncompleteResultsError
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
    DatasetParameter,
    EnsureDataset,
    EnsureListOf,
    EnsurePath,
    EnsureStr,
)
from datalad_next.datasets import Dataset
from datalad_next.runners import (
    call_git_oneline,
    call_git_success,
)

from datalad_remake import (
    PatternPath,
    specification_dir,
    template_dir,
    url_scheme,
)
from datalad_remake.commands import provision_cmd
from datalad_remake.utils.chdir import chdir
from datalad_remake.utils.compute import compute
from datalad_remake.utils.getconfig import get_trusted_keys
from datalad_remake.utils.glob import resolve_patterns
from datalad_remake.utils.read_list import read_list
from datalad_remake.utils.remake_remote import add_remake_remote
from datalad_remake.utils.verify import verify_file

if TYPE_CHECKING:
    from collections.abc import (
        Generator,
        Iterable,
    )
    from typing import ClassVar

lgr = logging.getLogger('datalad.remake.make_cmd')


# decoration auto-generates standard help
@build_doc
# all commands must be derived from Interface
class Make(ValidatedInterface):
    # first docstring line is used a short description in the cmdline help
    # the rest is put in the verbose help and manpage
    """Specify a computation and optionally execute it"""

    _validator_ = EnsureCommandParameterization(
        {
            'dataset': EnsureDataset(installed=True),
            'template': EnsureStr(min_len=1),
            'label': EnsureStr(),
            'input': EnsureListOf(EnsureStr(min_len=1)),
            'input_list': EnsurePath(),
            'output': EnsureListOf(EnsureStr(min_len=1), min_len=1),
            'output_list': EnsurePath(),
            'parameter': EnsureListOf(EnsureStr(min_len=3)),
            'parameter_list': EnsurePath(),
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
        'prospective_execution': Parameter(
            args=('--prospective-execution',),
            action='store_true',
            doc="Don't perform the computation now, only register compute "
            'instructions, `datalad get <file>` or `git annex get <file>` '
            'will trigger the computation.  \n'
            'Note: if this option is provided, input- and output-patterns will '
            'be stored verbatim. Input globbing will be performed '
            'when the computation is triggered. But the name of the output '
            'files that are created will be the verbatim output pattern '
            'strings.',
        ),
        'template': Parameter(
            args=('template',),
            doc='Name of the computing template (template should be present '
            'in $DATASET/.datalad/remake/methods/)',
        ),
        'label': Parameter(
            args=('--label',),
            doc='Label of the computation. This is a user defined name that '
            'is used to identify and prioritize computations, if more than one '
            'computation is registered for a file. If no label is provided, '
            'the template name will be used. Prioritization is done by '
            'reading the git configuration `datalad.make.priority` (which '
            'should contain a comma-separated list of labels). If this '
            'configuration key does not exist, the priority list is read from '
            'the file `$DATASET/.datalad/make/priority`. If that does not '
            'exist either, a random computation is chosen.',
        ),
        'branch': Parameter(
            args=(
                '-b',
                '--branch',
            ),
            doc='Branch (or commit) that should be used for computation, if '
            'not specified HEAD will be used',
        ),
        'input': Parameter(
            args=(
                '-i',
                '--input',
            ),
            action='append',
            doc='An input file pattern (repeat for multiple inputs). '
            'File patterns support python globbing, globbing is performed by '
            'installing all possibly matching subdatasets and performing '
            'globbing in those, recursively. That means expressions like `**` '
            'might pull in a huge number of datasets. Input file patterns '
            'must be relative, they are dereferenced from the root of the '
            'dataset.',
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
            'before being used. This is useful if a large number of input file '
            'patterns should be provided.',
        ),
        'output': Parameter(
            args=(
                '-o',
                '--output',
            ),
            action='append',
            doc='An output file pattern (repeat for multiple outputs)'
            'file pattern support python globbing, output globbing is performed '
            'in the worktree after the computation). Output file patterns '
            'must be relative, they are dereferenced from the root of the '
            'dataset.',
        ),
        'output_list': Parameter(
            args=(
                '-O',
                '--output-list',
            ),
            doc='Name of a file that contains a list of output file patterns. '
            'Format is one file per line, relative path from `dataset`. '
            'Empty lines, i.e. lines that contain only newlines, and lines '
            "that start with '#' are ignored. Line content is stripped "
            'before being used. This is useful if a large number of output '
            'file patterns should be provided.',
        ),
        'parameter': Parameter(
            args=(
                '-p',
                '--parameter',
            ),
            action='append',
            doc='Input parameter in the form <name>=<value> (repeat for '
            'multiple parameters).',
        ),
        'parameter_list': Parameter(
            args=(
                '-P',
                '--parameter-list',
            ),
            doc='Name of a file that contains a list of parameters. Format '
            'is one `<name>=<value>` string per line. '
            'Empty lines, i.e. lines that contain only newlines, and lines '
            "that start with '#' are ignored. Line content is stripped "
            'before being used. This is useful if a large number of parameters '
            'should be provided.',
        ),
        'stdout': Parameter(
            args=(
                '-s',
                '--stdout',
            ),
            default=None,
            doc='Name of a file that will receive `stdout` output from the '
            'computation. If not given, `stdout` output will be discarded. '
            'It is preferable to NOT add the `stdout` file to the dataset on '
            'which the computation is performed. The reason is that `stdout` '
            'output tends to differ between runs, for example due to time '
            'stamps or other non-deterministic factors.',
        ),
        'allow_untrusted_execution': Parameter(
            args=('--allow-untrusted-execution',),
            action='store_true',
            default=False,
            doc='Skip commit signature verification before executing code. This '
            'should only be used in a strictly controlled environment with '
            'fully trusted datasets. Fully trusted dataset means: every commit '
            'stems from a trusted entity. This option has no effect when '
            'combined with `--prospective-execution`.  '
            'DO NOT USE THIS OPTION, unless you are sure to understand the '
            'consequences. One of which is that arbitrary parties can '
            'execute arbitrary code under your account on your '
            'infrastructure.',
        ),
    }

    @staticmethod
    @datasetmethod(name='make')
    @eval_results
    def __call__(
        dataset: DatasetParameter | None = None,
        *,
        template: str = '',
        label: str = '',
        prospective_execution: bool = False,
        branch: str | None = None,
        input: list[str] | None = None,  # noqa: A002
        input_list: Path | None = None,
        output: list[str] | None = None,
        output_list: Path | None = None,
        parameter: list[str] | None = None,
        parameter_list: Path | None = None,
        stdout: str | None = None,
        allow_untrusted_execution: bool = False,
    ) -> Generator:
        ds: Dataset = dataset.ds if dataset else Dataset('.')

        input_pattern = list(map(PatternPath, (input or []) + read_list(input_list)))
        output_pattern = list(map(PatternPath, (output or []) + read_list(output_list)))
        stdout_path = None if stdout is None else PatternPath(stdout)

        parameter_dict = dict(
            [p.split('=', 1) for p in (parameter or []) + read_list(parameter_list)]
        )

        # We have to get the URL first, because saving the specification to
        # the dataset will change the version.
        url_base, reset_commit = get_url(
            ds,
            branch,
            template,
            parameter_dict,
            input_pattern,
            output_pattern,
            stdout_path,
            label or template,
        )

        if not prospective_execution:
            with provide_context(
                ds,
                branch,
                input_pattern,
            ) as worktree:
                execute(
                    worktree,
                    template,
                    parameter_dict,
                    output_pattern,
                    stdout_path,
                    None if allow_untrusted_execution else get_trusted_keys(),
                )
                resolved_output = collect(worktree, ds, output_pattern, stdout_path)
        else:
            if allow_untrusted_execution:
                lgr.warning(
                    '--allow-untrusted-execution has no effect if '
                    '--prospective-execution`is provided.'
                )
            resolved_output = set(output_pattern)

        initialize_remotes(ds, resolved_output)

        for out in resolved_output:
            url = add_url(ds, out, url_base, url_only=prospective_execution)
            yield get_status_dict(
                action='make',
                path=str(ds.pathobj / out),
                status='ok',
                message=f'added url: {url!r} to {out!r} in {ds.pathobj}',
            )


def get_url(
    dataset: Dataset,
    branch: str | None,
    template_name: str,
    parameters: dict[str, str],
    input_pattern: list[PatternPath],
    output_pattern: list[PatternPath],
    stdout: PatternPath | None,
    label: str,
) -> tuple[str, str]:
    # If something goes wrong after the compute specification was saved,
    # the dataset state should be reset to `branch`
    reset_branch = branch or dataset.repo.get_hexsha()

    # Write the compute specification to a file in the dataset
    digest = write_spec(
        dataset, template_name, input_pattern, output_pattern, stdout, parameters
    )

    return (
        f'{url_scheme}:///'
        f'?label={quote(label)}'
        f'&root_version={quote(dataset.repo.get_hexsha())}'
        f'&specification={quote(digest)}'
    ), reset_branch


def write_spec(
    dataset: Dataset,
    method: str,
    input_pattern: list[PatternPath],
    output_pattern: list[PatternPath],
    stdout: PatternPath | None,
    parameters: dict[str, str],
) -> str:
    # create the specification and hash it
    spec = build_json(method, input_pattern, output_pattern, stdout, parameters)
    hasher = hashlib.md5()  # noqa S324
    hasher.update(spec.encode())
    digest = hasher.hexdigest()

    # write the specification file
    spec_dir = dataset.pathobj / specification_dir
    spec_dir.mkdir(parents=True, exist_ok=True)
    spec_file = spec_dir / digest
    with chdir(dataset.pathobj):
        call_git_success(['annex', 'unlock', str(spec_file)], capture_output=True)
    spec_file.write_text(spec)
    dataset.save(
        message=f'[DATALAD] saving computation spec\n\nfile name: {digest}',
        recursive=True,
        result_renderer='disabled',
    )
    return digest


def build_json(
    method: str,
    inputs: list[PatternPath],
    outputs: list[PatternPath],
    stdout: PatternPath | None,
    parameters: dict[str, str],
) -> str:
    return json.dumps(
        {
            'method': method,
            'input': sorted(map(str, inputs)),
            'output': sorted(map(str, outputs)),
            'stdout': None if stdout is None else str(stdout),
            'parameter': parameters,
        },
        sort_keys=True,
    )


def add_url(
    dataset: Dataset,
    file_path: PatternPath,
    url_base: str,
    *,
    url_only: bool,
) -> str:
    lgr.debug(
        'add_url: %s %s %s %s', str(dataset), str(file_path), url_base, repr(url_only)
    )

    # Build the file-specific URL and store it in the annex
    url = url_base + f'&this={quote(str(file_path))}'
    dataset_path, path = get_file_dataset(dataset.pathobj / file_path)

    # If the file does not exist and speculative computation is requested, we
    # can just add the URL.
    if not (dataset.pathobj / path).exists() and url_only:
        can_add = True
    else:
        # Check if the file is annexed, otherwise we cannot add a URL
        can_add = call_git_success(
            ['annex', 'whereis', str(path)],
            cwd=dataset_path,
            capture_output=True,
        )

    # Add the URL
    if can_add:
        success = call_git_success(
            ['annex', 'addurl', url, '--file', str(path)]
            + (['--relaxed'] if url_only else []),
            cwd=dataset_path,
            capture_output=True,
        )
        if not success:
            msg = (
                f'\naddurl failed:\ndataset_path: {dataset_path}\n'
                f'url: {url!r}\nfile_path: {path!r}'
            )
            raise RuntimeError(msg)
    return url


def get_file_dataset(file: Path) -> tuple[Path, Path]:
    """Get dataset of file and relative path of file from the dataset

    Determine the path of the dataset that contains the file and the relative
    path of the file in this dataset."""
    top_level = Path(
        call_git_oneline(['rev-parse', '--show-toplevel'], cwd=file.parent)
    )
    return Path(top_level), file.absolute().relative_to(top_level)


def provide(
    dataset: Dataset,
    branch: str | None,
    input_patterns: list[PatternPath],
) -> Path:
    lgr.debug('provide: %s %s %s', dataset, branch, input_patterns)
    result = list(
        provision_cmd.provide(
            dataset=dataset,
            input_patterns=input_patterns,
            source_branch=branch,
        )
    )
    return Path(result[0]['path'])


@contextlib.contextmanager
def provide_context(
    dataset: Dataset,
    branch: str | None,
    input_patterns: list[PatternPath],
) -> Generator:
    worktree = provide(dataset, branch=branch, input_patterns=input_patterns)
    try:
        yield worktree
    finally:
        if os.environ.get('DATALAD_REMAKE_KEEP_TEMP') is not None:
            lgr.debug('remake debug: keeping: %s %s', dataset, str(worktree))
        else:
            lgr.debug('un_provide: %s %s', dataset, str(worktree))
            dataset.provision(delete=worktree, result_renderer='disabled')


def execute(
    worktree: Path,
    template_name: str,
    parameter: dict[str, str],
    output_pattern: list[PatternPath],
    stdout: PatternPath | None,
    trusted_key_ids: list[str] | None,
) -> None:
    lgr.debug(
        'execute: %s %s %s %s %s',
        str(worktree),
        template_name,
        repr(parameter),
        repr(output_pattern),
        repr(stdout),
    )

    worktree_ds = Dataset(worktree)

    # Determine which outputs already exist
    existing_outputs = resolve_patterns(root_dir=worktree, patterns=output_pattern)

    # Get the subdatasets, directories, and files of the existing output space
    create_output_space(worktree_ds, existing_outputs)

    # Unlock existing output files in the output space (worktree-directory)
    unlock_files(worktree_ds, existing_outputs)

    # Run the computation in the worktree-directory
    template_path = Path(template_dir) / template_name
    if trusted_key_ids is not None:
        verify_file(worktree_ds.pathobj, template_path, trusted_key_ids)

    worktree_ds.get(template_path, result_renderer='disabled')
    compute(
        worktree,
        worktree / template_path,
        parameter,
        None if stdout is None else worktree / stdout,
    )


def collect(
    worktree: Path,
    dataset: Dataset,
    output_pattern: Iterable[PatternPath],
    stdout: PatternPath | None,
) -> set[PatternPath]:
    output = resolve_patterns(root_dir=worktree, patterns=output_pattern)
    if stdout is not None:
        output.add(stdout)

    # Ensure that all subdatasets that are touched by paths in `output` are
    # installed.
    install_containing_subdatasets(dataset, output)

    # Unlock output files in the dataset-directory and copy the result
    unlock_files(dataset, output)
    for o in output:
        lgr.debug('collect: collecting %s', o)
        destination = dataset.pathobj / o
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(worktree / o, destination)

    # Save the dataset
    dataset.save(recursive=True, result_renderer='disabled')
    return output


def install_containing_subdatasets(
    dataset: Dataset,
    files: Iterable[PatternPath],
) -> None:
    """Install all subdatasets that contain a file from `files`."""

    # Set the set of subdatasets to the set of subdatasets that are installed.
    # Compare each prefix of a file path with the path of a subdataset from the
    # root of `dataset`. If it matches, the subdataset is installed and the set
    # of subdatasets is updated accordingly.

    # Get the relative paths of all known subdatasets
    subdataset_infos = {
        # Determine the relative path of the parent dataset with system `Path`
        # instances, and convert it into `PatternPath` objects.
        PatternPath(Path(result['path']).relative_to(Path(result['parentds']))): result[
            'state'
        ]
        == 'present'
        for result in dataset.subdatasets(recursive=True)
    }

    # Get the prefixes of all required paths sorted by length
    required_paths = sorted(
        {
            prefix
            for file in files
            for prefix in file.parents
            if prefix != PatternPath('.')
        },
        key=lambda p: p.parts.__len__(),
    )

    for path in required_paths:
        if path in subdataset_infos and not subdataset_infos[path]:
            dataset.install(path=str(path), result_renderer='disabled')
            # Update subdataset_info to get newly installed subdatasets.
            subdataset_infos = {
                PatternPath(
                    Path(result['path']).relative_to(Path(result['parentds']))
                ): result['state'] == 'present'
                for result in dataset.subdatasets(recursive=True)
            }


def initialize_remotes(
    dataset: Dataset,
    files: Iterable[PatternPath],
) -> None:
    """Add a remake remote to all datasets that are touched by the files"""

    # Get the subdatasets that contain generated files
    touched_dataset_dirs = {
        get_file_dataset(dataset.pathobj / file)[0] for file in files
    }

    for dataset_dir in touched_dataset_dirs:
        add_remake_remote(str(dataset_dir))


def unlock_files(
    dataset: Dataset,
    files: Iterable[PatternPath],
) -> None:
    """Use datalad to resolve subdatasets and unlock files in the dataset."""
    # TODO: for some reason `dataset unlock` does not operate in the
    #  context of `dataset.pathobj`, so we need to change the working
    #  directory manually here.
    with chdir(dataset.pathobj):
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


def create_output_space(
    dataset: Dataset,
    files: Iterable[PatternPath],
) -> None:
    """Get all files that are part of the output space."""
    for f in files:
        with contextlib.suppress(IncompleteResultsError):
            # Convert the `PatternPath` instance to a system path and pass its
            # string representation to `Dataset.get()`.
            dataset.get(str(Path(f)), result_renderer='disabled')
