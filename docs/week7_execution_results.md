# Week 7 execution results — Sol2

Status: **Week7 computational work complete and independently accounted**.
Student authorship and external Sol review are separate requirements, not
supplied by machine execution.

## Work completed and remaining

| Week7 workload | New physical fits | Member models | Status |
| --- | ---: | ---: | --- |
| E1:90 higher-seed baseline ensembles plus384 single-model repairs | 474 | 834 | Complete; all30labels independently verified |
| E2A:95 new baseline ensembles, plus5 immutable historical reuses | 95 | 475 | Complete; all95fits/copies and5reuses independently reverified |
| First sweep:3 anchored baseline ensembles | 3 | 15 | Complete and verified |
| First sweep:6 paired single-model repairs | 6 | 6 | Complete; undiagnosed label independently verified |
| Exact new Week7 inventory | 578 | 1330 | Complete;0other attempts and0unknown attempts |

All150historical E1 baselines remain preserved;102are required by the label
inventory. Historical training is not counted again. Five E2A baseline fits
are reused from the original smoke batch, not replacement-trained. The188
development timing models are also separate from the new research count.

## What the results say

E1 has30completed labels: **29 estimation-error labels, no hypothesis-class
labels, no ambiguous labels and1undiagnosed condition**. None is missing or
blocked. The E1-only minimum class count is0, not a whole-study adequacy result.
The six shape/uniform conditions use20seeds; the other24use3seeds. All60repair
arm intervals formed. These unequal-precision tests are not pooled.

The undiagnosed E1 condition is shape/sparse,N5000. Its data repair has a51.9%
point reduction, but the95%seed-t interval crosses zero. Model repair has a6.4%
point reduction and also fails the interval requirement. The fixed rule
requires both the interval criterion and a strict reduction greater than20%.
No extra seeds, increased budget or replacement followed this result.

The first sweep unit,0184fbfcd8b9, is also retained as **undiagnosed**. Its data
repair reaches20.1%point reduction but fails the interval requirement; its
model repair has a negative interval but reaches only7.7%reduction. This is a
valid completed outcome, not a failed training run. It stays separate from E1.

The existing D156 trend analysis and figures are unchanged: all5configuration
criteria were met under the documented amendment. This is not full H1
confirmation or a simultaneous/global test. Week10 interprets the same report
with repair evidence; there was no second correlation/bootstrap look. H2/H3,
E2A labels, remaining sweep groups, reserves and Week8 exclusion rates were
not analyzed or activated here.

Detailed evidence:

- `week7_repair_label_results.md`: all30units,60arm effects,95%seed-t intervals,
  relative reductions, seed counts, observed labels and label-file hashes.
- `week7_experiment_1_results.md`: unchanged D156 coefficients/figures and the
  required discrete-bootstrap support/mass tables. Zero-width intervals are
  not zero sampling uncertainty.
- `week7_sol_closeout.md`: mandatory delta70companion with source pins,
  complete NUMBERS, first-sweep estimates, failure history and review limits.

Three old model-repair explanation strings incorrectly say “includes zero”
for wholly positive intervals. The actual estimates, intervals, false
acceptance decisions and labels are correct. The detailed reports correct the
wording to “not wholly below zero”; immutable evidence is unchanged. A future
code wording change needs explicit reader/version compatibility, not silent
rewriting of source-rederived labels.

## Verification and source identity

Full guarded-source QA: **4085passed,8expectedskips,51passedsubtests**, no
failures/errors,4137.69seconds. XML SHA256:
`f892e4702f0279df88f8c9e9c29e9c564121909da3f6fd58c508b9d754d981c6`.
The4144XMLrecords include the51subtests. Skips are3CUDA-dependent checks,
4Windows symlink-permission checks and1inapplicable identity-field check.
They are not claims of tested support for those unavailable paths.

