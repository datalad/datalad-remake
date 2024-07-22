"""DataLad demo command"""

__docformat__ = 'restructuredtext'

import logging
from os.path import curdir
from os.path import abspath

from datalad.distribution.dataset import datasetmethod
from datalad.interface.base import Interface
from datalad.interface.base import build_doc
from datalad.interface.base import eval_results
from datalad.interface.results import get_status_dict


lgr = logging.getLogger('datalad.compute')


# decoration auto-generates standard help
@build_doc
# all commands must be derived from Interface
class Compute(Interface):
    # first docstring line is used a short description in the cmdline help
    # the rest is put in the verbose help and manpage
    """Specify a computation and optionally execute it
    """

    # parameters of the command, must be exhaustive
    _params_ = dict()

    @staticmethod
    @datasetmethod(name='compute')
    @eval_results
    # signature must match parameter list above
    # additional generic arguments are added by decorators
    def __call__():
        yield get_status_dict(
            action='compute',
            path=abspath(curdir),
            status='ok',
            message='compute command NOT YET IMPLEMENTED',
        )
