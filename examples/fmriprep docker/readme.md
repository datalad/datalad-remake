# Use case: running fMRIprep with the `fmriprep-docker` wrapper 

This example demonstrates how to run fMRIprep on a single subject of a BIDS dataset using `fmriprep-docker` [wrapper](https://fmriprep.org/en/20.0.0/docker.html#running-fmriprep-with-the-fmriprep-docker-wrapper).

The example comprises the following files:
- `fmriprep-docker` template
- `input.txt` input specification
- `output.txt` output specification
- `parameter.txt` parameters

## Requirements

This example requires `fmriprep-docker` wrapper [installed](https://fmriprep.org/en/20.0.0/installation.html#the-fmriprep-docker-wrapper).

Moreover, in order to use fMRIprep you need to obtain a [FreeSurfer license](https://surfer.nmr.mgh.harvard.edu/fswiki/License).

It is assumed that the license file is located in `/tmp`. Make sure to copy it there or modify the `parameter.txt` file accordingly (see the [Add template](#add-template) section below).

## How to install

Install `datalad-remake` extension, as described [here](https://github.com/datalad/datalad-remake/tree/main?tab=readme-ov-file#installation).

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
> datalad clone -d . https://github.com/OpenNeuroDatasets/ds000102 data/ds000102
> datalad create -d . derivatives/ds000102
```

The dataset used in this example is organized in a modular way. In particular, input data (`data/ds000102`) and output data (`derivatives/ds000102`) are tracked in separate subdatasets.

The resulting dataset structure is as follows:

```
my-project
├── data
│   └── ds000102
└── derivatives
    └── ds000102
```

### Configure special remote

Configure the dataset in which you want to collect the results of the (re)computation, in this case `derivatives/ds000102` subdataset.

```bash
> cd $HOME/my-project/derivatives/ds000102
```

Add a `datalad-remake` special remote:

```bash
> git annex initremote datalad-remake type=external externaltype=datalad-remake encryption=none
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
> cp $EXAMPLE/*.txt ./
```

### Execute (re)computation

To test the example, run:

```bash
> cd $HOME/my-project
> datalad make -I input.txt -O output.txt -P parameter.txt fmriprep-docker
```

You can also do that in `debug` mode:

```bash
> datalad -l debug make -I input.txt -O output.txt -P parameter.txt fmriprep-docker
```

### Final note

In this example fMRIprep is invoked with the option `--sloppy` to reduce the runtime. For reproducible results, run fMRIprep without `--sloppy`.
