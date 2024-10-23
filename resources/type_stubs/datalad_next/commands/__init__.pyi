from .results import CommandResult as CommandResult, CommandResultStatus as CommandResultStatus
from datalad.interface.base import Interface, build_doc as build_doc, eval_results as eval_results
from datalad.interface.results import get_status_dict as get_status_dict
from datalad.interface.utils import generic_result_renderer as generic_result_renderer
from datalad.support.param import Parameter as Parameter
from datalad_next.constraints import EnsureCommandParameterization as EnsureCommandParameterization, ParameterConstraintContext as ParameterConstraintContext
from datalad_next.datasets import datasetmethod as datasetmethod

class ValidatedInterface(Interface):
    @classmethod
    def get_parameter_validator(cls) -> EnsureCommandParameterization | None: ...
