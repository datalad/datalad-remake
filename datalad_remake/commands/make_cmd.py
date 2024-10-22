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
    specification_dir,
    template_dir,
    url_scheme,
)
from datalad_remake.utils.compute import compute
from datalad_remake.utils.glob import resolve_patterns

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
        'url_only': Parameter(
            args=('-u', '--url-only'),
            action='store_true',
            doc="Don't perform the computation, register an URL-key "
            'instead. A `git annex get <file>` will trigger the computation',
        ),
        'template': Parameter(
            args=('template',),
            doc='Name of the computing template (template should be present '
            'in $DATASET/.datalad/remake/methods)',
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
            doc='An input file pattern (repeat for multiple inputs, '
            'file pattern support python globbing, globbing is expanded '
            'in the source dataset)',
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
        'output': Parameter(
            args=(
                '-o',
                '--output',
            ),
            action='append',
            doc='An output file pattern (repeat for multiple outputs)'
            'file pattern support python globbing, globbing is expanded '
            'in the worktree)',
        ),
        'output_list': Parameter(
            args=(
                '-O',
                '--output-list',
            ),
            doc='Name of a file that contains a list of output patterns. Format '
            'is one file per line, relative path from `dataset`. Empty '
            'lines, i.e. lines that contain only newlines, arg ignored. '
            'This is useful if a large number of output files should be '
            'provided.',
        ),
        'parameter': Parameter(
            args=(
                '-p',
                '--parameter',
            ),
            action='append',
            doc='Input parameter in the form <name>=<value> (repeat for '
            'multiple parameters)',
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
            'before used. This is useful if a large number of parameters '
            'should be provided.',
        ),
    }

    @staticmethod
    @datasetmethod(name='make')
    @eval_results
    def __call__(
        dataset: DatasetParameter | None = None,
        *,
        template: str = '',
        url_only: bool = False,
        branch: str | None = None,
        input: list[str] | None = None,  # noqa: A002
        input_list: Path | None = None,
        output: list[str] | None = None,
        output_list: Path | None = None,
        parameter: list[str] | None = None,
        parameter_list: Path | None = None,
    ) -> Generator:
        ds: Dataset = dataset.ds if dataset else Dataset('.')

        input_pattern = (input or []) + read_list(input_list)
        output_pattern = (output or []) + read_list(output_list)
        parameter = (parameter or []) + read_list(parameter_list)

        parameter_dict = {p.split('=', 1)[0]: p.split('=', 1)[1] for p in parameter}

        # We have to get the URL first, because saving the specification to
        # the dataset will change the version.
        url_base, reset_commit = get_url(
            ds, branch, template, parameter_dict, input_pattern, output_pattern
        )

        if not url_only:
            with provide_context(
                ds,
                branch,
                input_pattern,
            ) as worktree:
                execute(worktree, template, parameter_dict, output_pattern)
                resolved_output = collect(worktree, ds, output_pattern)
        else:
            resolved_output = set(output_pattern)

        for out in resolved_output:
            url = add_url(ds, out, url_base, url_only=url_only)
            yield get_status_dict(
                action='make',
                path=str(ds.pathobj / out),
                status='ok',
                message=f'added url: {url!r} to {out!r} in {ds.pathobj}',
            )


def read_list(list_file: str | Path | None) -> list[str]:
    if list_file is None:
        return []
    return list(
        filter(
            lambda s: s != '' and not s.startswith('#'),
            [
                line.strip()
                for line in Path(list_file).read_text().splitlines(keepends=False)
            ],
        )
    )


def get_url(
    dataset: Dataset,
    branch: str | None,
    template_name: str,
    parameters: dict[str, str],
    input_pattern: list[str],
    output_pattern: list[str],
) -> tuple[str, str]:
    # If something goes wrong after the make specification was saved,
    # the dataset state should be reset to `branch`
    reset_branch = branch or dataset.repo.get_hexsha()

    # Write the specification to a file in the dataset
    digest = write_spec(
        dataset, template_name, input_pattern, output_pattern, parameters
    )

    return (
        f'{url_scheme}:///'
        f'?root_version={quote(dataset.repo.get_hexsha())}'
        f'&specification={quote(digest)}'
    ), reset_branch


def write_spec(
    dataset: Dataset,
    method: str,
    input_pattern: list[str],
    output_pattern: list[str],
    parameters: dict[str, str],
) -> str:
    # create the specification and hash it
    spec = build_json(method, input_pattern, output_pattern, parameters)
    hasher = hashlib.sha256()
    hasher.update(spec.encode())
    digest = hasher.hexdigest()

    # write the specification file
    spec_dir = dataset.pathobj / specification_dir
    spec_dir.mkdir(exist_ok=True)
    spec_file = spec_dir / digest
    with contextlib.chdir(dataset.pathobj):
        call_git_success(['annex', 'unlock', str(spec_file)], capture_output=True)
    spec_file.write_text(spec)
    dataset.save(
        message=f'[DATALAD] saving computation spec\n\nfile name: {digest}',
        recursive=True,
        result_renderer='disabled',
    )
    return digest


def build_json(
    method: str, inputs: list[str], outputs: list[str], parameters: dict[str, str]
) -> str:
    return json.dumps(
        {'method': method, 'input': inputs, 'output': outputs, 'parameter': parameters}
    )


def add_url(dataset: Dataset, file_path: str, url_base: str, *, url_only: bool) -> str:
    lgr.debug('add_url: %s %s %s %s', str(dataset), file_path, url_base, repr(url_only))

    # Build the file-specific URL and store it in the annex
    url = url_base + f'&this={quote(file_path)}'
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
    return (Path(top_level), file.absolute().relative_to(top_level))


def provide(
    dataset: Dataset,
    branch: str | None,
    input_patterns: list[str],
) -> Path:
    lgr.debug('provide: %s %s %s', dataset, branch, input_patterns)
    result = dataset.provision(
        input=input_patterns, branch=branch, result_renderer='disabled'
    )
    return Path(result[0]['path'])


@contextlib.contextmanager
def provide_context(
    dataset: Dataset,
    branch: str | None,
    input_patterns: list[str],
) -> Generator:
    worktree = provide(dataset, branch=branch, input_patterns=input_patterns)
    try:
        yield worktree
    finally:
        lgr.debug('un_provide: %s %s', dataset, str(worktree))
        dataset.provision(delete=worktree, result_renderer='disabled')


def execute(
    worktree: Path,
    template_name: str,
    parameter: dict[str, str],
    output_pattern: list[str],
) -> None:
    lgr.debug(
        'execute: %s %s %s %s',
        str(worktree),
        template_name,
        repr(parameter),
        repr(output_pattern),
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
    worktree_ds.get(template_path)
    compute(worktree, worktree / template_path, parameter)


def collect(
    worktree: Path,
    dataset: Dataset,
    output_pattern: Iterable[str],
) -> set[str]:
    output = resolve_patterns(root_dir=worktree, patterns=output_pattern)

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


def unlock_files(dataset: Dataset, files: Iterable[str]) -> None:
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


def create_output_space(dataset: Dataset, files: Iterable[str]) -> None:
    """Get all files that are part of the output space."""
    for f in files:
        with contextlib.suppress(IncompleteResultsError):
            dataset.get(f, result_renderer='disabled')
