"""DataLad demo command"""

__docformat__ = 'restructuredtext'

import logging
from os.path import curdir
from os.path import abspath
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
from datalad_next.constraints import EnsureDataset

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
    ))

    # parameters of the command, must be exhaustive
    _params_ = dict(
        dataset=Parameter(
            args=('-d', '--dataset'),
            doc="""Dataset to be used as a configuration source. Beyond
            reading configuration items, this command does not interact with
            the dataset."""),
        url_only=Parameter(
            args=('-u', '--url-only'),
            action="store_true",
            doc="""Don't perform the computation, register an URL-key
            instead"""),
        template=Parameter(
            args=('template',),
            doc="""Name of the computing template (template should be present
            in $DATASET/.datalad/compute/methods)"""),
        output=Parameter(
            args=('output',),
            doc="""name of the output file"""),
        parameters=Parameter(
            args=('parameters',),
            doc="""parameters in the form <name>=<value>""",
            nargs='*'),
    )

    @staticmethod
    @datasetmethod(name='compute')
    @eval_results
    # signature must match parameter list above
    # additional generic arguments are added by decorators
    def __call__(dataset,
                 url_only=False,
                 template=None,
                 output=None,
                 parameters=None
                 ):

        dataset = dataset.ds

        if not url_only:
            parameter_dict = {
                parameter.split('=')[0]: parameter.split('=')[1]
                for parameter in parameters
            }
            template_path = dataset.pathobj / template_dir / template
            compute(template_path, parameter_dict, output)
            dataset.save()

        relaxed = ['--relaxed'] if url_only else []
        url = get_url(template, parameters)
        dataset.repo.call_annex(['addurl', url, '--file', output] + relaxed)

        yield get_status_dict(
                action='compute',
                path=abspath(curdir),
                status='ok',
                message=f'added url: {url!r} to {output!r}',
            )


def get_url(template_name: str, parameters: list[str]) -> str:
    url_params = '&'.join(
        f'{name}={quote(value)}'
        for name, value in map(lambda s: s.split('=', 1), parameters)
    )
    return f'{url_scheme}:///?dep=&method={template_name}&' + url_params
