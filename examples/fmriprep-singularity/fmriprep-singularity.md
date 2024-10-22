# Use case: running fMRIprep in a singularity container

This example demonstrates how to run fMRIprep on a single subject of a BIDS dataset using a singularity container. Specifically, the singularity container used in this example is `bids-fmriprep--24.1.0` and comes from the [ReproNim containers collection](https://github.com/ReproNim/containers).

The example comprises the following files:
- `fmriprep-singularity` template
- `input.txt` input specification
- `output.txt` output specification
- `parameter.txt` parameters

## Requirements

This example requires Singularity.

Please note, that there is no need to install fMRIprep. The singularity container will be automatically retrieved from the ReproNim containers collection. However, in order to use fMRIprep you need to obtain a [FreeSurfer license](https://surfer.nmr.mgh.harvard.edu/fswiki/License). 

Please also note that fMRIprep is invoced with the option `--sloppy`. This is done to reduce the runtime. For reproducible results, please run fMRIprep without the option `--sloppy`.

It is assumed that the license file is located in `/tmp`. Make sure to copy it there or modify the `parameter.txt` file accordingly (see the [Add template](#add-template) section below).

## How to install

Install `datalad-remake` extension, as described [here](https://github.com/christian-monch/datalad-compute/tree/main?tab=readme-ov-file#installation).

## How to use

It is assumed that you have a local copy of the `datalad-remake` project in your `$HOME` directory. If this not the case, adjust the path below:

```
EXAMPLE=$HOME/datalad-remake/examples/fmriprep-singularity
```

### Create dataset

Create a dataset, together with its subdatasets:

```
cd $HOME
datalad create -c text2git my-project

cd my-project

datalad clone -d . https://github.com/ReproNim/containers code/containers
datalad get -n code/containers

datalad clone -d . https://github.com/OpenNeuroDatasets/ds000102 data/ds000102
datalad get -n data/ds000102

datalad create -d . derivatives/ds000102
```

The dataset used in this example is organized in a modular way. In particular, input data (`data/ds000102`) and output data (`derivatives/ds000102`) are tracked in separate subdatasets, as is the software container (`code/containers`).

The resulting dataset structure is as follows:

```
my-project
├── code
│   └── containers
├── data
│   └── ds000102
└── derivatives
    └── ds000102
```

### Configure special remote

Configure the dataset in which you want to collect the results of the (re)computation, in this case `derivatives/ds000102` subdataset.

```
cd $HOME/my-project/derivatives/ds000102
```

Add a `datalad-remake` special remote:

```
git annex initremote compute type=external externaltype=datalad-remake encryption=none
```


### Add template

Place the `fmriprep-singularity` template in the `.datalad/remake/methods` of the root dataset:

```
cd $HOME/my-project

mkdir -p .datalad/remake/methods
cp $EXAMPLE/fmriprep-singularity .datalad/remake/methods/fmriprep-singularity

datalad save -m "Add a remake method"
```

Place the `input.txt`, `output.txt` and `parameter.txt` files in the root dataset. These files do not have to be tracked in git history, so no `datalad save` is required at this point.

```
cp $EXAMPLE/*.txt ./
```

### Execute (re)computation

To test the example, run:

```
cd $HOME/my-project
datalad make -I input.txt -O output.txt -P parameter.txt fmriprep-singularity
```

You can also do that in `debug` mode:

```
datalad -l debug make -I input.txt -O output.txt -P parameter.txt fmriprep-singularity
```
