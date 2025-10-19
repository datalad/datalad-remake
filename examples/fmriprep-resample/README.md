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
> datalad clone https://hub.datalad.org/m-wierzba/ds001734-remake-demo.git my-project
> cd my-project
> datalad get -n code/containers
> datalad get -n data/ds001734
> datalad get -n derivatives/ds001734
```

The dataset was created based on the tutorial steps described [here](https://github.com/datalad/datalad-remake/blob/main/examples/fmriprep-singularity) and it is organized in a modular way. It contains raw BIDS data (`data/ds001734`), as well as fMRIPrep derivative data (`derivatives/ds001734`). Also, it includes the software container with fMRIPrep (`code/containers`).

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
│   ├── filter.json
│   ├── make
│   └── resample.py
├── data
│   └── ds001734
└── derivatives
    └── ds001734
```

### Inspect dataset's content

Our goal is to obtain the preprocessed BOLD image: `sub-001_task-MGT_run-01_space-MNI152NLin2009cAsym_desc-preproc_bold.nii.gz`. In fact, this file is already included in the example dataset.

Upon running `git annex whereis`, we learn that this file can be obtained via `datalad-remake-auto` special remote. This is because the file was originally created using DataLad Remake (see [here](https://github.com/datalad/datalad-remake/blob/main/examples/fmriprep-singularity)).

```bash
> cd derivatives/ds001734
> git annex whereis **/sub-001_task-MGT_run-01_space-MNI152NLin2009cAsym_desc-preproc_bold.nii.gz
whereis sub-001/func/sub-001_task-MGT_run-01_space-MNI152NLin2009cAsym_desc-preproc_bold.nii.gz (2 copies) 
        65a6107f-fe44-4f6c-9a4f-8a0ab5c17672 -- [datalad-remake-auto]
        a2dfc37e-9ea6-45b7-9c43-26058c2aa206 -- git@d6951ae9b36f:/var/lib/gitea/git/repositories/m-wierzba/ds001734-derivatives-remake-demo.git [origin]

  datalad-remake-auto: datalad-remake:///?label=fmriprep-singularity&root_version=c3b4f6bff479fe25b77affa5eb2015a1a831dfa6&specification=e85277aa6d05644d13c88e981e8148c2&this=derivatives/ds001734/sub-001/func/sub-001_task-MGT_run-01_space-MNI152NLin2009cAsym_desc-preproc_bold.nii.gz
ok
```

We can inspect the specification of the method originally used to create this file.

```bash
> cd $HOME/my-project
> jq . .datalad/make/specifications/e85277aa6d05644d13c88e981e8148c2 
{
  "input": [
    "code/containers/images/bids/bids-fmriprep--24.1.0.sing",
    "data/ds001734/T1w.json",
    "data/ds001734/dataset_description.json",
    "data/ds001734/participants.tsv",
    "data/ds001734/sub-001/**",
    "data/ds001734/task-MGT_bold.json"
  ],
  "method": "fmriprep-singularity",
  "output": [
    "derivatives/ds001734/**"
  ],
  "parameter": {
    "container": "code/containers/images/bids/bids-fmriprep--24.1.0.sing",
    "filter_file": "code/filter.json",
    "input_dir": "data/ds001734",
    "license_file": "/tmp/license.txt",
    "output_dir": "derivatives/ds001734",
    "participant_label": "001"
  },
  "stdout": null
}
```

Upon reviewing the `fmriprep-singularity` method, we learn that the command used to create the file was as follows:

```bash
> cat .datalad/make/methods/fmriprep-singularity | tail -18

command = [
    'singularity',
    'run', '{container}',
    '{root_directory}/{input_dir}',
    '{root_directory}/{output_dir}',
    'participant',
    '--participant-label', '{participant_label}',
    '--bids-filter-file', '{filter_file}',
    '--omp-nthreads', '1',
    '--random-seed', '2137',
    '--skull-strip-fixed-seed',
    '--sloppy',
    '--fs-license-file', '{license_file}',
    '--skip_bids_validation',
    '--fs-no-reconall',
    '--output-spaces', 'MNI152NLin6Asym:res-2', 'MNI152NLin2009cAsym'
]
```

Thus, the file was initially created by running a standard, full fMRIPrep pipeline. In the next steps, we will attempt to recreate this file using a different method that is much less computationally expensive.

### Adjust the cost of using git-annex special remotes

When determining which remote to transfer annexed files from, ones with lower costs are preferred. The default cost is 100 for local repositories, and 200 for remote repositories. Similarly, the default cost for the `datalad-remake-auto` special remote is 100.

As a result, at the time of provisioning inputs for a given computation, recreating them via `datalad-remake-auto` will be preferred over pulling them from a remote repository. To temporarily override this behavior, we modify the cost associated with the `datalad-remake-auto` special remote.

```bash
> cd $HOME/my-project
> git config remote.datalad-remake-auto.annex-cost 1000
```

**NOTE:** You may want to change the default cost for `datalad-remake-auto` back to 100 after completing this tutorial. Here, we do that only to avoid running the full fMRIPrep pipeline.

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

Upon running `git annex whereis` again, we see that `sub-001_task-MGT_run-01_space-MNI152NLin2009cAsym_desc-preproc_bold.nii.gz` is now associated with two different methods.
