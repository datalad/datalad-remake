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

This extension requires Python >= `3.9`.


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
parameters = ['first', 'second', 'output']

command = [
    "bash",
    "-c",
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

### Prospective computation
The `datalad make` command can also be used to perform a *prospective
computation*. To use this feature, the following configuration value 
has to be set ():

```bash
> git config remote.datalad-remake.annex-security-allow-unverified-downloads ACKTHPPT
```

<details>
    <summary>Why does the configuration variable have to be set?</summary>

This setting allows git-annex to download files from the special remote `datalad-remake`
although git-annex cannot check a hash to verify that the content is correct.
Because the computation was never performed, there is no hash available for content
verification of an output file yet.

For more information see the description of
`remote.<name>.annex-security-allow-unverified-downloads` and of
`annex.security.allow-unverified-downloads` at
https://git-annex.branchable.com/git-annex/.
</details>

Afterwards, a prospective computation can be initiated by using the 
`--prospective-execution` option:

```bash
> datalad make -p first=john -p second=susan -p output=person \
-o person-1.txt -o person-2.txt --prospective-execution --allow-untrusted-execution one-to-many
```

The following command will fail, because no computation has been performed,
and the file content is unavailable:

```bash
> cat person-1.txt    # this will fail, because the computation has not yet been performed
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
content: john
```

Additional examples can be found in the [examples](https://github.com/datalad/datalad-remake/tree/main/examples) directory.


## Trusted execution

By default, the `datalad-remake` will only perform "trusted"
computations. That holds for the direct execution via `datalad make` as well as
for the indirect execution via the git-annex special remote as a result of
`datalad get`. A computation is trusted, if the method and the parameters
that define the computation are trusted.

A method is considered "trusted" if the last commit to the method template
is signed by a trusted key.

Parameters, i.e. input, output, and method-parameter values, are initially
provided in the `datalad make` command line. If the `datalad make` command
executes successfully, they will be associated with the output files of the
`datalad make` command. These associations are done via a commit to the dataset
and a call to `git annex addurl`. Parameters are considered "trusted" if:

1. they are provided by the user via the `datalad make` command line, or
2. they were associated with a file in a commit that is signed by a trusted key.

### Trusted keys

Signature validation is performed by `git verify-commit`, which uses GPG to
perform the cryptographic processes. To successfully verify a signature, the
signer's public key must be added to the active GPG-keyring. To indicate to
`datalad make` that the signer should be trusted, the key-id of the signer's
public key must be added to
the git configuration variable `datalad.make.trusted-keys`. This can be done
via the command:

```bash
> git config --add datalad.make.trusted-keys <key-id>
```

If more than one key should be defined as trusted, the configuration variable
`datalad.make.trusted-keys` can be set to a comma-separated list of key-ids,
e.g.:

```bash
> git config datalad.make.trusted-keys <key-id-1>,<key-id-2>,...,<key-id-n>
```

The key-id can be obtained via `gpg --list-keys --keyid-format long`. The key
id is the part after the `/` in the `pub` line. For example, in the following
output:

```bash
> gpg --list-keys --keyid-format long
/tmp/test_simple_verification0/gpg/pubring.kbx
--------------------------------------------------------------------------
sec   rsa4096/F1B64364FF34DDCB 2024-10-28 [SCEAR]
      F6AC1EE006B3E2D0805DA103F1B64364FF34DDCB
uid                 [ultimate] Test User <test@example.com>

```
the key id is `F1B64364FF34DDCB`. To inform `datalad make` and the git-annex
special remote that this key is trusted, the following command could be used:
    
```bash
> git config --add datalad.make.trusted-keys F1B64364FF34DDCB
```
For instructions how to sign commits, see the [Git documentation](https://git-scm.com/book/en/v2/Git-Tools-Signing-Your-Work).

# Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) if you are interested in internals or
contributing to the project.


# Acknowledgements

This development was supported by European Union’s Horizon research and
innovation programme under grant agreement [eBRAIN-Health
(HORIZON-INFRA-2021-TECH-01-01, grant no.
101058516)](https://cordis.europa.eu/project/id/101058516).
