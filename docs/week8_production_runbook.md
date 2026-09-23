# Week 8 production runbook

**Status:** E2A epoch 001 externally interrupted; one D-161 recovery epoch is
authorized but not yet consumed.  D-168 supersedes the earlier startup chain
before that authority is consumed.  This runbook records the fixed operational
order; it is not a result or substitute for immutable evidence.  Every path is
below `D:/Aenv/pro2`, every fit uses the frozen CPU 4/4 route, and the GPU
remains unused.

D-171 relocation checkpoint: the controller and dependencies now live below
D:/Aenv/pro2 with explicit historical/current provenance. Preserve release
attempts001-004 and their refusals. A fresh complete gate and clean local commit
are required before V2 receipt/audits under `.tmp/week8-d168-release-attempt-005`
and independent native status. The relocated stage0 policy literals below apply;
original evidence bytes and historical identities remain separately preserved.

## Clean-revision prerequisite

All Week 8 implementation, tests, decisions and this runbook are committed
before any production preflight.  Each preflight records that exact clean Git
commit and the pinned environment.  The operational single-fit timeout remains
3,600 seconds and the launch-bound storage floor remains exactly 8 GiB
(8,589,934,592 bytes), as recorded before Week 7 production.  A dirty or
untrustworthy tree, changed upstream plan, missing historical source, active
common lease, failed storage canary, or less than that free-space floor stops
execution.

The shared lease is the existing
`week7-production-control` / `week7-production` namespace.  Experiment 2A,
Experiment 2B and sweep-002 must run serially under that one owner.  Lease age
never authorizes recovery.  D-161's incident-specific path instead requires
positive Windows process-liveness evidence, two stable inventories, an
immutable recovery authorization, and the stable lease-transition lock.

## Authorized command surfaces

D-168 supersedes the D-167 launch mechanics before the first production
recovery.  No operator invokes the entrypoint file directly.  Every D-161/E2A
command (`status`, `adjudicate`, `recover`, `seal`, `monitor`, `finalize`,
`report`, or `figures`) starts through the fixed D-168 stage-0 renderer, the
reviewed inbox Windows PowerShell host, the tracked native launcher, and the
externally hash-checked contents of `scripts/week8_recovery_outer_bootstrap.txt`.
The native launcher supplies an exact twelve-entry environment, and every
Python boundary in this recovery chain receives literal
`-I -S -B -X utf8 -c`.  The outer literal receives the externally approved
entrypoint SHA-256, raw-helper SHA-256, clean controller commit, one allowlisted
command, and the stage-0 binding.  The eight release values are written after
the final commit to an immutable V2 project-local receipt outside both
worktrees; the actual invocation contains the release literals independently.
Reading the receipt dynamically is not authority.

The only later direct module surfaces are the fixed
`bu.experiments.week8_exclusion_production` and
`bu.experiments.week8_baseline_production` wrappers.  Do not invoke
`week8_exp2a_production`, `week8_exp2a_repair_launch`, `week8_launch`, `batch`,
a runner, a script path, or another lower CLI directly.  Do not add a global,
system, or repository `safe.directory` entry.

Before project or third-party import, raw authority verifies and retains read
handles for every tracked controller/execution file and every pinned Git/site
file, then executes captured Python source through verified importers.  The
externally supplied controller commit is checked both by the outer bootstrap
and raw Git plumbing.  Each nested fit starts the pinned interpreter under
`-I -S -B -X utf8 -c`, receives only captured fit-child/helper bytes, revalidates the
same static authority, and executes the fixed historical `_fit_worker` without
pickle serialization or native `multiprocessing` spawn.  A changed, extra,
ignored, linked, reparse, unstable, unlocked, or uncommitted worktree entry
refuses before mutation.

Epoch 001 remains bound to detached execution commit
`4515d5165756c8d1669d38d2ee854fa1051b1017`.  A nonzero or ambiguous result
stops progression.  D-161 permits one continuation only after `adjudicate`.
After epoch 002 starts, only `seal` may be attempted, and only to prove an
already complete lower epoch; it executes zero fits.

## D-161 one-use E2A recovery

