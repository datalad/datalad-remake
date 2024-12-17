from __future__ import annotations

import re
import subprocess
import sys
from io import TextIOBase
from queue import Queue
from typing import (
    TYPE_CHECKING,
    cast,
)

from annexremote import Master

from datalad_remake.annexremotes.remake_remote import RemakeRemote

if TYPE_CHECKING:
    from pathlib import Path


# For debugging purposes we want to see all messages that are exchanged between
# the remote and the host. Some code in datalad_next test configurations
# makes it quite difficult to use the standard logging calls. Therefore, we
# define this super simple custom logger here.
def log(*args):
    print(*args, file=sys.stderr, flush=True)  # noqa T201


class MockedOutput:
    def __init__(self):
        self.output = ''
        self.lines = []

    def write(self, *args, **_):
        self.output += ''.join(args)
        lines_with = self.output.splitlines(keepends=True)
        lines_without = self.output.splitlines(keepends=False)
        if not lines_with:
            pass
        elif lines_without[-1] == lines_with[-1]:
            self.lines = lines_without[:-1]
            self.output = lines_with[-1]
        else:
            self.lines = lines_without
            self.output = ''
            log(f'HOST <--- REMOTE: {self.lines[-1]!r}')

    def flush(self):
        pass

    def next_line(self):
        if self.lines:
            while True:
                line = self.lines.pop(0)
                if line.startswith('DEBUG '):
                    continue
                return line
        return None


class MockedInput:
    def __init__(self):
        self.input: Queue = Queue()

    def readline(self):
        line = self.input.get()
        log(f'HOST ---> REMOTE: {line!r}')
        return line

    def send(self, value):
        self.input.put(value)


def create_keypair(gpg_dir: Path, name: bytes = b'Test User'):
    gpg_dir.mkdir(parents=True, exist_ok=True)
    gpg_dir.chmod(0o700)
    private_keys_dir = gpg_dir / 'private-keys-v1.d'
    private_keys_dir.mkdir(exist_ok=True)
    private_keys_dir.chmod(0o700)
    template = b"""
        Key-Type: RSA
        Key-Length: 4096
        Subkey-Type: RSA
        Subkey-Length: 4096
        Name-Real: $NAME
        Name-Email: test@example.com
        Expire-Date: 0
        %no-protection
        #%transient-key
        %commit
    """
    script = template.replace(b'$NAME', name)

    # unset $HOME to prevent accidental changes to the user's keyring
    environment = {'HOME': '/dev/null'}

    # use gpg to generate a keypair
    subprocess.run(
        [  # noqa: S607
            'gpg',
            '--batch',
            '--homedir',
            str(gpg_dir),
            '--gen-key',
            '--keyid-format',
            'long',
        ],
        input=script,
        capture_output=True,
        check=True,
        env=environment,
    )

    result = subprocess.run(
        [  # noqa: S607
            'gpg',
            '--homedir',
            str(gpg_dir),
            '--list-secret-keys',
            '--keyid-format',
            'long',
        ],
        capture_output=True,
        check=True,
        env=environment,
    )
    return re.findall(
        r'(?m)sec.*rsa4096/([A-Z0-9]+).*\n.*\n.*' + name.decode(),
        result.stdout.decode(),
    )[0]


def run_remake_remote(dest_path, urls):
    input_ = MockedInput()

    annex_key = 'some-fake-annex-key'
    # We send all messages into the queue upfront because we do the test in a
    # single thread and do not get back control once `master.listen` is called
    # below.
    input_.send('PREPARE\n')
    input_.send(f'TRANSFER RETRIEVE {annex_key} {dest_path / "remade.txt"!s}\n')
    input_.send('VALUE .git\n')
    # The next two lines assemble the answer to
    # `GETURLS <annex-key> datalad-remake:`
    for url in urls:
        input_.send(f'VALUE {url}\n')
    input_.send('VALUE\n')
    input_.send('VALUE .git\n')
    input_.send('VALUE .git\n')
    input_.send('')

    master = Master(output=cast(TextIOBase, MockedOutput()))
    remote = RemakeRemote(master)
    master.LinkRemote(remote)
    master.Listen(input=cast(TextIOBase, input_))
