from __future__ import annotations

from contextlib import contextmanager


@contextmanager
def patched_env(
    add: dict | None = None,
    remove: list[str] | None = None,
):
    """
    Patch the environment for the duration of the context manager.

    Parameters
    ----------
    add : dict
        The environment variables to add.
    remove : list[str]
        The environment variables to remove.

    Yields
    -------
    None
    """
    import os

    # Store the original environment
    original_env = dict(os.environ)

    # Update the environment
    os.environ.update(add or {})
    for var in remove or []:
        if var in os.environ:
            del os.environ[var]

    try:
        yield
    finally:
        # Restore the original environment
        os.environ.clear()
        os.environ.update(original_env)
