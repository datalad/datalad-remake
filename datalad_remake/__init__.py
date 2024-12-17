"""DataLad remake extension"""

from __future__ import annotations

from datalad_remake._version import __version__

__all__ = [
    '__version__',
    'allow_untrusted_execution_key',
    'auto_remote_name',
    'command_suite',
    'priority_config_key',
    'specification_dir',
    'template_dir',
    'trusted_keys_config_key',
    'url_scheme',
]


# Defines a datalad command suite.
# This variable must be bound as a setuptools entrypoint
# to be found by datalad
command_suite = (
    # description of the command suite, displayed in cmdline help
    'DataLad remake command suite',
    [
        # specification of a command, any number of commands can be defined
        (
            # importable module that contains the command implementation
            'datalad_remake.commands.make_cmd',
            # name of the command class implementation in above module
            'Make',
            # optional name of the command in the cmdline API
            'make',
            # optional name of the command in the Python API
            'make',
        ),
        (
            # importable module that contains the command implementation
            'datalad_remake.commands.provision_cmd',
            # name of the command class implementation in above module
            'Provision',
            # optional name of the command in the cmdline API
            'provision',
            # optional name of the command in the Python API
            'provision',
        ),
    ],
)


url_scheme = 'datalad-remake'
template_dir = '.datalad/make/methods'
specification_dir = '.datalad/make/specifications'
trusted_keys_config_key = 'datalad.make.trusted-keys'
allow_untrusted_execution_key = 'datalad.make.allow-untrusted-execution.d-'
priority_config_key = 'datalad.make.priority'
auto_remote_name = 'datalad-remake-auto'
