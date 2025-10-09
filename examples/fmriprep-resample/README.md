# Use case: resample a BOLD image onto a target space

This example demonstrates how to run a simple Python [script](https://hub.datalad.org/mslw/fmriprep-resampling) to reproduce fMRIPrep's preprocessed BOLD image (projected onto a target space) from the raw image, ancillary fMRIPrep derivatives, and related metadata. All dependencies for the script are provided by an fMRIPrep singularity container. The singularity container used in this example is `bids-fmriprep--24.1.0` and comes from the [ReproNim containers collection](https://github.com/ReproNim/containers).

The example comprises the following files:
- `fmriprep-resample` template
- `input.txt` input specification
- `output.txt` output specification
- `parameter.txt` parameters

## Requirements

This example requires Singularity.

Please note, that there is no need to install fMRIPrep. The singularity container will be automatically retrieved from the ReproNim containers collection.

## How to install

Install `datalad-remake` extension, as described [here](https://github.com/datalad/datalad-remake/tree/main?tab=readme-ov-file#installation). Make sure that you have a valid GPG key and that you have successfully configured Git for commit signing, as described [here](https://github.com/datalad/datalad-remake/tree/main?tab=readme-ov-file#requirements).

## How to use

It is assumed that you have a local copy of the `datalad-remake` project in your `$HOME` directory. If this not the case, adjust the path below:

```
EXAMPLE=$HOME/datalad-remake/examples/fmriprep-resample
```

### Clone example dataset

To run the example, you'll need a raw BIDS dataset that has been minimally preprocessed with fMRIPrep. For a complete list of data dependencies, please refer to [this](https://github.com/datalad/datalad-remake/blob/main/examples/fmriprep-resample/input.txt) specification.

For convenience, a ready-made dataset containing all inputs required for running the example can be obtained like so:

```bash
> cd $HOME
> datalad clone https://hub.datalad.org/example my-project
> cd my-project
> datalad get -n data/ds001734
> datalad get -n derivatives/ds001734
```

The dataset is organized in a modular way. It contains raw BIDS data (`data/ds001734`), as well as fMRIPrep derivative data (`derivatives/ds001734`). Also, it includes the software container with fMRIPrep (`code/containers`).

The only thing that's missing is the Python [script](https://hub.datalad.org/mslw/fmriprep-resampling) that selectivly applies fMRIPrep's workflows to deterministically reproduce the BOLD image from the raw image, without the need to run a complete fMRIPrep preprocessing pipeline. The `resample.py` script can be obtained as follows:

```bash
> curl -o code/resample.py \
https://hub.datalad.org/mslw/fmriprep-resampling/raw/branch/main/resample.py
> datalad save -m "Add resampling script"
```

The resulting dataset structure is as follows:

```
my-project
├── code
│   ├── containers
│   ├── make
│   └── resample.py
├── data
│   └── ds001734
└── derivatives
    └── ds001734
```

### Add template

Place the `fmriprep-resample` template in the `.datalad/make/methods` of the root dataset:

```bash
> cd $HOME/my-project
> cp $EXAMPLE/fmriprep-resample .datalad/make/methods/fmriprep-resample
> datalad save -m "Add a make method"
```

Place the `input.txt`, `output.txt` and `parameter.txt` files in the root dataset. These files do not have to be tracked in git history, so no `datalad save` is required at this point.

```bash
> mkdir -p code/make/fmriprep-resample
> cp $EXAMPLE/*.txt ./code/make/fmriprep-resample/
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
-I code/make/fmriprep-resample/input.txt \
-O code/make/fmriprep-resample/output.txt \
-P code/make/fmriprep-resample/parameter.txt \
fmriprep-resample
```
