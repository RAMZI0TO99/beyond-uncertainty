# Week 7 CPU timing — completed development measurement

Measured 2026-08-31 from clean implementation revision
`bc89a83783d68bf6cfa45868422dc37d9a718502`, after the 4,037-pass full suite.
Both benchmark parents exited successfully and both strict timing readers
rederived the inventories, repetition requirements, provenance and projections.
No research fit, repair label, failure mask or hypothesis test was produced.

## Evidence and fixed procedure

| Artifact, relative to `pro2` | SHA256 |
|---|---|
| `.tmp/week7-repair-timing-2026-08-31-attempt-001/timing.json` | `5ea1a229b711be4f98f095498f28edb9414e1cb53df3596288f15d3e919ccff0` |
| `.tmp/week7-baseline-timing-2026-08-31-attempt-001/timing.json` | `798778be36fbe5bd43a4e0960e23030914ab011ad5275b5c516241af5527c409` |

Each exact architecture/size case used development seed 0 for one warm-up and
seeds 1, 2, 3 for three measured repetitions, with the registered training
settings unshortened. Every case ran in a fresh process on the fixed CPU route:
four intra-op/four inter-op threads, float32, exact pinned dependencies. The
case timeout was 1,800 seconds. There were no failed or retried cases.

Seventeen repair cases trained 68 single models. Six separate baseline cases
trained 24 five-member ensembles, or 120 member models. Total development
training: **188 models**, not extra confirmatory seeds or research replications.
Case selection was deterministic and source-only; it was not changed from
inspection of results. All output/cache/temp paths stayed inside the project.

## Exact E1 workload projection

These are two descriptive extrapolations, **not endpoints of a confidence
interval or guaranteed completion window**. Each group uses the median or the
maximum of its three measured repetition durations, multiplied by the exact
registered count. Baseline duration is measured for an entire five-model
ensemble and is multiplied by ensemble jobs, never by member count again.

| Remaining E1 work | Physical fits | Member models | Median-summary CPU hours | Maximum-summary CPU hours |
|---|---:|---:|---:|---:|
| Repairs | 384 | 384 | 0.7715762711109386 | 1.67736429155649 |
| Higher-seed baselines | 90 | 450 | 0.3819698708335636 | 0.4429448679169582 |
| Total new E1 work | 474 | 834 | 1.1535461419445023 | 2.120309159473448 |

The separately reported **gross all-repairs inventory** contains 2,310 models:
8.878493981966717 median-summary hours or 15.481608381254564 maximum-summary
hours. It includes later scheduled repairs and is **not remaining Week-7 work,
the whole-project cost, or an authorization to execute those later jobs**.

The summed collection/training durations, including warm-ups, were
1,184.7957106001559 seconds for repair timing and 373.7507878000033 seconds for
baseline timing. These sums exclude parent/process overhead and are not the
benchmarks' full start-to-finish wall times.

## Limitations and production boundary

Measured components are pool collection and actual training, including bootstrap
and early stopping. Prediction, symbolic anchors, evidence serialization,
per-epoch logging, process launch, revalidation, copy and recovery costs are
not priced. Host load and thermal effects are uncontrolled. Architecturally
identical conditions can stop at different epochs. Empirical maxima are not
worst-case bounds; no GPU-hour gate is adjudicated by local CPU wall hours.

The E1 estimate does not price the 95 new E2A baselines or the first sweep's
three baselines and full anchored-repair overhead. Actual launch receipts will
provide their observed throughput. Do not substitute these cases for unmeasured
architectures or call the E1 total a complete Week-7 duration estimate.

Production remains the exact D-157 inventory: 578 new physical fits /1,330 member
models, with all declared historical reuse preserved. Before launch, set the
operational single-fit timeout to **3,600 seconds** and the storage floor to
**8 GiB (8,589,934,592 bytes)**; neither changes training settings or scientific
stopping rules. Fresh preflights must recheck clean Git, independent timing
pins, historical sources, storage, copy integrity, and the common lease.
Free space after timing verification was 20,058,066,944 bytes, not a guarantee
of future free space. No source or timing artifact may be overwritten on failure.
