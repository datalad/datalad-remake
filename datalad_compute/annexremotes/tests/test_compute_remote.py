import subprocess
import sys
from queue import Queue

from annexremote import Master

from ..compute_remote import ComputeRemote
from datalad_compute.commands.tests.create_datasets import create_ds_hierarchy


template = """
inputs = ['content']

use_shell = 'true'
executable = "echo"

arguments = [
    "content: {content} > 'a.txt';",
]
"""


class MockedOutput:
    def __init__(self):
        self.output = ''
        self.lines = []

    def write(self, *args, **kwargs):
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
        print(repr(self.output), repr(self.lines))

    def flush(self):
        pass

    def next_line(self):
        print('next_line:', self.lines)
        if self.lines:
            while True:
                line = self.lines.pop(0)
                if line.startswith('DEBUG '):
                    print('XXX DEBUG XXX ' + line[6:], file=sys.stderr)
                    continue
                return line
        return None


class MockedInput:
    def __init__(self):
        self.input = Queue()

    def readline(self):
        return self.input.get()

    def send(self, value):
        self.input.put(value)


def test_compute_remote_main(tmp_path, monkeypatch):

    dataset = create_ds_hierarchy(tmp_path, 'ds1', 0)[0][2]
    monkeypatch.chdir(dataset.path)

    template_path = dataset.pathobj / '.datalad' / 'compute' / 'methods'
    template_path.mkdir(parents=True)
    (template_path / 'echo').write_text(template)
    dataset.save()

    key = tuple(
        filter(
            lambda line: line.startswith(b'key: '),
            subprocess.run(
                ['git', 'annex', 'info', 'a.txt'],
                stdout=subprocess.PIPE,
                check=True).stdout.splitlines()))[0].split(b': ')[1]

    result = dataset.configuration('get', 'datalad.dataset.id')
    dataset_id = result[0]['value']
    dataset_version = dataset.repo.get_hexsha()

    input = MockedInput()

    # We send all messages into the queue upfront because we do the test in a
    # single thread and do not get back control once `master.listen` is called
    # below.
    input.send('PREPARE\n')
    input.send(f'TRANSFER RETRIEVE {key} {str(tmp_path / "computed.txt")}\n')
    url = (
        'datalad-make:///?'
        f'root_id={dataset_id}'
        f'&default_root_version={dataset_version}'
        '&method=echo'
        '&input=%5B%5D'
        '&output=%5B"a.txt"%5D'
        '&params=%5B"content=some_string"%5D'
        '&this=a.txt'
    )
    input.send(f'VALUE {url}\n')
    input.send('VALUE\n')
    input.send('VALUE .git\n')
    input.send('')

    output = MockedOutput()

    master = Master(output=output)
    remote = ComputeRemote(master)
    master.LinkRemote(remote)
    master.Listen(input=input)

    # At this point the compute remote should have executed the computation
    # and written the result.
    assert (tmp_path / 'computed.txt').read_text().strip() == 'content: some_string'
