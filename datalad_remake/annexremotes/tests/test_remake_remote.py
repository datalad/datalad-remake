import pytest
from datalad_core.config import ConfigItem

from datalad_remake import allow_untrusted_execution_key
from datalad_remake.commands.tests.create_datasets import create_ds_hierarchy
from datalad_remake.utils.platform import on_windows

from ... import (
    PatternPath,
    specification_dir,
    template_dir,
    trusted_keys_config_key,
)
from ...commands.make_cmd import build_json
from .utils import (
    create_keypair,
    run_remake_remote,
)

if on_windows:
    template = """
    parameters = ['content']
    command = ["pwsh", "-c", "Write-Output 'content: {content}' > a.txt"]
    """
else:
    template = """
    parameters = ['content']
    command = ["bash", "-c", "echo content: {content} > 'a.txt'"]
    """


@pytest.mark.parametrize('trusted', [True, False])
def test_compute_remote_main(tmp_path, cfgman, monkeypatch, trusted):
    if trusted:
        if on_windows:
            pytest.skip('GPG key generation currently not supported on Windows')

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
        build_json('echo', [], [PatternPath('a.txt')], {'content': 'some_string'})
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
