from pathlib import Path

from datalad_next.runners import (
    call_git_oneline,
    call_git_success,
)


def verify_file(root_directory: Path, file: Path):
    # Get the latest commit of `file`
    commit = call_git_oneline([
        '-C', str(root_directory),
        'log', '-1', '--follow',
        '--pretty=%H',
        str(file)
    ])

    # Let git do the verification of the commit
    result = call_git_success([
        '-C', str(root_directory),
        'verify-commit',
        commit
    ])
    if not result:
        msg = f'Signature validation of {file} failed'
        raise ValueError(msg)
