# Week 8 production runbook

**Status:** pre-production.  This runbook records the fixed operational order;
it is not a launch permission, result, or substitute for immutable preflight
evidence.  Every path is below `D:/Aenv/pro/pro`, every fit uses the frozen CPU
4/4 route, and the GPU remains unused.

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
never authorizes recovery.

## Authorized command surfaces

Only these three modules may be invoked for Week 8 production:

- `bu.experiments.week8_exp2a_production`;
- `bu.experiments.week8_exclusion_production`;
- `bu.experiments.week8_baseline_production`.

Do not invoke `week8_exp2a_repair_launch`, `week8_launch`, `batch`, a runner,
or any other lower-level CLI directly.  Their parameters are intentionally
more general than this fixed attempt.  The wrappers above own every path,
count, timeout, storage floor, lease and phase transition.

From `D:\Aenv\pro\pro\pro2`, establish one clean commit and project-local
runtime temporary directory before the first command:

```powershell
Set-Location 'D:\Aenv\pro\pro\pro2'
$Week8Commit = (& git rev-parse HEAD).Trim()
$Week8Dirty = @(& git status --porcelain)
if ($Week8Dirty.Count -ne 0) { throw "Week 8 requires a clean tree" }
if ($Week8Commit -notmatch '^[0-9a-f]{40}$') { throw "Invalid commit" }
$env:TEMP = 'D:\Aenv\pro\pro\week8-runtime-temp-2026-09-01-attempt-001'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
```

Keep HEAD and the worktree unchanged for the whole sequence.
Commit-gated phases recheck `$Week8Commit`; argument-free monitor commands
validate immutable operational evidence rather than the current Git tree.  A
nonzero result stops progression.  Never rerun fitting after incomplete,
failed or partial history.  The same fixed launch wrapper may be re-entered
only when it validates one exact complete lower report and merely seals a
missing completion receipt while executing zero additional fits.

## Exact root inventory

All paths below are direct children of `D:\Aenv\pro\pro` except the two named
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
  `week8-exp2a-monitor-2026-09-01-attempt-001-project-evidence`.

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

First run the completed current-tree full suite and commit the implementation.
Then execute E2A in this exact order:

```powershell
& .\.venv\Scripts\python.exe -m bu.experiments.week8_exp2a_production prepare --expected-git-commit $Week8Commit
& .\.venv\Scripts\python.exe -m bu.experiments.week8_exp2a_production preflight --expected-git-commit $Week8Commit
& .\.venv\Scripts\python.exe -m bu.experiments.week8_exp2a_production launch --expected-git-commit $Week8Commit
& .\.venv\Scripts\python.exe -m bu.experiments.week8_exp2a_production monitor
& .\.venv\Scripts\python.exe -m bu.experiments.week8_exp2a_production finalize --expected-git-commit $Week8Commit
& .\.venv\Scripts\python.exe -m bu.experiments.week8_exp2a_production report --expected-git-commit $Week8Commit
Remove-Item Env:MPLCONFIGDIR -ErrorAction SilentlyContinue
& .\.venv\Scripts\python.exe -m bu.experiments.week8_exp2a_production figures --expected-git-commit $Week8Commit
```

The `launch` call is blocking.  While it is active, a second terminal may run
the following outcome-blind command after the launch checkpoint exists.  A
new terminal does not inherit the first terminal's location or environment,
so initialize it explicitly.  The monitor may be repeated for progress.  The
command in the fixed sequence above must then return `status: complete` after
launch and before finalization:

```powershell
Set-Location 'D:\Aenv\pro\pro\pro2'
$env:TEMP = 'D:\Aenv\pro\pro\week8-runtime-temp-2026-09-01-attempt-001'
$env:TMP = $env:TEMP
if (-not (Test-Path -LiteralPath $env:TEMP)) { throw "Runtime temp missing" }
& .\.venv\Scripts\python.exe -m bu.experiments.week8_exp2a_production monitor
```

After finalization, mechanically inspect the report/figure manifests and
visually inspect all three PNGs.  Sign consistency remains unapplied and
`h2_verdict` remains null.  Next publish the no-compute pre-reserve exclusion
report; this command has no route to reserve selection or fitting:

```powershell
& .\.venv\Scripts\python.exe -m bu.experiments.week8_exclusion_production publish --expected-git-commit $Week8Commit
```

Finally run the baseline wrapper serially.  E2B must finish before sweep-002
preflight starts:

```powershell
& .\.venv\Scripts\python.exe -m bu.experiments.week8_baseline_production prepare --expected-git-commit $Week8Commit
& .\.venv\Scripts\python.exe -m bu.experiments.week8_baseline_production preflight-exp2b
& .\.venv\Scripts\python.exe -m bu.experiments.week8_baseline_production launch-exp2b
& .\.venv\Scripts\python.exe -m bu.experiments.week8_baseline_production monitor-exp2b
& .\.venv\Scripts\python.exe -m bu.experiments.week8_baseline_production preflight-sweep-002
& .\.venv\Scripts\python.exe -m bu.experiments.week8_baseline_production launch-sweep-002
& .\.venv\Scripts\python.exe -m bu.experiments.week8_baseline_production monitor-sweep-002
```

Each baseline `launch-*` call is blocking.  Its matching `monitor-*` command
may run from a second terminal after the checkpoint exists and must run once
after completion.  Initialize every second terminal with the same
`Set-Location`, `TEMP`, `TMP` and existence check shown for the E2A monitor.
No sweep group after 002 is enabled.

Closeout then reconciles physical-fit/model-training counts, hashes every
manifest and independent copy, updates the state/execution/delta ledgers,
preserves the student's Week 6/7/8 own-voice reminder, and commits the final
documentation.  External Sol review remains pending.

## Resource and stop policy

The expected new workload is 389 physical fits and 1,081 member-model
trainings.  Prior throughput suggests roughly 1.5--2 hours of CPU execution,
plus source verification/finalization; this is an operational estimate, not a
registered runtime claim.  The device must stay on during active launch.  No
automatic retry is permitted after a preserved failed attempt.  Missing,
partial, divergent, unsynced or source-incompatible evidence remains visible
and stops the relevant downstream finalizer; it never triggers replacement
training or a changed scientific rule.