Epoch 001 stopped after 150 starts and 149 durable acknowledgements.  The one
unresolved job has a complete local canonical result and an interrupted hidden
destination partial; neither may be discarded or retrained.  Before mutation,
the inspector proves 149 complete pairs, that complete local-only job, 111
untouched jobs, zero failures, exact source/control hashes, and two stable
Windows liveness snapshots.  Incident and epoch-001 terminal records are then
published as immutable independent twins.

The D-168 release chain is executable and has one explicit native trust root:
`C:\Windows`.  No cached PowerShell Core, activated environment, ambient
`python`, `Start-Process`, or project file executes before the exact inbox host
`C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe` receives the
reviewed `-EncodedCommand` bytes.  Those stage-0 bytes open and hash the release
receipt and native launcher before creating a `ScriptBlock`, and retain
deny-write/delete handles until the controller exits.  Stage 0 runs through
`C:\Windows\System32\cmd.exe /d /q /v:off` under an exact ten-entry environment
(nine fixed host values plus the authenticated envelope).  The native launcher
then constructs an exact twelve-entry controller environment.  Neither boundary
inherits `PYTHON*`, CLR profiling, PowerShell policy, module, or user-startup
variables.

After all tests pass, remove or relocate ignored QA residue, make one clean
controller commit, and recheck the exact committed tree.  Capture the final
commit plus SHA-256 values for the tracked native launcher, outer literal,
entrypoint, raw helper, stage-0 source, encoded payload and exact environment
policy.  First verify the registered stage-0 constants:

```powershell
& 'D:\Aenv\pro2\pro2\.venv\Scripts\python.exe' -I -S -B -X utf8 `
  'D:\Aenv\pro2\week8-recovery-controller-worktree\scripts\week8_recovery_stage0.py' --policy
```

Require `stage0_source_sha256=29183177378884857c03f37e8da1bd64f1643bca4e32ff56fb9899ef26b25f48`,
`stage0_encoded_sha256=401bfeb512de0233a1663365cda68f8f733cdf96682561a20f8ce6d1c48a5001`,
and `stage0_environment_policy_sha256=759d257d3842052eeb2f38bcea5ede02b9ddff617979f486ca6fa1c280a7af49`.
Create the external release directory once at
`D:\Aenv\pro2\.tmp\week8-d168-release-attempt-005`; it is outside both
worktrees and must be empty.  Then invoke the standalone renderer with literal,
reviewed values (never values dynamically parsed from Git or result evidence):

```powershell
& 'D:\Aenv\pro2\pro2\.venv\Scripts\python.exe' -I -S -B -X utf8 `
  'D:\Aenv\pro2\week8-recovery-controller-worktree\scripts\week8_recovery_release_receipt.py' `
  --output 'D:\Aenv\pro2\.tmp\week8-d168-release-attempt-005\release-receipt-v2.txt' `
  --controller-commit 'FINAL_CONTROLLER_COMMIT' `
  --native-launcher-sha256 'FINAL_NATIVE_LAUNCHER_SHA256' `
  --outer-sha256 'FINAL_OUTER_SHA256' `
  --entry-sha256 'FINAL_ENTRYPOINT_SHA256' `
  --helper-sha256 'FINAL_HELPER_SHA256' `
  --stage0-source-sha256 '29183177378884857c03f37e8da1bd64f1643bca4e32ff56fb9899ef26b25f48' `
  --stage0-encoded-sha256 '401bfeb512de0233a1663365cda68f8f733cdf96682561a20f8ce6d1c48a5001' `
  --stage0-environment-policy-sha256 '759d257d3842052eeb2f38bcea5ede02b9ddff617979f486ca6fa1c280a7af49'
```

The renderer uses OS-level exclusive creation and refuses an existing path.
Hash the completed receipt once and substitute that literal as
`FINAL_RECEIPT_SHA256`.  Generate one no-overwrite stage-0 record per command
with `week8_recovery_stage0.py`; for example, the first is:

```powershell
& 'D:\Aenv\pro2\pro2\.venv\Scripts\python.exe' -I -S -B -X utf8 `
  'D:\Aenv\pro2\week8-recovery-controller-worktree\scripts\week8_recovery_stage0.py' `
  --output 'D:\Aenv\pro2\.tmp\week8-d168-release-attempt-005\stage0-status-audit.txt' `
  --launcher-path 'D:\Aenv\pro2\week8-recovery-controller-worktree\scripts\week8_recovery_native_launcher.ps1' `
  --receipt-path 'D:\Aenv\pro2\.tmp\week8-d168-release-attempt-005\release-receipt-v2.txt' `
  --launcher-sha256 'FINAL_NATIVE_LAUNCHER_SHA256' `
  --receipt-sha256 'FINAL_RECEIPT_SHA256' `
  --command status
```

