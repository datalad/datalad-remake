from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import tomllib


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
                      output_path: str,
                      ) -> dict[str, str]:

    # Check the user specified inputs
    inputs = template['inputs']
    if len(inputs) != len(arguments.keys()):
        raise ValueError('Template inputs and arguments have different lengths')
    if not all(input_name in arguments for input_name in inputs):
        raise ValueError('Template inputs and arguments have different names')

    output_name = template['output']
    all_variables = inputs + [output_name]
    if len(all_variables) != len(set(all_variables)):
        raise ValueError('Template inputs/output contain duplicates')

    return {
        **{
            input_name: arguments[input_name]
            for input_name in inputs
        },
        output_name: output_path
    }


def compute(template_path: Path,
            compute_arguments: dict[str, str],
            output_path: str,
            ):
    with template_path.open('rb') as f:
        template = tomllib.load(f)

    substitutions = get_substitutions(template, compute_arguments, output_path)

    substituted_executable = substitute_string(template['executable'], substitutions)
    substituted_arguments = substitute_arguments(
        template,
        substitutions,
        'arguments'
    )

    if template.get('use_shell', 'false') == 'true':
        subprocess.run(' '.join([substituted_executable] + substituted_arguments), shell=True)
    else:
        subprocess.run([substituted_executable] + substituted_arguments)
