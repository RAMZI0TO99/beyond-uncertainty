# Experiment 1 — authorized Week-7 coefficient report

2026-08-31, Sol2. D-154 amendment; external Sol review pending. All five
configurations meet the unchanged negative-disagreement reading rule. This is
the amended operational conjunction, **not full H1 confirmation**, an originally
preregistered global test, or a simultaneous confidence claim.

## Evidence and method

The report uses the existing 150 baseline fits: 30 configuration-conditions in
five comparison groups, five seeds (1000–1004), six data sizes
(100, 250, 500, 1000, 2500, 5000). Each original fit contains five ensemble
members; no fit was retrained. The 30 multi-role fits are counted once.
Within each configuration the point statistic is Spearman rho of the equal-seed
mean curve. Each interval enumerates all 3,125 ordered paired seed-block
resamples and uses linear percentile quantiles. Configurations are not pooled.
Error uses the same statistic as a diagnostic, not an additional H1 criterion.

| Configuration | Disagreement rho | Pointwise 95% seed-bootstrap interval | Criterion |
|---|---:|---|---|
| Shape / uniform | -0.942857 | [-0.942857, -0.828571] | Met |
| Shape / sparse | -0.828571 | [-1.000000, -0.828571] | Met |
| Colour / uniform | -0.942857 | [-1.000000, -0.828571] | Met |
| Colour / clustered | -0.828571 | [-0.942857, -0.828571] | Met |
| Shape / clustered | -0.942857 | [-1.000000, -0.828571] | Met |

For **diagnostic error**, all five point coefficients are -1.000000, with
percentile intervals [-1.000000, -1.000000]. These zero-width intervals reflect
the discrete rank statistic and bootstrap support, **not zero sampling
uncertainty**. There are no undefined coefficients/resamples in any of the ten
metric results. Exact enumeration is not a claim of exact frequentist coverage.

## Bootstrap support — must accompany the intervals

Coefficients below are rounded to six decimal places only for display. Each
entry is `rho: count (mass)` out of 3,125 equally weighted ordered resamples;
full floating-point values are retained in the immutable JSON report.

| Configuration | Disagreement support |
|---|---|
| Shape / uniform | -0.942857: 2573 (0.82336); -0.828571: 552 (0.17664) |
| Shape / sparse | -1.000000: 80 (0.02560); -0.942857: 1002 (0.32064); -0.828571: 2043 (0.65376) |
| Colour / uniform | -1.000000: 271 (0.08672); -0.942857: 2718 (0.86976); -0.828571: 136 (0.04352) |
| Colour / clustered | -0.942857: 1362 (0.43584); -0.828571: 1753 (0.56096); -0.771429: 10 (0.00320) |
| Shape / clustered | -1.000000: 385 (0.12320); -0.942857: 1912 (0.61184); -0.828571: 778 (0.24896); -0.771429: 50 (0.01600) |

Error support is -1.000000: 3125 (1.00000) for shape/uniform, shape/sparse,
colour/clustered and shape/clustered. Colour/uniform has -1.000000: 3124
(0.99968) and -0.942857: 1 (0.00032). Undefined count/mass is 0/0 for all ten.

## Interpretation and unfinished obligations

The evidence supports the specified negative trend across dataset sizes in
each configuration. The plotted disagreement curves are not uniformly
monotonic, particularly at small data sizes; a negative rank trend does not
assert monotonicity of every seed curve. No added seeds, smoothing, subset
selection, alternative estimator, or repair-width adjustment follows this result.

The all-five conjunction and reporting timing were fixed under explicit owner
authority **after collection and partial prior exposure**. Development and
calibration evidence, the separate smoke label, and two D-150 raw per-fit
summaries were already known. No additional result was opened to choose D-154.
Do not describe the amendment as fully blinded pre-data registration.

These baselines do not establish realizability or repair-derived class labels.
All 30 Experiment-1 conditions still lack completed paired-repair labels in
this report. Observed N0/N1/min(N0,N1), ambiguous/undiagnosed counts and exclusion
rates are **not determined here**, rather than assigned from intended class or
silently treated as zero. No acceptance test was run by this analysis. Full H1
interpretation and Gate 2 remain Week-10 obligations informed by scheduled
repair validation. Week 10 reuses this report; regeneration is verification,
not an independent statistical look.

