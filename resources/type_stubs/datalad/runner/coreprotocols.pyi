from .protocol import WitlessProtocol as WitlessProtocol
from _typeshed import Incomplete

lgr: Incomplete

class NoCapture(WitlessProtocol): ...

class StdOutCapture(WitlessProtocol):
    proc_out: bool

class StdErrCapture(WitlessProtocol):
    proc_err: bool

class StdOutErrCapture(WitlessProtocol):
    proc_out: bool
    proc_err: bool

class KillOutput(WitlessProtocol):
    proc_out: bool
    proc_err: bool
    def pipe_data_received(self, fd: int, data: bytes) -> None: ...
