import re
import subprocess
from io import TextIOBase
from pathlib import Path
from queue import Queue
from typing import cast

import pytest
from annexremote import Master
from datalad_next.tests import skip_if_on_windows

from datalad_remake.commands.tests.create_datasets import create_ds_hierarchy

from ... import (
    specification_dir,
    template_dir,
)
from ...commands.make_cmd import build_json
from ..remake_remote import RemakeRemote

template = """
parameters = ['content']

use_shell = 'true'

command = ["echo content: {content} > 'a.txt'"]
"""


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


@skip_if_on_windows
@pytest.mark.parametrize('trusted', [True, False])
def test_compute_remote_main(tmp_path, datalad_cfg, monkeypatch, trusted):
    if trusted:
        gpg_homedir = tmp_path / 'tmp_gpg_dir'
        tmp_home = tmp_path / 'tmp_home'

        # make sure that the users keystore is not overwritten
        monkeypatch.setenv('HOME', str(tmp_home))

        # Generate a keypair
        signing_key = create_keypair(gpg_dir=gpg_homedir)

        # Activate the new keys
        monkeypatch.setenv('GNUPGHOME', str(gpg_homedir))

        datalad_cfg.add('datalad.trusted-keys', signing_key, where='global')

    else:
        signing_key = None

    dataset = create_ds_hierarchy(tmp_path, 'ds1', 0, signing_key)[0][2]
    monkeypatch.chdir(dataset.path)

    template_path = dataset.pathobj / template_dir
    template_path.mkdir(parents=True)
    (template_path / 'echo').write_text(template)
    dataset.save()

    key = next(
        filter(
            lambda line: line.startswith(b'key: '),
            subprocess.run(
                ['git', 'annex', 'info', 'a.txt'],  # noqa: S607
                stdout=subprocess.PIPE,
                check=True,
            ).stdout.splitlines(),
        )
    ).split(b': ')[1]

    specification_path = dataset.pathobj / specification_dir
    spec_name = '000001111122222'
    specification_path.mkdir(parents=True, exist_ok=True)
    (specification_path / spec_name).write_text(
        build_json('echo', [], ['a.txt'], {'content': 'some_string'})
    )
    dataset.save()

    input_ = MockedInput()

    # We send all messages into the queue upfront because we do the test in a
    # single thread and do not get back control once `master.listen` is called
    # below.
    input_.send('PREPARE\n')
    input_.send(f'TRANSFER RETRIEVE {key.decode()} {tmp_path / "remade.txt"!s}\n')
    # The next line is the answer to `GETCONFIG allow_untrusted_execution`
    input_.send(f'VALUE {"false" if trusted else "true"}\n')
    url = (
        'datalad-make:///?'
        f'root_version={dataset.repo.get_hexsha()}'
        '&specification=000001111122222'
        '&this=a.txt'
    )
    # The next line is the answer to
    # `GETURLS MD5E-s2--60b725f10c9c85c70d97880dfe8191b3.txt datalad-remake:`
    input_.send(f'VALUE {url}\n')
    input_.send('VALUE\n')
    input_.send('VALUE .git\n')
    input_.send('')

    output = MockedOutput()

    master = Master(output=cast(TextIOBase, output))
    remote = RemakeRemote(master)
    master.LinkRemote(remote)
    master.Listen(input=cast(TextIOBase, input_))

    # At this point the datalad-remake remote should have executed the
    # computation and written the result.
    assert (tmp_path / 'remade.txt').read_text().strip() == 'content: some_string'


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
    # Unset $HOME to prevent accidental changes to the user's keyring
    environment = {'HOME': '/dev/null'}

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