The audit record deliberately contains no executable command, payload, or
envelope.  Review that audit record and the renderer's terminal output, then
copy and run the complete terminal `stage0_cmd_payload=` value exactly.  Do not
parse or execute the audit file, persist the executable payload as a script,
reconstruct its encoded command, or route it through `subprocess.list2cmdline`.
Generate analogous immutable records for `adjudicate`, `recover`, `seal`,
`monitor`, `finalize`, `report`, and `figures`.  The candidate renderers are not
authority: stage 0 rehashes both inputs, the native launcher rechecks the
receipt and the registered retained startup inventory, and raw authority independently
revalidates the clean commits, exact complete environment, working directory,
Python prefixes, `pyvenv.cfg`, base runtime, venv Scripts, Git runtime, and
site-packages before admitting project code.  Raw authority schema 4 binds the
stage-0 aggregate through the controller, worker, inspector and every nested fit.
A wrong hash, linked/reparse
path, runtime residue, changed byte, extra tree entry, or nonzero exit refuses.

Run the four calls below in order.  Require `status` to report
`not_adjudicated`, `independent_inspection_performed=true`,
`mechanical_source_validation_performed=true`, `liveness_verdict=pass`, and
the exact counts `events=299`, `started=150`, `synced=149`,
`local_completed=150`, `durable_completed=149`, `untouched=111`,
`partial_files=11`, and `orphan_local_files=15` before continuing.  This first
call repeats the fixed old-source inspector and the full outcome-blind
inventory twice without publishing an adjudication record or changing any
production evidence.

```powershell
# Run the complete terminal stage0_cmd_payload= value emitted while creating
# stage0-status-audit.txt; inspect its output.  Then run, one at a time, the
# complete in-memory terminal payloads emitted for:
# stage0-adjudicate-audit.txt
# stage0-recover-audit.txt
# stage0-seal-audit.txt
```

`recover` is blocking.  Do
not monitor concurrently and keep the device on.  Expected accounting is
`executed=111`, `resumed=150`, `synced=261`, `total=261`.  If the lower epoch
completed but the controller response was lost, invoke only `seal` with the
same frozen launcher.  If epoch 002 is incomplete, `seal` refuses permanently.

Worker-terminal and postmortem publication share the persistent one-byte
`.week7-production.lease-transition.lock`.  Never delete, replace, truncate,
repair, or republish a partial invocation, claim, terminal, postmortem, or lock
file.  One-sided evidence is permanent stop evidence.  The Windows liveness
gate accepts only the exact stable base-interpreter/controller plus pinned venv
launcher pair; every other live or ambiguously inspectable Python/PyPy process
blocks.  This mechanism does not claim protection against a concurrent
same-user attacker able to replace directory entries or alter another process;
production is run quiescently under the cleared environment, captured sources,
retained handles, exact inventories, and fail-closed postconditions.

## Exact root inventory

All paths below are direct children of `D:\Aenv\pro2` except the two named
preparation children.  Every `project-evidence` path is an independent
same-volume copy, not an off-device backup.

Experiment 2A owns:

- `week8-execution-preparation-2026-09-01-attempt-001`, with children
  `exp2a-original` and `exp2a-project-evidence`;
- `week8-exp2a-2026-09-01-attempt-001-preflight`;
- `week8-exp2a-2026-09-01-attempt-001-output`;
- `week8-exp2a-2026-09-01-attempt-001-staging`;
- `week8-exp2a-2026-09-01-attempt-001-project-evidence`;
- `week8-exp2a-labels-2026-09-01-attempt-001` and
  `week8-exp2a-labels-2026-09-01-attempt-001-project-evidence`;
- `week8-exp2a-report-2026-09-01-attempt-001` and
  `week8-exp2a-report-2026-09-01-attempt-001-project-evidence`;
