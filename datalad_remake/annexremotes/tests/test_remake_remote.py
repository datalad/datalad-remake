import subprocess
from queue import Queue

from annexremote import Master
from datalad_next.tests import skip_if_on_windows

from datalad_remake.commands.tests.create_datasets import create_ds_hierarchy

from ... import specification_dir
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
        lineswith = self.output.splitlines(keepends=True)
        lineswithout = self.output.splitlines(keepends=False)
        if not lineswith:
            pass
        elif lineswithout[-1] == lineswith[-1]:
            self.lines = lineswithout[:-1]
            self.output = lineswith[-1]
        else:
            self.lines = lineswithout
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
def test_compute_remote_main(tmp_path, monkeypatch):
    dataset = create_ds_hierarchy(tmp_path, 'ds1', 0)[0][2]
    monkeypatch.chdir(dataset.path)

    template_path = dataset.pathobj / '.datalad' / 'make' / 'methods'
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

    (dataset.pathobj / specification_dir).mkdir(parents=True, exist_ok=True)
    (dataset.pathobj / specification_dir / '000001111122222').write_text(
        build_json('echo', [], ['a.txt'], {'content': 'some_string'})
    )

    input_ = MockedInput()

    # We send all messages into the queue upfront because we do the test in a
    # single thread and do not get back control once `master.listen` is called
    # below.
    input_.send('PREPARE\n')
    input_.send(f'TRANSFER RETRIEVE {key.decode()} {tmp_path / "remade.txt"!s}\n')
    url = (
        'datalad-make:///?'
        f'root_version={dataset.repo.get_hexsha()}'
        '&specification=000001111122222'
        '&this=a.txt'
    )
    input_.send(f'VALUE {url}\n')
    input_.send('VALUE\n')
    input_.send('VALUE .git\n')
    input_.send('')

    output = MockedOutput()

    master = Master(output=output)
    remote = RemakeRemote(master)
    master.LinkRemote(remote)
    master.Listen(input=input_)

    # At this point the datalad-remake remote should have executed the
    # computation and written the result.
    assert (tmp_path / 'remade.txt').read_text().strip() == 'content: some_string'
