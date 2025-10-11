# Use case: running fMRIPrep with the `fmriprep-docker` wrapper 

This example demonstrates how to run fMRIPrep on a single subject of a BIDS dataset using `fmriprep-docker` [wrapper](https://fmriprep.org/en/20.0.0/docker.html#running-fmriprep-with-the-fmriprep-docker-wrapper).

The example comprises the following files:
- `fmriprep-docker` template
- `input.txt` input specification
- `output.txt` output specification
- `parameter.txt` parameters

## Requirements

This example requires `fmriprep-docker` wrapper [installed](https://fmriprep.org/en/20.0.0/installation.html#the-fmriprep-docker-wrapper).

Moreover, in order to use fMRIPrep you need to obtain a [FreeSurfer license](https://surfer.nmr.mgh.harvard.edu/fswiki/License).

It is assumed that the license file is located in `/tmp`. Make sure to copy it there or modify the `parameter.txt` file accordingly (see the [Add template](#add-template) section below).

## How to install

Install `datalad-remake` extension, as described [here](https://github.com/datalad/datalad-remake/tree/main?tab=readme-ov-file#installation). Make sure that you have a valid GPG key and that you have successfully configured Git for commit signing, as described [here](https://github.com/datalad/datalad-remake/tree/main?tab=readme-ov-file#requirements).

## How to use

It is assumed that you have a local copy of the `datalad-remake` project in your `$HOME` directory. If this not the case, adjust the path below:

```
EXAMPLE=$HOME/datalad-remake/examples/fmriprep-docker
```

### Create dataset

Create a dataset, together with its subdatasets:

```bash
> cd $HOME
> datalad create -c text2git my-project
> cd my-project
> datalad clone -d . https://github.com/OpenNeuroDatasets/ds001734 data/ds001734
> datalad create -d . derivatives/ds001734
```

The dataset used in this example is organized in a modular way. In particular, input data (`data/ds001734`) and output data (`derivatives/ds001734`) are tracked in separate subdatasets.

The resulting dataset structure is as follows:

```
my-project
├── data
│   └── ds001734
└── derivatives
    └── ds001734
```

### Add template

Place the `fmriprep-docker` template in the `.datalad/make/methods` of the root dataset:

```bash
> cd $HOME/my-project
> mkdir -p .datalad/make/methods
> cp $EXAMPLE/fmriprep-docker .datalad/make/methods/fmriprep-docker
> datalad save -m "Add a make method"
```

Place the `input.txt`, `output.txt` and `parameter.txt` files in the root dataset. These files do not have to be tracked in git history, so no `datalad save` is required at this point.

```bash
> mkdir -p code/make/fmriprep-docker
> cp $EXAMPLE/*.txt ./code/make/fmriprep-docker/
```

### Configure trusted keys

Configure trusted keys, by executing the command below. Replace `<key-id>` with a GPG key that you have used for signing commits. For more details, please go [here](https://github.com/datalad/datalad-remake#trusted-keys).

```bash
> git config --global --add datalad.make.trusted-keys <key-id>
```

### Execute (re)computation

To test the example, run:

```bash
> cd $HOME/my-project
> datalad make \
-I code/make/fmriprep-docker/input.txt \
-O code/make/fmriprep-docker/output.txt \
-P code/make/fmriprep-docker/parameter.txt \
fmriprep-docker
```

You can also do that in `debug` mode:

```bash
> datalad -l debug make \
-I code/make/fmriprep-docker/input.txt \
-O code/make/fmriprep-docker/output.txt \
-P code/make/fmriprep-docker/parameter.txt \
fmriprep-docker
```

### Final note

In this example fMRIPrep is invoked with the option `--sloppy` to reduce the runtime. For reproducible results, run fMRIPrep without `--sloppy`.
