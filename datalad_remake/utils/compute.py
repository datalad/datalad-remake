from __future__ import annotations

import contextlib
import logging
import subprocess
import tomllib

from pathlib import Path
from typing import Any


lgr = logging.getLogger('datalad.compute')


def substitute_string(format_str: str,
                      replacements: dict[str, str],
                      ) -> str:
    for variable_name, replacement in replacements.items():
        place_holder = '{' + variable_name + '}'
        if place_holder in format_str:
            format_str = format_str.replace(place_holder, replacement)
    return format_str


def substitute_arguments(spec: dict[str, Any],
                         replacements: dict[str, str],
                         format_list_id: str,
                         ) -> list[str]:

    return [
        substitute_string(str(format_str), replacements)
        for format_str in spec[format_list_id]
    ]


def get_substitutions(template: dict[str, Any],
                      arguments: dict[str, str],
                      ) -> dict[str, str]:

    # Check the user specified inputs
    inputs = template['inputs']
    if len(inputs) != len(arguments.keys()):
        raise ValueError('Template inputs and arguments have different lengths')
    if not all(input_name in arguments for input_name in inputs):
        raise ValueError(f'Template inputs and arguments have different names: inputs: {inputs}, arguments: {arguments}')

    if len(inputs) != len(set(inputs)):
        raise ValueError('Template inputs contain duplicates')

    return {
        input_name: arguments[input_name]
        for input_name in inputs
    }


def compute(root_directory: Path,
            template_path: Path,
            compute_arguments: dict[str, str],
            ) -> None:

    with template_path.open('rb') as f:
        template = tomllib.load(f)

    substitutions = get_substitutions(template, compute_arguments)
    substitutions['root_directory'] = str(root_directory)

    substituted_executable = substitute_string(template['executable'], substitutions)
    substituted_arguments = substitute_arguments(
        template,
        substitutions,
        'arguments'
    )

    with contextlib.chdir(root_directory):
        if template.get('use_shell', 'false') == 'true':
            lgr.debug(f'compute: RUNNING: with shell=True: {" ".join([substituted_executable] + substituted_arguments)}')
            subprocess.run(' '.join([substituted_executable] + substituted_arguments), shell=True, check=True)
        else:
            lgr.debug(f'compute: RUNNING: {[substituted_executable] + substituted_arguments}')
            subprocess.run([substituted_executable] + substituted_arguments, check=True)
