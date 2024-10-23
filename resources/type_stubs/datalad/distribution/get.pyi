from collections.abc import Generator

from _typeshed import Incomplete
from datalad.config import ConfigManager as ConfigManager
from datalad.core.distributed.clone import clone_dataset as clone_dataset
from datalad.distribution.dataset import Dataset as Dataset
from datalad.distribution.dataset import EnsureDataset as EnsureDataset
from datalad.distribution.dataset import datasetmethod as datasetmethod
from datalad.distribution.dataset import require_dataset as require_dataset
from datalad.interface.base import Interface as Interface
from datalad.interface.base import build_doc as build_doc
from datalad.interface.base import eval_results as eval_results
from datalad.interface.common_opts import jobs_opt as jobs_opt
from datalad.interface.common_opts import location_description as location_description
from datalad.interface.common_opts import reckless_opt as reckless_opt
from datalad.interface.common_opts import recursion_flag as recursion_flag
from datalad.interface.results import annexjson2result as annexjson2result
from datalad.interface.results import get_status_dict as get_status_dict
from datalad.interface.results import is_ok_dataset as is_ok_dataset
from datalad.interface.results import (
    results_from_annex_noinfo as results_from_annex_noinfo,
)
from datalad.interface.results import results_from_paths as results_from_paths
from datalad.interface.results import success_status_map as success_status_map
from datalad.local.subdatasets import Subdatasets as Subdatasets
from datalad.support.annexrepo import AnnexRepo as AnnexRepo
from datalad.support.collections import ReadOnlyDict as ReadOnlyDict
from datalad.support.constraints import EnsureChoice as EnsureChoice
from datalad.support.constraints import EnsureInt as EnsureInt
from datalad.support.constraints import EnsureNone as EnsureNone
from datalad.support.constraints import EnsureStr as EnsureStr
from datalad.support.exceptions import CapturedException as CapturedException
from datalad.support.exceptions import CommandError as CommandError
from datalad.support.exceptions import (
    InsufficientArgumentsError as InsufficientArgumentsError,
)
from datalad.support.gitrepo import GitRepo as GitRepo
from datalad.support.network import RI as RI
from datalad.support.network import URL as URL
from datalad.support.network import urlquote as urlquote
from datalad.support.parallel import (
    ProducerConsumerProgressLog as ProducerConsumerProgressLog,
)
from datalad.support.param import Parameter as Parameter
from datalad.utils import Path as Path
from datalad.utils import get_dataset_root as get_dataset_root
from datalad.utils import shortened_repr as shortened_repr
from datalad.utils import unique as unique

__docformat__: str
lgr: Incomplete

class Get(Interface):
    @staticmethod
    def __call__(path: Incomplete | None = None, *, source: Incomplete | None = None, dataset: Incomplete | None = None, recursive: bool = False, recursion_limit: Incomplete | None = None, get_data: bool = True, description: Incomplete | None = None, reckless: Incomplete | None = None, jobs: str = 'auto') -> Generator[Incomplete, None, None]: ...
