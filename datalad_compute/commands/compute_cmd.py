"""DataLad demo command"""

from __future__ import annotations

__docformat__ = 'restructuredtext'

import json
import logging
from os.path import abspath
from pathlib import Path
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
from datalad_next.runners import call_git_oneline, call_git_success

from datalad_compute import (
    template_dir,
    url_scheme,
)
from datalad_compute.utils.compute import compute


lgr = logging.getLogger('datalad.compute')


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
    def __call__(dataset,
                 url_only=False,
                 template=None,
                 branch=None,
                 input=None,
                 output=None,
                 parameter=None,
                 ):

        root_dataset : Dataset = dataset.ds

        if not url_only:
            template_path = root_dataset.pathobj / template_dir / template
            parameter_dict = {
                p.split('=', 1)[0]: p.split('=', 1)[1]
                for p in parameter
            }
            compute(
                root_dataset,
                branch,
                template_path,
                [Path(i) for i in input],
                [Path(o) for o in output],
                parameter_dict
            )
            root_dataset.save(recursive=True)

        url = get_url(dataset, branch, template, parameter, input, output)
        relaxed = ['--relaxed'] if url_only else []
        for out in output:
            file_dataset_path = get_file_dataset(Path(out))
            call_git_success(
                [
                    '-C', str(file_dataset_path), 'annex',
                    'addurl', url, '--file', out
                ]
                + relaxed
            )

            yield get_status_dict(
                    action='compute',
                    path=abspath(out),
                    status='ok',
                    message=f'added url: {url!r} to {out!r}',
                )


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


def get_file_dataset(file: Path) -> Path:
    """ Get dataset of file and path from that dataset to root dataset

    Determine the dataset that contains the file and the relative path from
    this dataset to root dataset."""
    top_level = call_git_oneline(
        ['-C', str(file.parent), 'rev-parse', '--show-toplevel']
    )
    return Path(top_level)