- `week8-exp2a-figures-2026-09-01-attempt-001` and the non-evidence cache
  `week8-exp2a-figures-2026-09-01-attempt-001-mpl-cache`;
- `week8-exp2a-monitor-2026-09-01-attempt-001` and
  `week8-exp2a-monitor-2026-09-01-attempt-001-project-evidence`;
- `week8-exp2a-recovery-2026-09-02-attempt-001` and
  `week8-exp2a-recovery-2026-09-02-attempt-001-project-evidence`;
- the non-evidence, required-empty runtime directories
  `week8-exp2a-recovery-runtime-2026-09-02-attempt-001` and
  `week8-exp2a-recovery-inspector-runtime-2026-09-02-attempt-001`, plus the
  reusable non-evidence downstream scratch directory
  `week8-downstream-runtime-2026-09-02-attempt-001`;
- the D-168 required-empty stage-0 runtime directory
  `week8-d168-stage0-runtime-attempt-001` and required-empty native startup
  directory `week8-d167-native-runtime-attempt-001`; and the external,
  no-overwrite release/audit records under ignored project-local
  `.tmp/week8-d168-release-attempt-005`, outside both worktrees.

The exclusion publication reopens the historical
`week7-first-sweep-label-2026-08-31-attempt-001` and its `-project-evidence`
peer.  It owns only `week8-exclusion-2026-09-01-attempt-001` and
`week8-exclusion-2026-09-01-attempt-001-project-evidence`.

The baseline wrapper owns:

- `week8-baseline-preparation-2026-09-01-attempt-001`, with children
  `original` and `project-evidence`;
- `week8-exp2b-2026-09-01-attempt-001-preflight`;
- `week8-exp2b-2026-09-01-attempt-001-output`;
- `week8-exp2b-2026-09-01-attempt-001-staging`;
- `week8-exp2b-2026-09-01-attempt-001-project-evidence`;
- `week8-monitor-exp2b-2026-09-01-attempt-001` and its `-project-evidence`
  peer;
- `week8-sweep-002-2026-09-01-attempt-001-preflight`;
- `week8-sweep-002-2026-09-01-attempt-001-output`;
- `week8-sweep-002-2026-09-01-attempt-001-staging`;
- `week8-sweep-002-2026-09-01-attempt-001-project-evidence`;
- `week8-monitor-sweep-002-2026-09-01-attempt-001` and its
  `-project-evidence` peer.

The shared control root remains `week7-production-control`, with lease name
`week7-production`; it is not a new scientific evidence root.

## Fixed command order

The original E2A prepare/preflight/launch sequence belongs to epoch 001 and
must never be repeated.  Keep the same receipt, launcher hash, and captured
controller release unchanged.  After recovery and sealing, resume E2A in this
exact order through the corresponding reviewed stage-0 records:

```powershell
# Run the complete in-memory terminal stage0_cmd_payload= value emitted for
# stage0-monitor-audit.txt.  Then, one at a time, run the corresponding terminal
# payloads for stage0-finalize-audit.txt, stage0-report-audit.txt, and
# stage0-figures-audit.txt.
```

The post-recovery monitor is run exactly once after terminal sealing and must
return `status: complete` from stable, independently copied evidence.  The old
advice permitting repeated live E2A monitors is withdrawn for this incident:
one monitor detected source motion between its two reads and exited nonzero
after publishing a valid earlier snapshot.

After finalization, mechanically inspect the report/figure manifests and
visually inspect all three PNGs.  Sign consistency remains unapplied and
`h2_verdict` remains null.  Only then open a fresh shell for exclusion/E2B.
The controller commit below is the same hard-coded final release commit; do
not derive it by parsing incident or result evidence.

