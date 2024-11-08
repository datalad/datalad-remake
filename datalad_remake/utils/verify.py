import contextlib
import logging
import os
import subprocess
import tempfile
from pathlib import Path

from datalad_next.runners import (
    call_git_oneline,
    call_git_success,
)

lgr = logging.getLogger('datalad.remake.utils.verify')


def verify_file(root_directory: Path, file: Path, trusted_key_ids: list[str]):
    if not trusted_key_ids:
        msg = 'No trusted keys provided'
        raise ValueError(msg)

    # Get the latest commit of `file`
    commit = call_git_oneline(
        ['-C', str(root_directory), 'log', '-1', '--follow', '--pretty=%H', str(file)]
    )

    with tempfile.TemporaryDirectory() as temp_gpg_dir:
        # Create a temporary PGP keyring that contains the trusted keys
        _copy_keys_to(trusted_key_ids, temp_gpg_dir)

        # Let git do the verification of the commit with the trusted keys
        with _gpg_dir(temp_gpg_dir):
            result = call_git_success(
                ['-C', str(root_directory), 'verify-commit', commit]
            )

        if not result:
            msg = f'Signature validation of {file} failed'
            raise ValueError(msg)


def _copy_keys_to(trusted_key_ids: list[str], keyring_dir: str) -> None:
    for key_id in trusted_key_ids:
        # Export the requested key into `result.stdout`
        result = subprocess.run(
            ['gpg', '-a', '--export', key_id],  # noqa: S607
            stdout=subprocess.PIPE,
            check=False,
        )

        if result.returncode != 0:
            lgr.warning(f'Could not locate trusted key with id: {key_id}')
            continue

        # Import key from `result.stdout` into a keyring in `keyring_dir`
        subprocess.run(
            ['gpg', '--homedir', str(keyring_dir), '--import'],  # noqa: S607
            input=result.stdout,
            check=True,
        )


@contextlib.contextmanager
def _gpg_dir(directory: str):
    _original_value = os.environ.get('GNUPGHOME')
    try:
        os.environ['GNUPGHOME'] = directory
        yield
    finally:
        if _original_value is None:
            del os.environ['GNUPGHOME']
        else:
            os.environ['GNUPGHOME'] = _original_value
