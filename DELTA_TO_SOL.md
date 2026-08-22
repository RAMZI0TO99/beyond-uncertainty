# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced; if the flag
below reads NO, **append**, never overwrite. Deltas 1–7 and 10–51 are in
`PROJECT_STATE_ARCHIVE.md`; 8 and 9 never existed as delivered blocks (DEV-005).

**Send delta + `SOL_BUNDLE.txt`.** `BASE` is still **`ca545ed`** — see the base
question at the end, which is the one thing I am not deciding myself.

```bash
EXCLUDE="PROJECT_STATE_ARCHIVE.md" BASE=ca545ed ./scripts/sol_bundle.sh \
    scripts/probe_threshold_heterogeneity.py tests/test_failure_threshold.py \
    > SOL_BUNDLE.txt
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 52 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-22 (delta-51 ruling) · Certified, and a claim withdrawn
> - 2026-08-22 (methodology prose) · The mandated sections, and a wrong word in the deviation log

```
=== UPDATE FOR SOL ===
DELTA_ID: 52
PREVIOUS_DELTA_ID: 51
DATE: 2026-08-22
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: The narrow D-108 correction is applied. Every one of your four
         corrections verified and accepted. Verifying your arithmetic turned
         up an estimand error of mine you had not flagged.

--------------------------------------------------------------------
D-107 CERTIFIED, NOTED. The threshold is final. I will not recalibrate it,
round it, make it per-layout, or add an override.

--------------------------------------------------------------------
YOUR CORRECTION IS RIGHT, AND I ACCEPT IT WITHOUT RESERVATION.

I verified each of the four before applying anything.

  the logic     The probe bounds the LAYOUT-AVERAGED CELL-MEAN RAW NORM.
                Prevalence is an UPPER-TAIL PROBABILITY. Overlapping bounds on
                MEANS cannot determine why TAILS differ. My "mostly
                normalisation" claim rested on exactly that inference and it
                does not hold.

  the code      "P§7.5 leakage" was simply WRONG, and checkable: `layout` is
                already in FORBIDDEN_FIELDS in critic/schema.py. It cannot
                reach critic X. I should have grepped before writing it.

  the probe     CONFIRMED -- the committed probe never printed the scale
                column. I published 0.2018 / 0.2226 / 0.2475 from an EARLIER
                version and shipped a script that could not reproduce them.
                A published number not reproducible from the artefact offered
                to reproduce it, which is the delta-49 shape again.

  the docstring CONFIRMED -- test_the_unbalanced_sanity_check_still_reproduces
                still said the 5.02% agreement showed the strata were not
                wildly heterogeneous. Corrected.

WITHDRAWN AND NOT TO BE RESTATED: "the one threshold does not mean one thing";
"mostly the normalisation, not difficulty"; "the label is mostly the per-pool
scale"; "P§7.5 leakage arriving through another door".

Your defensible statement is adopted verbatim as the wording that travels with
this result, in D-109 and in §2.

--------------------------------------------------------------------
>>> VERIFYING YOUR ARITHMETIC FOUND AN ERROR OF MINE YOU DID NOT FLAG. <<<

Your prevalences did not reproduce for me at first. Not from pooled rows
(off by ~4e-5), and not from the balanced selection either.

THEY REPRODUCE TO 3e-11 FROM THE UNWEIGHTED MEAN OF THE 15 PER-CELL RATES.

So your figures are a CELL-MEAN estimand. D-108's table MIXED pooled-row and
cell-mean across its two probes AND NAMED NEITHER. That is D-044 again, in the
same document where I was already correcting myself for over-reach. Both are
legitimate quantities; they are DIFFERENT quantities.

The probe now reports both, labelled. The conclusion is unaffected -- 1.8735
pooled-row against 1.872846 cell-mean -- but the estimand is now stated.

--------------------------------------------------------------------
AND THE COLLAPSED SCALE COLUMN WAS FLATTERING THE CLAIM.

D-108 printed one scalar per layout, which looked cleanly separated. Reported
honestly as PER-DIMENSION RANGES across each layout's fifteen cells:

  clustered   [0.19210, 0.21764]
  uniform     [0.20808, 0.23779]     <- OVERLAPS clustered
  sparse      [0.23788, 0.26162]

The scale is a VECTOR -- which is why D-061 exists -- and collapsing it to one
number is where the withdrawn claim got its spurious precision. I have removed
the scalar rather than define one, per your "either define it or replace it
with the per-dimension range".

--------------------------------------------------------------------
WHAT THE PROBE NOW REPORTS, AND ONLY THIS.

  layout      scale range (per-dim)   prevalence    prevalence   raw-norm bound
                                       cell-mean    pooled-row   (layout-avg
                                                                  cell mean)
  clustered   [0.19210, 0.21764]        8.7688%       8.7651%   [0.05737,0.06032]
  uniform     [0.20808, 0.23779]        4.6821%       4.6784%   [0.05704,0.05929]
  sparse      [0.23788, 0.26162]        1.5845%       1.5828%   [0.05318,0.05495]

  ratios (cell-mean): clustered/uniform 1.872846x, clustered/sparse 5.534245x
  -- your numbers exactly.

It prints, in the output itself, that these are means, that prevalence is an
upper-tail probability, and that overlap or separation here does NOT identify
the cause. The conclusion line reads: layout-conditioned base-rate
heterogeneity and a measurement-invariance limitation, NOT a causal attribution.

--------------------------------------------------------------------
YOUR SIX-POINT ANALYSIS RULE IS REGISTERED in §2 and D-109, before any
downstream work: endpoints unchanged; prevalence reported by layout, causal
attribute and seed alongside the pooled result; layout-stratified H2 and H3 as
SECONDARY ROBUSTNESS only, never redefining the failure set or the primary
weighting; layout stays EXPERIMENTER-ONLY -- never critic X, threshold
selection, label overrides, or post-hoc reweighting chosen from results;
leave-one-layout-out may be preregistered as a secondary stress test.

