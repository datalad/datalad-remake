Trusted execution
=================

By default, ``datalad-remake`` will only perform "trusted" computations. That
holds for the direct execution via ``datalad make`` as well as for the indirect
execution via the git-annex special remote as a result of ``datalad get``. A
computation is trusted, if the method and the parameters that define the
computation are trusted.

A method is considered "trusted" if the last commit to the method template is
signed by a trusted key.

Parameters, i.e. input, output, and method-parameter values, are initially
provided in the ``datalad make`` command line. If the ``datalad make`` command
executes successfully, they will be associated with the output files of the
``datalad make`` command. These associations are done via a commit to the
dataset and a call to ``git annex addurl``. Parameters are considered "trusted"
if:

1. they are provided by the user via the ``datalad make`` command line, or
2. they were associated with a file in a commit that is signed by a trusted key.

Trusted keys
------------

Signature validation is performed by ``git verify-commit``, which uses GPG to
perform the cryptographic processes. To successfully verify a signature, the
signer's public key must be added to the active GPG-keyring. To indicate to
``datalad make`` that the signer should be trusted, the key-id of the signer's
public key must be added to the Git configuration variable
``datalad.make.trusted-keys``. To ensure that the user has control over trusted
keys, datalad-remake will not read this variable from the repository
configuration, but only from Git global variables, from Git system variables, or
from the command itself (via the option `-c`).

A trusted key could, for example, be added by executing the following command:


.. code-block:: console

   $ git config --global --add datalad.make.trusted-keys <key-id>


If more than one key should be defined as trusted, the configuration variable
``datalad.make.trusted-keys`` can be set to a comma-separated list of key-ids,
e.g.:

.. code-block:: console

   $ git config --global --add datalad.make.trusted-keys <key-id-1>,<key-id-2>,...,<key-id-n>

The key-id can be obtained via ``gpg --list-keys --keyid-format long``. The key
id is the part after the ``/`` in the ``pub`` line. For example, in the
following output:

.. code-block:: console

   $ gpg --list-keys --keyid-format long
   /tmp/test_simple_verification0/gpg/pubring.kbx
   --------------------------------------------------------------------------
   pub   rsa4096/F1B64364FF34DDCB 2024-10-28 [SCEAR]
         F6AC1EE006B3E2D0805DA103F1B64364FF34DDCB
   uid                 [ultimate] Test User <test@example.com>


the key id is ``F1B64364FF34DDCB``. To inform ``datalad make`` and the git-annex
special remote that this key is trusted, the following command could be used:
    
.. code-block:: console
                
   $ git config --global --add datalad.make.trusted-keys F1B64364FF34DDCB

For instructions how to sign commits, see the relevant chapter in the `Pro Git
Book <https://git-scm.com/book/en/v2/Git-Tools-Signing-Your-Work>`_.
