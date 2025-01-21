import enum
from .exception import CommandError as CommandError
from .protocol import GeneratorMixIn as GeneratorMixIn, WitlessProtocol as WitlessProtocol
from .runnerthreads import IOState as IOState, ReadThread as ReadThread, WaitThread as WaitThread, WriteThread as WriteThread
from _typeshed import Incomplete
from collections import deque
from collections.abc import Generator
from datalad.utils import on_windows as on_windows
from queue import Queue
from typing import IO

__docformat__: str
lgr: Incomplete
STDIN_FILENO: int
STDOUT_FILENO: int
STDERR_FILENO: int

class _ResultGenerator(Generator):
    class GeneratorState(enum.Enum):
        initialized = 0
        process_running = 1
        process_exited = 2
        connection_lost = 3
        waiting_for_process = 4
        exhausted = 5
    runner: Incomplete
    result_queue: Incomplete
    return_code: Incomplete
    state: Incomplete
    all_closed: bool
    send_lock: Incomplete
    def __init__(self, runner: ThreadedRunner, result_queue: deque) -> None: ...
    def send(self, message): ...
    def throw(self, exception_type, value: Incomplete | None = None, trace_back: Incomplete | None = None): ...

class ThreadedRunner:
    timeout_resolution: float
    cmd: Incomplete
    protocol_class: Incomplete
    stdin: Incomplete
    protocol_kwargs: Incomplete
    timeout: Incomplete
    exception_on_error: Incomplete
    popen_kwargs: Incomplete
    catch_stdout: Incomplete
    catch_stderr: Incomplete
    write_stdin: bool
    stdin_queue: Incomplete
    process_stdin_fileno: Incomplete
    process_stdout_fileno: Incomplete
    process_stderr_fileno: Incomplete
    stderr_enqueueing_thread: Incomplete
    stdout_enqueueing_thread: Incomplete
    stdin_enqueueing_thread: Incomplete
    process_waiting_thread: Incomplete
    process_running: bool
    output_queue: Incomplete
    process_removed: bool
    generator: Incomplete
    process: Incomplete
    return_code: Incomplete
    last_touched: Incomplete
    active_file_numbers: Incomplete
    stall_check_interval: int
    initialization_lock: Incomplete
    generator_condition: Incomplete
    owning_thread: Incomplete
    protocol: Incomplete
    fileno_mapping: Incomplete
    fileno_to_file: Incomplete
    file_to_fileno: Incomplete
    result: Incomplete
    def __init__(self, cmd: str | list, protocol_class: type[WitlessProtocol], stdin: int | IO | bytes | Queue[bytes | None] | None, protocol_kwargs: dict | None = None, timeout: float | None = None, exception_on_error: bool = True, **popen_kwargs) -> None: ...
    def run(self) -> dict | _ResultGenerator: ...
    def process_loop(self) -> dict: ...
    def process_timeouts(self) -> bool: ...
    def should_continue(self) -> bool: ...
    def is_stalled(self) -> bool: ...
    def check_for_stall(self) -> bool: ...
    def process_queue(self) -> None: ...
    def remove_process(self) -> None: ...
    def remove_file_number(self, file_number: int): ...
    def close_stdin(self) -> None: ...
    def ensure_stdin_stdout_stderr_closed(self) -> None: ...
    def ensure_stdout_stderr_closed(self) -> None: ...
    def wait_for_threads(self) -> None: ...

def run_command(cmd: str | list, protocol: type[WitlessProtocol], stdin: int | IO | bytes | Queue[bytes | None] | None, protocol_kwargs: dict | None = None, timeout: float | None = None, exception_on_error: bool = True, **popen_kwargs) -> dict | _ResultGenerator: ...
