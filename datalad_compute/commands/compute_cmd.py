"""DataLad demo command"""

__docformat__ = 'restructuredtext'

import logging
import time
from base64 import urlsafe_b64encode
from os.path import curdir
from os.path import abspath

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
        url_id=Parameter(
            args=('-i', '--id'),
            doc="""Use <id> as URL-id for the computation URLs"""),
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
                 url_id=None,
                 template=None,
                 output=None,
                 parameters=None
                 ):

        dataset = dataset.ds
        print(f'dataset={dataset}')
        print(f'url_only={url_only}')
        print(f'url_id={url_id}')
        print(f'template={template}')
        print(f'output={output}')
        print(f'parameters={parameters}')

        if not url_id:
            url_id = str(time.time())

        if not url_only:
            parameter_dict = {
                parameter.split('=')[0]: parameter.split('=')[1]
                for parameter in parameters
            }
            template_path = dataset.pathobj / '.datalad' / 'compute' / 'methods' / template
            compute(template_path, parameter_dict, output)
            dataset.save()

        relaxed = ['--relaxed'] if url_only else []
        urls = get_urls(url_id, template, parameters)
        for url in urls:
            dataset.repo.call_annex(['addurl', url, '--file', output] + relaxed)

        yield get_status_dict(
                action='compute',
                path=abspath(curdir),
                status='ok',
                message=f'added urls: {urls!r} to {output!r}',
            )


def get_urls(url_id, template_name: str, parameters: list[str]):
    method_url = 'compute://' + url_id + '/method/' + urlsafe_b64encode(template_name.encode()).decode()
    parameter_url = 'compute://' + url_id + '/parameter/' + urlsafe_b64encode(';'.join(parameters).encode()).decode()
    dependencies_url = 'compute://' + url_id + '/dependencies/' + urlsafe_b64encode('none'.encode()).decode()

    return [method_url, parameter_url, dependencies_url]
