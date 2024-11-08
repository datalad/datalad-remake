from ..git import DataladBranchConfig as DataladBranchConfig, GlobalGitConfig as GlobalGitConfig, LocalGitConfig as LocalGitConfig
from ..item import ConfigItem as ConfigItem
from datalad_core.consts import DATALAD_BRANCH_CONFIG_RELPATH as DATALAD_BRANCH_CONFIG_RELPATH
from datalad_core.runners import call_git_oneline as call_git_oneline

def test_global_git_config() -> None: ...
def test_global_git_config_pure(cfgman) -> None: ...
def test_local_git_config_norepo(tmp_path) -> None: ...
def test_local_git_config(gitrepo) -> None: ...
def test_datalad_branch_config(gitrepo) -> None: ...
def test_datalad_branch_shorthand(gitrepo) -> None: ...
def test_gitcfg_rec_to_keyvalue() -> None: ...