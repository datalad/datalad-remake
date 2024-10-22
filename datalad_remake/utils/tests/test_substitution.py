from ..compute import (
    substitute_arguments,
    substitute_string,
)


def test_multiple_substitutions():
    assert (
        substitute_string(
            'This is a {test} with {multiple} substitutions',
            {'test': 'string', 'multiple': 'multiple'},
        )
        == 'This is a string with multiple substitutions'
    )


def test_argument_substitution():
    arguments = [
        '{root_directory}/{input_dir}',
        '{root_directory}/{output_dir}',
    ]
    s = substitute_arguments(
        {'arguments': arguments},
        {
            'root_directory': '/path/to/root',
            'input_dir': 'input',
            'output_dir': 'output',
        },
        'arguments',
    )
    assert s == [
        '/path/to/root/input',
        '/path/to/root/output',
    ]
