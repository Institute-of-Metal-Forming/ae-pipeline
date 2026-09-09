# AE Pipeline

This repository contains a WIP data analysis pipeline for acoustic emission (AE) data obtained from Vallen AE Measurement Systems.
The pipeline is built on PyTask to manage task execution.

All software needed to work with the repository is provided via [`devenv`](https://devenv.sh/).
To create a shell environment with all software and config available, run:

```sh
devenv shell
```

The usual commands needed to work with the repository are provided by Just (see [`justfile`](./justfile)).
To see all available commands run:

```sh
just
```

To process all data simply run:

```sh
just build
```
