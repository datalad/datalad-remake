The `datalad-remake` documentation
**********************************

This extension equips DataLad with the functionality to (re)compute file
content on demand, based on a specified set of instructions. In particular,
it features a `datalad make` command for capturing instructions on how to
compute a given file, allowing the file content to be safely removed. It also
implements a git-annex special remote, which enables the (re)computation of
the file content based on the captured instructions. This is particularly
useful when the file content can be produced deterministically. If storing
the file content is more expensive than (re)producing it, this functionality
can lead to more effective resource utilization. Thus, this extension may be
of interest to a wide, interdisciplinary audience, including researchers,
data curators, and infrastructure administrators.


Functionality provided by DataLad remake
========================================

.. toctree::
   :maxdepth: 1

   how-it-works/index.rst
   api.rst
   annex-specialremotes.rst


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
