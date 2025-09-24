Delineation from related solutions
==================================

DataLad (re)run
---------------

DataLad provides `run
<https://docs.datalad.org/en/stable/generated/man/datalad-run.html>`_
and `rerun
<https://docs.datalad.org/en/stable/generated/man/datalad-rerun.html>`_
commands which are similar to ``make`` in that they also (re)execute
arbitrary commands and record their impact on a dataset. However,
there are key differences:

- While ``make`` can be used to compute a file for the first time,
  there is no "remake" command. Instead, recomputation is done by the
  remake special remote during ``get`` and therefore should behave no
  different from file downloads typically performed by ``get``.
- The remake special remote operates in a temporary worktree, set to
  the commit recorded by ``datalad make``. ``rerun`` operates in the
  dataset's main worktree and by default executes commands at HEAD
  (starting point can be specified with ``rerun --onto``).
- The goal of the remake special remote is to recompute the contents
  of an annexed file, and it will produce an error if the file can not
  be reproduced. ``rerun`` can be used to verify computational
  reproducibility but also to re-run same code with different inputs,
  so it creates a new commit if the outputs differ.
- The specification of data dependencies and compute instructions is
  different, with ``make`` using committed files and ``run`` using
  commit messages.

Git-annex compute special remote
--------------------------------

Git-annex provides a built-in `compute special remote
<https://git-annex.branchable.com/special_remotes/compute/>`_ (see
also: `computing annexed files
<https://git-annex.branchable.com/tips/computing_annexed_files/>`_). This
is a parallel development to DataLad-remake, and as such there are key
differences in both implementation and behavior:

- Specification of compute instructions and file dependencies is
  different. Git-annex expects a compute program to communicate inputs
  and outputs using standard input / output. DataLad-remake expects a
  configuration file with command parameterization (compute template)
  and a list of input and output file patterns.
- The storage of compute instructions is different; git-annex uses its
  VURL backend for annex keys and stores additional information in the
  git-annex branch (unlike DataLad-annex, it does not commit
  additional files to the same branch as the computed files).
- The trust model is different: while DataLad-remake relies on
  GPG-signed commits, Git-annex compute relies on a list of allowed
  compute programs
- By default, git-annex does not assume that the computed file needs
  to be bit-by-bit reproducible (it has the ``--reproducible`` option
  to enforce computational reproducibility).
- Git-annex does not operate on subdatasets (submodules), all inputs
  need to be gettable from the given Git repository.
