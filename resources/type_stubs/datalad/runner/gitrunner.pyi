from .runner import GeneratorMixIn as GeneratorMixIn, WitlessRunner as WitlessRunner
from _typeshed import Incomplete
from datalad.dochelpers import borrowdoc as borrowdoc
from datalad.utils import generate_file_chunks as generate_file_chunks, make_tempfile as make_tempfile

lgr: Incomplete
GIT_SSH_COMMAND: str

class GitRunnerBase:
    @staticmethod
    def get_git_environ_adjusted(env: Incomplete | None = None): ...

class GitWitlessRunner(WitlessRunner, GitRunnerBase):
    def __init__(self, *args, **kwargs) -> None: ...
    def run_on_filelist_chunks(self, cmd, files, *, protocol: Incomplete | None = None, cwd: Incomplete | None = None, env: Incomplete | None = None, pathspec_from_file: bool | None = False, **kwargs): ...
    def run_on_filelist_chunks_items_(self, cmd, files, *, protocol: Incomplete | None = None, cwd: Incomplete | None = None, env: Incomplete | None = None, pathspec_from_file: bool | None = False, **kwargs): ...
