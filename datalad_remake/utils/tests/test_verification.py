from pathlib import Path

import pytest

from datalad_remake.annexremotes.tests.test_remake_remote import create_keypair
from datalad_remake.commands.tests.create_datasets import create_ds_hierarchy
from datalad_remake.utils.verify import verify_file


def test_whitelist(tmp_path, monkeypatch):
    gpg_dir = tmp_path / 'gpg'

    # make sure that the users keystore is not overwritten
    monkeypatch.setenv('HOME', '/dev/null')

    # Create two key-pairs, one is used for signing, the other is used to
    # validate the whitelist functionality.
    signing_key = create_keypair(gpg_dir=gpg_dir, name=b'Signing User')
    other_key = create_keypair(gpg_dir=gpg_dir, name=b'Other User')

    # Activate the new keys to allow `create_ds_hierarchy` to sign the commits
    monkeypatch.setenv('GNUPGHOME', str(gpg_dir))

    # Generate a simple dataset
    dataset = create_ds_hierarchy(tmp_path, 'ds1', 0, signing_key)[0][2]

    verify_file(dataset.pathobj, Path('a.txt'), [signing_key])
    verify_file(dataset.pathobj, Path('a.txt'), [signing_key, other_key])

    # Expect verification to fail if only `other_key` is white-listed because
    # the commits were signed with `signing_key`.
    with pytest.raises(ValueError, match='Signature validation of a.txt failed'):
        verify_file(dataset.pathobj, Path('a.txt'), [other_key])

    # Expect verification to fail if no key is white-listed.
    with pytest.raises(ValueError, match='Signature validation of a.txt failed'):
        verify_file(dataset.pathobj, Path('a.txt'), [])
