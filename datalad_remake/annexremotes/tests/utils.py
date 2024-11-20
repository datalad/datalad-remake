from __future__ import annotations

import re
import subprocess
from queue import Queue
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


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
        return self.input.get()

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