The earlier failed runs are preserved. One Windows long-path test was confirmed
and passed unchanged with a shorter path. The first full guard suite used
scratch outside the actual repository: all69failures/setup errors were the
intended containment refusal. A corrective probe also omitted its parent
directory. After fixing test placement, the complete unchanged-source rerun
above passed. No guard, test, skip or assertion was weakened to obtain green.
Overlapping focused/full counts must not be summed.

E1 and both sweep launches, label CREATE and independent VERIFY ran on actual
clean `1f302d1a05425827229e6ba3f41010a2b003c6f1`. The original checkout stayed
frozen until the source-bound readers finished. Only then was it advanced to
full-QA-tested `4782c90ce0e66fb46768f08d5080a27590a51a48` for E2A. The new
storage guard is prospective: no retrospective protection, disk reservation,
runtime guarantee, active-child termination or successful per-child guard
receipt is claimed. Its fixed8GiBfloor is checked before each new child.

E1 independently verified576source/copy pairs, with0reader-executed fits.
Manifest SHA256:
`f5a186b930c202355343c88fec4a4199c5cc6391a1a05a304ea76d990e7aef92`;
independent VERIFY receipt:
`cedcaa3a08ff329d55096519095747aa23b29b48573140cc88486aa50cffcb10`.
First-sweep verification receipt:
`0192c18d291e65944a518f68195d3b189e2252db0b8e8c4e7b5054db9a71555f`.
Its initial reporting failure and verify-only recovery are retained; no label
was rebuilt, overwritten or replacement-trained.

## Actual compute accounting

CPU only; GPU use0. Production used fixed4intra-op/4inter-op threads and a
3600second per-attempt timeout. Final accounting rechecked all578canonical
attempt envelopes/receipts and their copies:578new fits/1330models,0other
attempt seconds and0unknown attempts. Successful supervised-attempt wall time
sums12094.442840200325s:E19370.183577700227;E2A1934.6859239999903;
sweep baseline77.88229890004732;sweep repairs711.6910396000603.
Persisted parent intervals:E2A2000.487148s;sweep baseline107.869737s.
E1/sweep-repair parent intervals were not persisted and remain null.

Accounting report SHA `3856368d16ad2fa994b5498cf24cd758d157c6ca99d76cd8ed47bf74caaa495f`;
E2A report `a4e61a274c07d3653cbd05073669cc0b94bea57169237def5de397422cfa9f34`;
independent readback pair `4c4ae415b806140c437d79c0a90768206abc81058a93c04842675cf439551192`.
Readback verified all95fits/copies,5reuses and retained old-source001 as
unlaunched/metadata-only. No preflight was rewritten or reissued.

Attempt wall time is not CPU-core-hours,GPU-hours or pure training time.
Copies/reuse/label readers/QA are not counted as new computation.

The original development timing is retained in `week7_cpu_timing.md`:17repair
cases plus6baseline cases,188models. Its E1 collection/training projections
excluded scoring/evidence/copy/process overhead and were not confidence bounds
or end-to-end runtime promises. No new model-cost estimate replaces actual
attempt receipts at closeout.

## What still needs the student and reviewer

See `week7_student_checklist.md`. The student's own approximately400word Week6
explanation and500word Week7results section are still required. The updated
484word `week7_results_closeout_draft.md` is explicitly an AI drafting aid,
not the student's completed deliverable. Existing earlier drafts are preserved.

Sol2 is the implementation role working with external Sol, not a replacement
certifier. All undelivered deltas64–70 plus the mandatory closeout companion
must travel with the final verified transfer/evidence index. Generating files
does not mark them delivered or certified. The power gate remains FAIL, CPU
timing does not resolve the GPU-hour gate, and no scope expansion follows.

All copies and packets are project-local on the same D volume, not off-device
backups. A metadata packet is not self-contained scientific replay: raw
original/copy/exported fit trees remain at their explicit recorded paths.
The reconstructed local-history supplement is not certified real-project
ancestry or `SOL_BUNDLE.txt`. Do not rewrite original provenance to emulate a
missing execution environment.