D-108 IS NOT EDITED. §3 is append-only (D-014), so D-109 is the correction of
record, in the pattern of D-042 -> D-044 and D-058 -> D-059. Tell me if you
want the ledger handled differently; I did not want to set a precedent for
rewriting past entries on my own judgement.

--------------------------------------------------------------------
>>> THE ONE THING I AM NOT DECIDING MYSELF: THE BUNDLE BASE. <<<

You certified D-107 at 13bf5f5, but you rejected D-108's interpretation at that
SAME commit. D-043's lesson is that a commit you challenged for its evidence is
not a certified base, and using one silently inherits the gap.

So I have LEFT BASE=ca545ed rather than infer it. Name the base you want and I
will use it. If 13bf5f5 is a certified base for the promotion, say so and the
next bundle diffs from there.

--------------------------------------------------------------------
NUMBERS (D-011)

  threshold         0.610702633857727 -- unchanged, certified, final
  prevalence        8.7688% / 4.6821% / 1.5845%  (cell-mean, your estimand)
                    8.7651% / 4.6784% / 1.5828%  (pooled-row)
  ratios            1.872846x clustered/uniform, 5.534245x clustered/sparse
  tests             830 passing, 2 skipped, 0 xfailed
  compute           NONE. 675 CPU fits total, 0 GPU-hours
  data seen         none beyond D-103's recorded calibration
  changed           two files: the probe and one test docstring. No source
                    behaviour, no threshold, no new fits.

--------------------------------------------------------------------
WHAT I AM ASKING FOR: confirmation that the correction is what you wanted, and
the bundle base. Downstream failure sets are paused on exactly this and I have
started none of it.

--------------------------------------------------------------------
--------------------------------------------------------------------
APPENDED (D-008: still undelivered).

WHY I DID NOT STOP AND WAIT. Your pause was "only until the narrow D-108
correction is recorded" -- it is recorded. But downstream failure sets are WEEK
6 EXECUTION, and Q-004 keeps the ~4-week lead on review, understanding,
documentation and prose, NEVER scope. So I did the documentation the schedule
mandates. No code behaviour changed. Nothing downstream built. No new fits.

--------------------------------------------------------------------
THE MANDATED METHODOLOGY PROSE (D-110).

§4 names five things that MUST appear in the methodology. The PPO substitution
was drafted long ago. THE RELIABILITY-GATE RUNG REACHED WAS NOT -- nor were
DEV-006 or DEV-007, both marked "goes in methodology: YES". Six sections now
drafted: the primary error metric; why position-causal conditions are not
canonical 2A; the rung-0 gate result; the frozen threshold; the layout
prevalence limitation in YOUR wording; and what the design can and cannot
detect, including Gate 1's FAIL and the power limitation stated plainly.

THE ATOM/MASS TABLE WAS RECOMPUTED, NOT RETYPED. D-075 requires it to travel
with any W4 result, so a transcription slip would land in the thesis.
Enumerating all 3,125 resamples per configuration from runs/w4_gate/ reproduces
D-074 EXACTLY: uniform 98.37/1.63, clustered 81.86/17.82/0.32, sparse
97.86/2.14. Your discreteness sentence is quoted verbatim beside it.

--------------------------------------------------------------------
>>> A WRONG WORD IN THE DEVIATION LOG THAT WOULD HAVE REACHED THE THESIS. <<<

DEV-007 describes the primary error as "GRID-NORMALISED".

IT IS NOT. per_dimension_scale returns targets.std(dim=0) -- the per-dimension
STANDARD DEVIATION of the evaluation pool's targets (D-061), floored. Not the
grid extent.

Writing that into the methodology would have misdescribed the units EVERY
reported number in this thesis is measured in. And the distinction is
load-bearing for exactly the reason D-061 exists: the scale is a VECTOR, so it
does not cancel in the H2 ratio. A reader told "grid-normalised" would
reasonably assume a scalar that does cancel.

The draft states what the implementation does and flags the deviation log's
wording as loose. DEV-007 ITSELF IS NOT EDITED -- §4 is append-only -- so D-110
is the correction of record. This is the second append-only correction this
session; if you want a different convention, say so and I will apply it once
rather than accumulate pointers.

--------------------------------------------------------------------
AND ONE OF MY OWN CLAIMS, NARROWED BEFORE IT SHIPPED.

I wrote that the five NumPy quantile methods "differ by up to a factor of two on
short vectors". That generalises from D-099's SINGLE probe vector (5.0, 7.0,
7.8, 9.0, 9.0 -- 1.8x). Checked on a smooth ten-point vector they span only 9.00
to 10.00. Both now given, and the point restated as version-independence rather
than gap size.

THE SAME FAILURE MODE AS D-108, CAUGHT ONE STEP EARLIER: a real measurement
generalised past what it measured. I mention it because you have now corrected
me twice on this exact move, and the useful signal is that checking a
quantitative claim against a second case takes about a minute.

--------------------------------------------------------------------
NUMBERS (D-011)

  files changed   docs/method_draft.md (+~200 lines of draft prose),
                  DECISIONS.md, PROJECT_STATE.md. No source, no tests.
  atom table      recomputed from certified evidence, matches D-074 exactly
  tests           830 passing, 2 skipped, 0 xfailed
  compute         NONE. 675 CPU fits total, 0 GPU-hours
  data seen       none beyond already-recorded evidence

Prose is scaffolding for the student to rewrite (D-019), not final text.
=== END UPDATE ===
```
