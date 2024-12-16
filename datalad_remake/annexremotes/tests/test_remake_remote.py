import pytest
from datalad_core.config import ConfigItem
from datalad_core.tests.fixtures import cfgman  # noqa: F401
from datalad_next.tests import skip_if_on_windows

from datalad_remake import allow_untrusted_execution_key
from datalad_remake.commands.tests.create_datasets import create_ds_hierarchy

from ... import (
    specification_dir,
    template_dir,
    trusted_keys_config_key,
)
from ...commands.make_cmd import build_json
from .utils import (
    create_keypair,
    run_remake_remote,
)

template = """
parameters = ['content']
command = ["bash", "-c", "echo content: {content} > 'a.txt'"]
"""


@skip_if_on_windows
@pytest.mark.parametrize('trusted', [True, False])
def test_compute_remote_main(tmp_path, cfgman, monkeypatch, trusted):  # noqa: F811
    if trusted:
        gpg_homedir = tmp_path / 'tmp_gpg_dir'
        tmp_home = tmp_path / 'tmp_home'

        # make sure that the users keystore is not overwritten
        monkeypatch.setenv('HOME', str(tmp_home))

        # Generate a keypair
        signing_key = create_keypair(gpg_dir=gpg_homedir)

        # Activate the new keys
        monkeypatch.setenv('GNUPGHOME', str(gpg_homedir))

    else:
        signing_key = None

    dataset = create_ds_hierarchy(tmp_path, 'ds1', 0, signing_key)[0][2]
    monkeypatch.chdir(dataset.path)

    template_path = dataset.pathobj / template_dir
    template_path.mkdir(parents=True)
    (template_path / 'echo').write_text(template)
    dataset.save()

    specification_path = dataset.pathobj / specification_dir
    spec_name = '000001111122222'
    specification_path.mkdir(parents=True, exist_ok=True)
    (specification_path / spec_name).write_text(
        build_json('echo', [], ['a.txt'], {'content': 'some_string'})
    )
    dataset.save()

    url = 'datalad-make:///?' + '&'.join(
        [
            'label=test1',
            f'root_version={dataset.repo.get_hexsha()}',
            'specification=000001111122222',
            'this=a.txt',
        ]
    )

    with cfgman.overrides(
        {
            trusted_keys_config_key: ConfigItem(signing_key),
            allow_untrusted_execution_key + dataset.id: ConfigItem('true'),

        }
    ):
        run_remake_remote(tmp_path, [url])

    # At this point the datalad-remake remote should have executed the
    # computation and written the result.
    assert (tmp_path / 'remade.txt').read_text().strip() == 'content: some_string'
