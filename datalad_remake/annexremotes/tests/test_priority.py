import subprocess
from io import TextIOBase
from typing import cast

import pytest
from annexremote import Master
from datalad_next.tests import skip_if_on_windows

from datalad_remake import priority_config_key
from datalad_remake.commands.tests.create_datasets import create_ds_hierarchy

from ... import (
    specification_dir,
    template_dir,
)
from ...commands.make_cmd import build_json
from ..remake_remote import RemakeRemote
from .utils import (
    MockedInput,
    MockedOutput,
)

# The following templates create differing content if formatted with different
# values for `label`. This is intended here, it
# only works because we drive the special remote ourselves, and skip the
# content validation. So they are not a valid example for different compute
# instructions that lead to identical results, but just a way to test the
# priority code.
template = """
parameters = ['content']
use_shell = 'true'
command = ["echo from {label}: {{content}} > 'a.txt'"]
"""


@skip_if_on_windows
@pytest.mark.parametrize('priority', [['alpha', 'beta'], ['beta', 'alpha']])
def test_compute_remote_priority(tmp_path, datalad_cfg, monkeypatch, priority):
    datalad_cfg.add(
        var=priority_config_key,
        value=','.join(priority),
        scope='global',
    )

    dataset = create_ds_hierarchy(
        tmp_path=tmp_path,
        name='ds1',
        subdataset_levels=0,
        signing_key=None,
    )[0][2]

    monkeypatch.chdir(dataset.path)

    template_path = dataset.pathobj / template_dir
    template_path.mkdir(parents=True)
    for label in priority:
        (template_path / label).write_text(template.format(label=label))
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
    for label in ('alpha', 'beta'):
        specification_path.mkdir(parents=True, exist_ok=True)
        (specification_path / f'00000-{label}').write_text(
            build_json(
                label,
                [],
                ['a.txt'],
                {'content': f'{label}_parameter'},
            )
        )
    dataset.save()

    # The compute instruction URLs that are associated with `a.txt`. The order
    # in which the URLs are reported to the special remote is fixed: first
    # `alpha`, second `beta`.
    urls = [
        'datalad-make:///?'
        + '&'.join(
            [
                f'label={label}',
                f'root_version={dataset.repo.get_hexsha()}',
                f'specification=00000-{label}',
                'this=a.txt',
            ]
        )
        for label in ['alpha', 'beta']
    ]

    input_ = MockedInput()

    # We send all messages into the queue upfront because we do the test in a
    # single thread and do not get back control once `master.listen` is called
    # below.
    input_.send('PREPARE\n')
    input_.send(f'TRANSFER RETRIEVE {key.decode()} {tmp_path / "remade.txt"!s}\n')
    # The next line is the answer to `GETCONFIG allow_untrusted_execution`
    input_.send('VALUE true\n')
    # The next two lines are the answer to
    # `GETURLS MD5E-s2--60b725f10c9c85c70d97880dfe8191b3.txt datalad-remake:`
    input_.send(f'VALUE {urls[0]}\n')
    input_.send(f'VALUE {urls[1]}\n')
    input_.send('VALUE\n')
    input_.send('VALUE .git\n')
    input_.send('VALUE .git\n')
    input_.send('')

    output = MockedOutput()

    master = Master(output=cast(TextIOBase, output))
    remote = RemakeRemote(master)
    master.LinkRemote(remote)
    master.Listen(input=cast(TextIOBase, input_))

    # At this point the datalad-remake remote should have executed the
    # prioritized template and written the result.
    assert (
        tmp_path / 'remade.txt'
    ).read_text().strip() == f'from {priority[0]}: {priority[0]}_parameter'
