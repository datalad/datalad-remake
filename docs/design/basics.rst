Basic principles
================

Provide -- execute -- collect
-----------------------------

DataLad-remake (re)computes in three stages:

- Provisioning: creates a temporary, partial copy of the dataset (worktree) to provide an isolated environment.
  Uses `git-worktree <https://git-scm.com/docs/git-worktree>`_ (unless on Windows, where it clones the dataset instead).
  Checks out the given commit, if specified. Gets all input files in the worktree. Installs subdatasets as needed.
- Execution: runs the computation in the provisioned worktree.
  Before running, gets and unlocks outputs which are already available; installs subdatasets as needed.
- Collection: copies the output files from the provisioned worktree into the dataset (main worktree).
  Ensures that subdatasets which may receive outputs are installed before copying, and saves recursively afterwards.

Note: when a file is recomputed during ``datalad get``, remake uses
the commit originally recorded by ``datalad make`` to provide the
worktree.  This means that recompute will use the same versions of the
input files as the original computation, even if the files got changed
in the meantime.

Recomputing during ``datalad get`` assumes that the process is
reproducible (bit-by-bit) and will error if the file checksum is
different.

Because provisioning involves git worktree or clone, all Git-tracked
files are automatically available in the provisioned worktree. Annexed
files have to be declared as inputs, if they are to be provisioned.

Storing compute instructions
----------------------------

DataLad-remake stores compute instructions (command template, data
dependencies, etc.) in text files committed to the dataset. These
files are in the same branch as the (re)computed files. By default,
DataLad remake expects commits adding compute instructions to be
signed. For more details, see :doc:`files` and
:doc:`trusted-execution`.

DataLad-remake also uses `git annex addurl
<https://git-annex.branchable.com/git-annex-addurl/>`_ to associate
``datalad-remake://`` URLs with computed files in order to link them
to the compute instructions. This URLs are handled by the remake
special remote. They contain: label of the compute template, Git
commit which added the compute specification, and the name (hash) of
the compute specification file.

Prospective execution
---------------------

By default, ``datalad make`` runs a computation, stores the compute
specification, and associates it with the output files. However, it is
also possible to skip computation, and only register compute
instructions for future use by ``datalad get`` (for example, for files
already computed via different means). This behavior can be chosen
using the ``--prospective-execution`` flag.
