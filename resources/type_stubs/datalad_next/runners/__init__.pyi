from subprocess import DEVNULL as DEVNULL

from datalad.runner import GitRunner as GitRunner
from datalad.runner import KillOutput as KillOutput
from datalad.runner import NoCapture as NoCapture
from datalad.runner import Protocol as Protocol
from datalad.runner import Runner as Runner
from datalad.runner import StdErrCapture as StdErrCapture
from datalad.runner import StdOutCapture as StdOutCapture
from datalad.runner import StdOutErrCapture as StdOutErrCapture
from datalad.runner.nonasyncrunner import STDERR_FILENO as STDERR_FILENO
from datalad.runner.nonasyncrunner import STDOUT_FILENO as STDOUT_FILENO
from datalad.runner.nonasyncrunner import ThreadedRunner as ThreadedRunner
from datalad.runner.protocol import GeneratorMixIn as GeneratorMixIn
from datalad.runner.utils import LineSplitter as LineSplitter
from datalad_next.exceptions import CommandError as CommandError

from .git import call_git as call_git
from .git import call_git_lines as call_git_lines
from .git import call_git_oneline as call_git_oneline
from .git import call_git_success as call_git_success
from .git import iter_git_subproc as iter_git_subproc
from .iter_subproc import iter_subproc as iter_subproc
from .protocols import NoCaptureGeneratorProtocol as NoCaptureGeneratorProtocol
from .protocols import StdOutCaptureGeneratorProtocol as StdOutCaptureGeneratorProtocol