```powershell
Set-Location 'D:\Aenv\pro2\week8-recovery-controller-worktree'
$RecoveryCommit = 'FINAL_CONTROLLER_COMMIT'
$env:TEMP = 'D:\Aenv\pro2\week8-downstream-runtime-2026-09-02-attempt-001'
$env:TMP = $env:TEMP
$env:TMPDIR = $env:TEMP
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
$env:CUDA_VISIBLE_DEVICES = '-1'
$env:HIP_VISIBLE_DEVICES = '-1'
$env:OMP_NUM_THREADS = '4'
$env:MKL_NUM_THREADS = '4'
$env:OPENBLAS_NUM_THREADS = '4'
$env:NUMEXPR_NUM_THREADS = '4'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONNOUSERSITE = '1'
$env:PYTHONSAFEPATH = '1'
Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue
$env:PYTHONPATH = 'D:\Aenv\pro2\week8-recovery-controller-worktree\src'
# Process-local Git controls for these later direct wrappers; no global config.
Get-ChildItem Env: | Where-Object { $_.Name -like 'GIT_*' } | ForEach-Object { Remove-Item -LiteralPath ('Env:' + $_.Name) }
$env:BU_RUNRECORD_GIT_EXECUTABLE = 'D:\Aenv\pro2\runtimes\git\mingw64\bin\git.exe'
$env:GIT_EXEC_PATH = 'D:\Aenv\pro2\runtimes\git\mingw64\bin'
$env:GIT_CONFIG_GLOBAL = 'NUL'
$env:GIT_CONFIG_SYSTEM = 'NUL'
$env:GIT_CONFIG_NOSYSTEM = '1'
$env:GIT_ATTR_NOSYSTEM = '1'
$env:GIT_NO_REPLACE_OBJECTS = '1'
$env:GIT_OPTIONAL_LOCKS = '0'
$env:GIT_TERMINAL_PROMPT = '0'
$env:GIT_CONFIG_COUNT = '5'
$env:GIT_CONFIG_KEY_0 = 'safe.directory'
$env:GIT_CONFIG_VALUE_0 = 'D:/Aenv/pro2/week8-recovery-controller-worktree'
$env:GIT_CONFIG_KEY_1 = 'core.fsmonitor'
$env:GIT_CONFIG_VALUE_1 = 'false'
$env:GIT_CONFIG_KEY_2 = 'core.untrackedCache'
$env:GIT_CONFIG_VALUE_2 = 'false'
$env:GIT_CONFIG_KEY_3 = 'core.hooksPath'
$env:GIT_CONFIG_VALUE_3 = 'NUL'
$env:GIT_CONFIG_KEY_4 = 'core.attributesFile'
$env:GIT_CONFIG_VALUE_4 = 'NUL'
```

Next publish the no-compute pre-reserve exclusion report; this command has no
route to reserve selection or fitting:

```powershell
& 'D:\Aenv\pro2\pro2\.venv\Scripts\python.exe' -s -P -m bu.experiments.week8_exclusion_production publish --expected-git-commit $RecoveryCommit
if ($LASTEXITCODE -ne 0) { throw "Pre-reserve exclusion publication refused" }
```

Finally run the baseline wrapper serially.  E2B must finish before sweep-002
preflight starts:

```powershell
& 'D:\Aenv\pro2\pro2\.venv\Scripts\python.exe' -s -P -m bu.experiments.week8_baseline_production prepare --expected-git-commit $RecoveryCommit
if ($LASTEXITCODE -ne 0) { throw "Baseline preparation refused" }
& 'D:\Aenv\pro2\pro2\.venv\Scripts\python.exe' -s -P -m bu.experiments.week8_baseline_production preflight-exp2b
if ($LASTEXITCODE -ne 0) { throw "E2B preflight refused" }
& 'D:\Aenv\pro2\pro2\.venv\Scripts\python.exe' -s -P -m bu.experiments.week8_baseline_production launch-exp2b
if ($LASTEXITCODE -ne 0) { throw "E2B launch refused or was interrupted; do not continue" }
& 'D:\Aenv\pro2\pro2\.venv\Scripts\python.exe' -s -P -m bu.experiments.week8_baseline_production monitor-exp2b
if ($LASTEXITCODE -ne 0) { throw "E2B terminal monitor refused" }
& 'D:\Aenv\pro2\pro2\.venv\Scripts\python.exe' -s -P -m bu.experiments.week8_baseline_production preflight-sweep-002
if ($LASTEXITCODE -ne 0) { throw "Sweep-002 preflight refused" }
& 'D:\Aenv\pro2\pro2\.venv\Scripts\python.exe' -s -P -m bu.experiments.week8_baseline_production launch-sweep-002
if ($LASTEXITCODE -ne 0) { throw "Sweep-002 launch refused or was interrupted; do not continue" }
& 'D:\Aenv\pro2\pro2\.venv\Scripts\python.exe' -s -P -m bu.experiments.week8_baseline_production monitor-sweep-002
if ($LASTEXITCODE -ne 0) { throw "Sweep-002 terminal monitor refused" }
```

