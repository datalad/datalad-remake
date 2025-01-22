from __future__ import annotations

import logging
import subprocess
from io import BufferedWriter
from typing import (
    TYPE_CHECKING,
    Any,
)

from datalad_remake.utils.chdir import chdir
from datalad_remake.utils.toml import toml_load

if TYPE_CHECKING:
    from pathlib import Path

lgr = logging.getLogger('datalad.remake')


def substitute_string(
    format_str: str,
    replacements: dict[str, str],
) -> str:
    for variable_name, replacement in replacements.items():
        place_holder = '{' + variable_name + '}'
        if place_holder in format_str:
            format_str = format_str.replace(place_holder, replacement)
    return format_str


def substitute_arguments(
    spec: dict[str, Any],
    replacements: dict[str, str],
    format_list_id: str,
) -> list[str]:
    return [
        substitute_string(str(format_str), replacements)
        for format_str in spec[format_list_id]
    ]


def get_substitutions(
    template: dict[str, Any],
    arguments: dict[str, str],
) -> dict[str, str]:
    # Check the user specified parameters
    parameters = template['parameters']
    if len(parameters) != len(arguments.keys()):
        msg = 'Method template parameters and arguments have different lengths'
        raise ValueError(msg)
    if not all(param_name in arguments for param_name in parameters):
        msg = (
            f'Method template parameters and arguments have different names: '
            f'parameters: {parameters}, arguments: {arguments}'
        )
        raise ValueError(msg)

    if len(parameters) != len(set(parameters)):
        msg = f'Method template parameters contain duplicates: {parameters}'
        raise ValueError(msg)

    return {param_name: arguments[param_name] for param_name in parameters}


def compute(
    root_directory: Path,
    template_path: Path,
    compute_arguments: dict[str, str],
    stdout: BufferedWriter,
) -> None:
    template = toml_load(template_path)

    substitutions = get_substitutions(template, compute_arguments)
    substitutions['root_directory'] = str(root_directory)

    substituted_command = substitute_arguments(template, substitutions, 'command')

    with chdir(root_directory):
        lgr.debug(f'compute: RUNNING: {substituted_command}')
        subprocess.run(substituted_command, check=True, stdout=stdout)
