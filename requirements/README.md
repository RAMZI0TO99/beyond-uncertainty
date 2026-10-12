# Development environment snapshot

For Windows x64, use a general-host **CPython 3.13** installation. The recorded environment used **3.13.5**. Create a new environment from the repository root:

```powershell
py -3.13 -I -S -B tools/setup_dev.py
```

An explicit Python 3.13 executable works instead of `py -3.13`. The helper creates `.venv`, installs the pinned development dependencies and this checkout in editable mode, then reads installed distribution metadata. It uses official PyPI and the official PyTorch CPU wheel index. It does not import the project or run tests, figures, training, archived helpers or scientific cases.

Select a different new directory with `--venv`. A directory that already contains anything is refused; an explicitly selected empty directory is allowed. The default `.venv` must not exist. Failed installations are retained for inspection, without automatic deletion or overwriting. Inspect an existing environment without launching its interpreter or changing it:

```powershell
py -3.13 -I -S -B tools/setup_dev.py --check --venv .venv
```

When Windows long-path support is disabled or its setting cannot be read, the environment's full absolute path must be at most65 UTF-16 units. The pinned CPU Torch wheel contains an installed license suffix190 units long; a74-unit target produced `WinError206` during the first isolated setup attempt. Setup now checks this before creating the environment and changes no registry settings. Keep the checkout near the drive root or select a fresh short target:

```powershell
py -3.13 -I -S -B tools/setup_dev.py --venv D:/bu-dev
```

An earlier partially installed environment is retained and must not be reused for another installation. Choose a different new path. The65-unit bound is a conservative safeguard for the inspected Windows dependency snapshot, not a guarantee for arbitrary future package versions or every Windows application.

[windows-cp313-cpu.txt](windows-cp313-cpu.txt) records the 37 observed non-project distributions, including pip26.2.1 and setuptools84.0.0. It pins the actual CPU PyTorch build, `2.13.0+cpu`: the recorded torch distribution metadata said `2.13.0`, while its `torch/version.py` explicitly identified `2.13.0+cpu` and `cuda=None`. The project remains a local editable install rather than a machine-bound `file://` dependency.

The bundled [PyYAML6.0.1 wheel](wheels/README.md) avoids rebuilding that old release on CPython3.13. The helper verifies its exact SHA256 before creating an environment or passing it to pip. Subsequent package installation requires wheels, so an unavailable compatible dependency stops setup instead of silently compiling it or substituting a different version.

This is a version snapshot and a verified PyYAML artifact, **not a complete hash-locked dependency/build reproduction**. Other wheels are downloaded and resolved for this platform. Their complete acquisition hashes and build provenance are not supplied by this file. The frozen historical runtime and its filesystem identities are separate evidence; the copied `.venv` and its absolute editable paths must not be reused as a new environment.

The scientific package declares Python>=3.11, but this snapshot and bundled wheel target Windows x64/CPython3.13. For Linux or macOS, create a separate isolated environment and resolve compatible packages from `pyproject.toml`; this Windows helper intentionally refuses that installation. Such an environment is ordinary development only, not a reproduction of the historical Windows execution environment.

Restored `.npy`/`.npz` payloads, fit records, ledgers, manifests and independent copies retain their original bytes and provenance. Environment setup does not recover missing artifacts, reproduce old filesystem identities, extend leases or admit execution. Read [CONTINUE.md](../CONTINUE.md) and [AGENTS.md](../AGENTS.md) before further project work.
