from _typeshed import Incomplete
from collections.abc import Generator
from datalad.config import ConfigManager as ConfigManager
from datalad.core.distributed.clone import clone_dataset as clone_dataset
from datalad.distribution.dataset import Dataset as Dataset, EnsureDataset as EnsureDataset, datasetmethod as datasetmethod, require_dataset as require_dataset
from datalad.interface.base import Interface as Interface, build_doc as build_doc, eval_results as eval_results
from datalad.interface.common_opts import jobs_opt as jobs_opt, location_description as location_description, reckless_opt as reckless_opt, recursion_flag as recursion_flag
from datalad.interface.results import annexjson2result as annexjson2result, get_status_dict as get_status_dict, is_ok_dataset as is_ok_dataset, results_from_annex_noinfo as results_from_annex_noinfo, results_from_paths as results_from_paths, success_status_map as success_status_map
from datalad.local.subdatasets import Subdatasets as Subdatasets
from datalad.support.annexrepo import AnnexRepo as AnnexRepo
from datalad.support.collections import ReadOnlyDict as ReadOnlyDict
from datalad.support.constraints import EnsureChoice as EnsureChoice, EnsureInt as EnsureInt, EnsureNone as EnsureNone, EnsureStr as EnsureStr
from datalad.support.exceptions import CapturedException as CapturedException, CommandError as CommandError, InsufficientArgumentsError as InsufficientArgumentsError
from datalad.support.gitrepo import GitRepo as GitRepo
from datalad.support.network import RI as RI, URL as URL, urlquote as urlquote
from datalad.support.parallel import ProducerConsumerProgressLog as ProducerConsumerProgressLog
from datalad.support.param import Parameter as Parameter
from datalad.utils import Path as Path, get_dataset_root as get_dataset_root, shortened_repr as shortened_repr, unique as unique

__docformat__: str
lgr: Incomplete

class Get(Interface):
    @staticmethod
    def __call__(path: Incomplete | None = None, *, source: Incomplete | None = None, dataset: Incomplete | None = None, recursive: bool = False, recursion_limit: Incomplete | None = None, get_data: bool = True, description: Incomplete | None = None, reckless: Incomplete | None = None, jobs: str = 'auto') -> Generator[Incomplete, None, None]: ...