## Exact provenance and files

- Fit execution commit: `f036fe02c4c9fe2fb756d65480186c8e10f7d48e`.
- Clean tested analysis commit: `ee02542f814ae977fa15036393ca6ea2829aa4ee`.
- Amendment SHA256: `4a856c65b4a0ae2f7b609d6dbf88f97e0489931498c26c165bd38b769a1e1707`.
- Report SHA256: `82b0277af9be843e46ff7d5b53020e23f5eab4e7c68101bffe457b8a2e37f44b`.
- Evidence root: `D:/Aenv/pro/pro/week7-analysis-2026-08-31-attempt-001`.
- Independent copy: `D:/Aenv/pro/pro/week7-analysis-2026-08-31-attempt-001-project-evidence`.
- Complete artifact-tree content digest: `31ec89a4cd8de4e6842d3f80d2f6d2c8c3c55c424479618b2793271ad4c04d58`.
- Copy/object-identity attestation: `b71c8197f5f6a16d34627469f101d38cd8748d22ef2811e91c96a9d4090d5864`.

Both copies are separate files on the same D volume, **not an off-device backup**.
The seven-file evidence supplement is
`D:/Aenv/pro/pro/week7-analysis-2026-08-31-attempt-001-evidence.zip`, SHA256
`800b9a92698817058eeb846e358bb8d2dfd3e8910c1b8d543cbcb31b99ebeef9`.
Every ZIP member matches its immutable artifact bytes. It does not contain or
replace the 150 original fit directories needed for an independent source audit.
`analysis_start.json` records pinned environment and explicit source paths;
`analysis_completion.json` records completion and artifact hashes. Existing
source/copy attestations match their pre-analysis values for all 150 fits.
Elapsed time including the finalization correction was 184.454924 seconds;
new fits, new labels and GPU use were all zero.

The figure manifest binds every plotted scalar and PNG to its sources. All 150
figure rows match the report's identities, digests and values exactly. Both
PNGs were visually inspected: five separate panels, complete seed legends,
readable axes/captions, no clipping or pooled curve.

## Preserved finalization failure and correction

The first orchestration command wrote/replay-verified the report and produced
both figures, then exited 1: it incorrectly compared a copy-evidence attestation
(including file object identities) with a content-only tree digest. These are
different hash payloads. Its immutable start field `source_tree_digests` actually
contains the former; that original record was not rewritten.

Finalization rederived the **same kind** of attestation for all 150 source/copy
pairs and matched every pre-analysis value. No changed source was found. The
report/figures were not regenerated or overwritten; no scientific code, rule
or result changed. `analysis_finalization_correction.json` preserves the error,
cause and field-meaning correction. Copies were then verified independently.
Do not erase this failed command from the audit history or report it as a
scientific-data mutation.

## Replay, not re-analysis

The artifact-only reader requires the report SHA256 above from this separately
retained record. It opens no fit sources and recomputes no rank correlations or
bootstrap samples. It checks the fixed report's bytes and internal consistency,
not the correctness of an entirely fabricated report plus a substituted digest.
Independent source/computation auditing is a separate verification operation.

```python
from pathlib import Path
from bu.experiments.experiment_1_report import replay_experiment_1_report

report = replay_experiment_1_report(
    Path("D:/Aenv/pro/pro/week7-analysis-2026-08-31-attempt-001/experiment_1_report.json"),
    expected_sha256="82b0277af9be843e46ff7d5b53020e23f5eab4e7c68101bffe457b8a2e37f44b",
)
```

## 2026-09-01 additive label-status pointer

This immutable D156 analysis was not rerun or edited after labels. Its historical
statement that labels were then pending remains true of this report's creation.
All30paired-repair labels are now independently verified:N0=29,N1=0,
ambiguous0,undiagnosed1,min0. The complete distinct seed-t method/effects/CIs
are in `week7_repair_label_results.md`; do not add those later seeds to the
five-seed trend bootstrap or treat this pointer as a second statistical look.
