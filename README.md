# datalad-remake

[![Documentation Status](https://readthedocs.org/projects/datalad-remake/badge/?version=latest)](https://datalad-remake.readthedocs.io/en/latest/?badge=latest)
[![Build status](https://ci.appveyor.com/api/projects/status/25vbds4nncadopf8/branch/main?svg=true)](https://ci.appveyor.com/project/mih/datalad-remake/branch/main)
[![codecov](https://codecov.io/github/datalad/datalad-remake/graph/badge.svg?token=EBVAZXLF0J)](https://codecov.io/github/datalad/datalad-remake)
[![Hatch project](https://img.shields.io/badge/%F0%9F%A5%9A-Hatch-4051b5.svg)](https://github.com/pypa/hatch)


**NOTE:** This extension is currently work-in-progress!


## About

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


## Requirements

This extension requires Python >= `3.11`.


## Installation

There is no PyPI package yet. To install the extension, clone the repository
and install it via `pip` (preferably in a virtual environment):

```bash
> git clone https://github.com/datalad/datalad-remake.git
> cd datalad-remake
> pip install -r requirements-devel.txt
> pip install .
```

To check your installation, run:

```bash
> datalad make --help
```


## Example usage

Create a dataset:


```bash
> datalad create remake-test-1
> cd remake-test-1
```

Create a template and place it in the `.datalad/make/methods` directory:

```bash
> mkdir -p .datalad/make/methods
> cat > .datalad/make/methods/one-to-many <<EOF
parameter = ['first', 'second', 'output']

use_shell = 'true'
command = [
    "echo content: {first} > '{output}-1.txt'; echo content: {second} > '{output}-2.txt'",
]
EOF
> datalad save -m "add `one-to-many` remake method"
```

Create a `datalad-remake` git-annex special remote:
```bash
> git annex initremote datalad-remake encryption=none type=external externaltype=datalad-remake allow_untrusted_execution=true
```

Execute a computation and save the result:
```bash
> datalad make -p first=bob -p second=alice -p output=name -o name-1.txt \
-o name-2.txt --allow-untrusted-execution one-to-many
```
The method `one-to-many` will create two files with the names `<output>-1.txt`
and `<output>-2.txt`. Thus, the two files `name-1.txt` and `name-2.txt` need to
be specified as outputs in the command above.

```bash
> cat name-1.txt
content: bob
> cat name-2.txt
content: alice
```

Drop the content of `name-1.txt`, verify it is gone, recreate it via
`datalad get`, which "fetches" it from the `datalad-remake` remote:

```bash
> datalad drop name-1.txt
> cat name-1.txt
> datalad get name-1.txt
> cat name-1.txt
``` 

The `datalad make` command can also be used to perform a *prospective
computation*. To use this feature, the following configuration value 
has to be set:

```bash
> git config annex.security.allow-unverified-downloads ACKTHPPT
```

Afterwards, a prospective computation can be initiated by using the 
`-u / --url-only` option:

```bash
> datalad make -p first=john -p second=susan -p output=person \
-o person-1.txt -o person-2.txt -u --allow_untrusted_execution one-to-many
> cat person-1.txt    # this will fail, because the computation has not yet been performed
```

The following command will fail, because no computation has been performed,
and the file content is unavailable:

```bash
> cat person-1.txt
```

We can further inspect this with `git annex info`:

```bash
> git annex info person-1.txt
```

Similarly, `git annex whereis` will show the URL, that can be handled by the
git-annex special remote:

```bash
> git annex whereis person-1.txt
```

Finally, `datalad get` can be used to produce the file content (for the first
time!) based on the specified instructions:

```bash
> datalad get person-1.txt
> cat person-1.txt
```


# Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) if you are interested in internals or
contributing to the project.


# Acknowledgements

This development was supported by European Union’s Horizon research and
innovation programme under grant agreement [eBRAIN-Health
(HORIZON-INFRA-2021-TECH-01-01, grant no.
101058516)](https://cordis.europa.eu/project/id/101058516).