Each baseline `launch-*` call is blocking.  Its matching `monitor-*` command
may run from a second terminal after the checkpoint exists and must run once
after completion.  Initialize every second terminal with the complete fresh
terminal block above and verify the same `$RecoveryCommit`.
No sweep group after 002 is enabled.

Closeout then reconciles physical-fit/model-training counts, hashes every
manifest and independent copy, updates the state/execution/delta ledgers,
preserves the student's Week 6/7/8 own-voice reminder, and commits the final
documentation.  External Sol review remains pending.

## Resource and stop policy

The original Week-8 workload was 389 physical fits and 1,081 member-model
trainings.  Epoch 001 completed 150/270, leaving **239 physical fits and 811
member-model trainings**: E2A 111/171, E2B 125/625 and sweep-002 3/15.  D-166
intentionally rechecks and locks the roughly 1-GB pinned dependency tree in
every new E2A fit child; the measured scan is about 75 seconds per child before
training.  A conservative end-to-end estimate is therefore **4--6 hours** of
CPU execution and verification, not the pre-D-166 1--1.5-hour estimate.  This
is operational, not a registered runtime claim.  The device must stay on
during active launch.  No
automatic retry is permitted after a preserved failed attempt.  D-161 is a
single record-gated recovery of an external parent termination, not a generic
retry rule.  Missing, divergent, source-incompatible or second-epoch partial
evidence remains visible and stops the relevant downstream finalizer; it never
triggers replacement training or a changed scientific rule.


## Non-evidence startup directory housekeeping (2026-09-08)

Before each stage, inspect both fixed startup runtime directories and require
them empty. September6 status left two DesktopCentral logs under the literal
stage0 child `%LOCALAPPDATA%/DesktopCentral_Agent`; their timestamps coincide
with that invocation, but the writing process was not observed. They were
preserved byte-identically on September8; the runtime parent was retained.
If residue recurs, first require the previous stage to have exited and preserve
its result. Inventory the residue without reading scientific outputs. Only
recognized non-evidence log residue may be moved into a fresh preservation
directory after checking exact paths, plain files and hashes; verify preserved
bytes and an empty unchanged runtime parent. Unknown contents require review.
Never replace the runtime parent, remove incident/lease/evidence artifacts,
disable the endpoint agent, relax the empty-directory check or change the
frozen startup environment. Housekeeping does not authorize retrying a failed
stage or another recovery. Preserve every attempt and follow the existing
nonzero-result stop rule.

## 2026-09-09 diagnostic release prerequisite (D-170)

Preserve attempts001–003. Attempt002 refused Git runtime drift, restored to the
original pin; attempt003 then refused an unresolved recovery check. The
new tested controller adds only bounded exit/stream/error fingerprints; these
are diagnostic evidence and never authorization to retry or consume recovery.
After a new clean commit and attempt004 receipt/status, inspect any refusal
fingerprints and resolve their cause. Every existing exact-count/liveness gate,
empty runtime check, native ceremony and one-use recovery rule still applies.

## 2026-09-20 D-171 relocation release prerequisite

All operator paths above now refer to the consolidated workspace. Original JSON
still records old logical paths; the fixed attestation resolves them without
editing bytes or claiming historical identities were reproduced. See
week8_relocation_provenance.md. Production child LOCALAPPDATA remains pinned to C:/Users/aladdin-alyanai/AppData/Local; only the diagnostic qa-environment-repair-002 used a project-local profile.
Preserve attempts001–004 and all failed/interrupted gates. Fresh complete QA,
governance and a clean controller commit are required before creating attempt005
V2 receipt/audits with the new exact release hashes. If an attempt path is already
occupied, preserve it and choose a fresh explicitly documented attempt; never
overwrite. Execute only renderer stdout retained in memory, never an audit file.
Do not run ordinary E2A launch or directly invoke the controller/worker/inspector.
Successful native status/counts/liveness must precede adjudication and the sole
recovery. Original lease restoration did not grant ownership. Do not regenerate
attestation to accept drift. No publication/push/deployment/external messages.
