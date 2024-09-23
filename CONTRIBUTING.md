# Contributing to `datalad-remake`

- [Developer cheat sheet](#developer-cheat-sheet)
- [Code organization](#code-organization)
- [Style guide](#contribution-style-guide)


## Developer cheat sheet

[Hatch](https://hatch.pypa.io) is used as a convenience solution for packaging and development tasks.
Hatch takes care of managing dependencies and environments, including the Python interpreter itself.
If not installed yet, installing via [pipx](https://github.com/pypa/pipx) is recommended (`pipx install hatch`).

Below is a list of some provided convenience commands.
An accurate overview of provided convenience scripts can be obtained by running: `hatch env show`.
All command setup can be found in `pyproject.toml`, and given alternatively managed dependencies, all commands can also be used without `hatch`.

### Run the tests (with coverage reporting)

```
hatch test [--cover]
```

There is also a setup for matrix test runs, covering all current Python versions:

```
hatch run tests:run [<select tests>]
```

This can also be used to run tests for a specific Python version only:

```
hatch run tests.py3.10:run [<select tests>]
```

### Build the HTML documentation (under `docs/_build/html`)

```
hatch run docs:build
# clean with
hatch run docs:clean
```

### Check type annotations

```
hatch run types:check
```

### Check commit messages for compliance with [Conventional Commits](https://www.conventionalcommits.org)

```
hatch run cz:check-commits
```

### Show would-be auto-generated changelog for the next release

```
hatch run cz:show-changelog
```

### Create a new release

```
hatch run cz:bump-version
```

The new version is determined automatically from the nature of the (conventional) commits made since the last release.
A changelog is generated and committed.

In cases where the generated changelog needs to be edited afterwards (typos, unnecessary complexity, etc.), the created version tag needs to be advanced.


### Build a new source package and wheel

```
hatch build
```

### Publish a new release to PyPi

```
hatch publish
```

## Contribution style guide

A contribution must be complete with code, tests, and documentation.

A high test-coverage is desirable. Contributors should aim for near-complete coverage (or better).
Tests must be dedicated for the code of a particular contribution.
It is not sufficient, if other code happens to also exercise a new feature.

### Documentation

Docstrings should be complete with information on parameters, return values, and exception behavior.
Documentation should be added to and rendered with the sphinx-based documentation.

### Commits

Commits and commit messages must be [Conventional Commits](https://www.conventionalcommits.org).
Their compliance is checked for each pull request. The following commit types are recognized:

- `feat`: introduces a new feature
- `fix`: address a problem, fix a bug
- `doc`: update the documentation
- `rf`: refactor code with no change of functionality
- `perf`: enhance performance of existing functionality
- `test`: add/update/modify test implementations
- `ci`: change CI setup
- `style`: beautification
- `chore`: results of routine tasks, such as changelog updates
- `revert`: revert a previous change
- `bump`: version update

Any breaking change must have at least one line of the format

    BREAKING CHANGE: <summary of the breakage>

in the body of the commit message that introduces the breakage.
Breaking changes can be introduced in any type of commit.
Any number of breaking changes can be described in a commit message (one per line).
Breaking changes trigger a major version update, and form a dedicated section in the changelog.

It is recommended to use the `hatch run cz:show-changelog` command to see how a change series will be represented in the changelog -- and tune as necessary to achieve a self-explanatory outcome.

### Pull requests

Contributions submitted via a pull-request (PR), are expected to be a clear, self-describing series of commits.
The PR description is largely irrelevant, and could be used for a TODO list, or conversational content.
All essential information concerning the code and changes **must** be contained in the commit messages.

Commit series should be "linear", with individual commits being self-contained, well-described changes.

If possible, only loosely related changes should be submitted in separate PRs to simplify reviewing and shorten time-to-merge.

Long-standing, inactive PRs (draft mode or not) are frowned upon, as they drain attention.i
It is often better to close a PR and open a new one, once work resumes.
Maintainers may close inactive PRs for this reason at any time.
