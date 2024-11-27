from .clone_utils import decode_source_spec as decode_source_spec, postclone_preannex_cfg_ria as postclone_preannex_cfg_ria, postclonecfg_ria as postclonecfg_ria
from _typeshed import Incomplete
from collections.abc import Generator
from datalad.cmd import CommandError as CommandError
from datalad.config import ConfigManager as ConfigManager
from datalad.distribution.dataset import Dataset as Dataset, EnsureDataset as EnsureDataset, datasetmethod as datasetmethod, require_dataset as require_dataset, resolve_path as resolve_path
from datalad.interface.base import Interface as Interface, build_doc as build_doc, eval_results as eval_results
from datalad.interface.common_opts import location_description as location_description, reckless_opt as reckless_opt
from datalad.interface.results import get_status_dict as get_status_dict
from datalad.support.annexrepo import AnnexRepo as AnnexRepo
from datalad.support.constraints import EnsureKeyChoice as EnsureKeyChoice, EnsureNone as EnsureNone, EnsureStr as EnsureStr
from datalad.support.exceptions import CapturedException as CapturedException
from datalad.support.network import PathRI as PathRI, RI as RI
from datalad.support.param import Parameter as Parameter
from datalad.utils import PurePath as PurePath, knows_annex as knows_annex, rmtree as rmtree

__docformat__: str
lgr: Incomplete

class Clone(Interface):
    result_filter: Incomplete
    return_type: str
    result_xfm: str
    @staticmethod
    def __call__(source, path: Incomplete | None = None, git_clone_opts: Incomplete | None = None, *, dataset: Incomplete | None = None, description: Incomplete | None = None, reckless: Incomplete | None = None, result_renderer: str | None = None) -> Dataset: ...

def clone_dataset(srcs, destds, reckless: Incomplete | None = None, description: Incomplete | None = None, result_props: Incomplete | None = None, cfg: Incomplete | None = None, checkout_gitsha: Incomplete | None = None, clone_opts: Incomplete | None = None) -> Generator[Incomplete, Incomplete, None]: ...
def postclone_checkout_commit(repo, target_commit, remote: str = 'origin') -> None: ...
def postclone_check_head(ds, remote: str = 'origin') -> None: ...
def configure_origins(cfgds, probeds, label: Incomplete | None = None, remote: str = 'origin') -> Generator[Incomplete, Incomplete, None]: ...
