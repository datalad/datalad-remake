# datalad-remake

[![Documentation Status](https://readthedocs.org/projects/datalad-remake/badge/?version=latest)](https://datalad-remake.readthedocs.io/en/latest/?badge=latest)
[![Build status](https://ci.appveyor.com/api/projects/status/25vbds4nncadopf8/branch/main?svg=true)](https://ci.appveyor.com/project/mih/datalad-remake/branch/main)
[![codecov](https://codecov.io/github/datalad/datalad-remake/graph/badge.svg?token=EBVAZXLF0J)](https://codecov.io/github/datalad/datalad-remake)
[![Hatch project](https://img.shields.io/badge/%F0%9F%A5%9A-Hatch-4051b5.svg)](https://github.com/pypa/hatch)


**NOTE:** This extension is currently work-in-progress!


## About

This extension equips DataLad with the functionality to generate file content on
demand, based on a specified set of instructions. This is particularly useful
when the file content can be (re)obtained deterministically. If storing the
file content is more expensive than (re)generating it, this functionality can
lead to more effective resource utilization. Thus, this extension may be of
interest to a wide, interdisciplinary audience, including researchers, data
curators, and infrastructure administrators.


## How it works

This extension provides a new command called `datalad make`.

By default, `datalad make` triggers the computation of content, generates a URL,
and associates this URL with the respective file (represented by a git-annex
key). The associated URL encodes all the information necessary to (re)make the
file content. 

It is also possible to perform a *prospective computation*, in which case the
URL is recorded, without initiating the computation. This URL can then be used
to actually perform the computation.

If the computation is performed, the URL is associated with a FILE-KEY,
otherwise the URL is associated with a URL-KEY. For more information on 
git-annex backends, go [here](https://git-annex.branchable.com/backends/).

The URLs are handled by a `datalad-remake` git-annex special remote, implemented in
this extension.


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


## Synopsis

```
datalad make [-i INPUT] [-o OUTPUT] [-p PARAMETER] [-u] TEMPLATE
```

By design, to perform the computation `datalad make` creates a temporary Git
worktree. All inputs required for the computation are automatically provisioned
to this temporary worktree, then the specified computation is performed, and
finally, all requested outputs are transferred back to the original dataset.

The command is invoked with the following arguments:

**`-i INPUT, --input INPUT`** (optional)

Specification of the input file(s) to be provisioned to a temporary Git
worktree. Paths need to be specified relative to the dataset in which `datalad
make` is executed.

**`-o OUTPUT, --output OUTPUT`**

Specification of the output file(s) to transfer back to the target dataset after
the computation. Paths need to be specified relative to the dataset in which
`datalad make` is executed.

**`-p PARAMETER, --parameter PARAMETER`** (optional)

Parameters for the computation, specified in a key-value format (e.g. `-p
key=value`).

**`-u`** (optional)

Run the command in a URL-only mode. If specified, a *prospective computation*
will be performed, i.e. only the URL will be recorded, without initiating the
computation.

**`TEMPLATE`**

Name of the method template used to perform the computation. The template should
be stored in `$DATASET_ROOT/.datalad/make/methods`. The template itself is a
simple text file, containing the following variables:
- `command`: command to be used for the computation
- `parameters` (optional):  list of strings, corresponding to the parameters for
  the computation
- `use_shell`: a boolean determining whether to use shell interpretation

Please note, that placeholders (denoted with curly braces) are supported to allow
for the parametrized execution of the command.

Also, in some cases, it may be more convenient to store inputs, outputs, and
parameters in external files. To support this, uppercase variants of the
command options have been introduced, i.e. `-I`, `-O` and `-P`, respectively.

```
datalad make -I input.txt -O output.txt -P parameter.txt TEMPLATE
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
> git annex initremote datalad-remake encryption=none type=external externaltype=datalad-remake
```

Execute a computation and save the result:
```bash
> datalad make -p first=bob -p second=alice -p output=name \
-o name-1.txt -o name-2.txt one-to-many
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

Afterwards, a prospective computation can be initiated by using the `-u`
option:

```bash
> datalad make -p first=john -p second=susan -p output=person \
-o person-1.txt -o person-2.txt -u one-to-many
```

This will fail, because no computation has been performed, and the file content
is unavailable:

```bash
> cat person-1.txt
```

However, `ls -l` will show a symlink to a URL-KEY:

```bash
> ls -l person-1.txt
```

Similarly, `git annex whereis` will show the associated URL, that encodes all
the information necessary and sufficient to generate the file content:

```bash
> git annex whereis person-1.txt
```

Based on this URL, `datalad get` can be used to generate the file content for
the first time based on the specified instructions:

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
