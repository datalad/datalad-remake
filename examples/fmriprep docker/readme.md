This directory contains a simple example for running `fmriprep-docker` on a single subject of a BIDS dataset. The template is `fmriprep-docker`, input, output, and parameter files are defined in `input.txt`, `output.txt`, and `parameter.txt`, respectively.

The example assumes that the BIDS dataset referenced in `input_dir` is a subdataset of the dataset in which the computation is started (the root-dataset), as outlined in the fairly-big-follow-up document (https://hackmd.io/7oRB8qwuRtCm6BkV44Ubww). In contrast to the fairly-big-follow-up document, the example uses another subdataset, that collects the results of the computation. The dataset layout is therefore as follows:
```
root-dataset
├── datasets
│   ├── ds000102
│
├── derivatives
    ├── ds000102
```

Executing the computation requires installation of this extension (see https://github.com/datalad/datalad-remake/tree/main/README.md), and the installation of the python package `fmriprep-docker`. The template, i.e. `fmriprep-docker` has to be placed in the folder `.datalad/make/methods` of the root-dataset (and the dataset has to be saved).

To keep the command line short, input files, output files, and parameter for the computation are defined in the lists:
- `input.txt`
- `output.txt`
- `parameter.txt`

Be sure to add a datalad-remake special remote to the dataset that contains the folder `derivatives/ds000102`.
This can be done with the following command:
```bash
> git annex initremote datalad-remake type=external externaltype=datalad-remake encryption=none
```

The computation can be executed with the following command:

```bash
> datalad make -I input.txt -O output.txt -P parameter.txt fmriprep-docker
```
