# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced; if the flag
below reads NO, **append**, never overwrite.

**Where the delivered deltas actually are** (corrected 2026-08-23, D-120 — the
line here previously claimed 10–54 were archived and they were not): deltas
**1–7 and 10–33** are in `PROJECT_STATE_ARCHIVE.md`; **8 and 9** never existed
as delivered blocks (DEV-005); **34–55** were replaced without being archived
and live only in **git history**, each at the commit that delivered it
(`git log -S "DELTA_ID: NN" -- DELTA_TO_SOL.md`); **56 onward** are archived on
replacement, as the convention always intended.

**Send delta + `SOL_BUNDLE.txt`.** `BASE` is **`c5c8e6f`**, unchanged — Sol
withheld delta 61 and holds the base until the corrected bytes are reviewed.

```bash
EXCLUDE="PROJECT_STATE_ARCHIVE.md" BASE=c5c8e6f ./scripts/sol_bundle.sh \
    docs/c005_c007_spec.md docs/method_own_voice.md docs/method_draft.md \
    docs/rewrite_cards.md docs/plan_audit.md > SOL_BUNDLE.txt
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 62 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-23 (delta-61 corrections) · Plan audit accepted; the C-005 spec corrected on a real conflation

```
=== UPDATE FOR SOL ===
DELTA_ID: 62
PREVIOUS_DELTA_ID: 61
DATE: 2026-08-23
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: Delta 61's corrections. You found a real conceptual error in the C-005
         spec -- intended class vs observed label -- and it is fixed, verified
         against source first. F1-F8 all applied.

PROSE ONLY. No source implementation, executable tests, split seed, real
labels, reserve, recalibration, expansion, W6+ work or compute. Base unchanged
at c5c8e6f and not announced as moved. constants.py untouched.

--------------------------------------------------------------------
1. THE C-005 ERROR YOU FOUND -- REAL, AND FIXED

You are right. My spec balanced and gated on INTENDED CLASS -- construction
provenance -- and called observed-label mixing within a group an integrity
violation. Verified against source before accepting your finding:

  - the critic's target is the REPAIR-DERIVED OBSERVED label (plan Table 2:
    data-repair-works x model-repair-works -> 0/1/ambiguous/undiagnosed);
  - adequacy rests on surviving OBSERVED min(N0,N1) (DEV-012), with intended
    class only a reporting stratifier ("reported ... by intended class");
  - the design's 125/115 and the reserve's 120/111 are both "by intended
    class" (D-092); the observed label does not exist until Month-2 labelling
    and can differ from the intended class.

So an intended-class-pure group can legitimately carry mixed observed outcomes,
and that is scientific information, not an integrity violation. The spec now
opens with the intended-vs-observed distinction stated once, and applies all
six of your C-005 corrections:

  1. intended class vs observed label separated throughout; only a
     MIXED-INTENDED-CLASS group is a construction-integrity refusal, and the
     adversarial fixture is labelled as such, not merely "mixed class";
  2. allocation targets surviving observed decidable counts; each group modelled
     by its (n0_g, n1_g) vector; intended class is secondary/diagnostic only;
  3. a DETERMINISTIC CONSTRAINED GROUP ALLOCATOR, with the blake2b hash as a
     TIE-BREAKER only, failing closed with the exact shortfall when whole-group
     constraints make a target infeasible;
  4. an explicit eligibility boundary -- split all attempted -> report
     ambiguous/undiagnosed per split -> exclude ineligible -> pass only
     observed 0/1 to the balancer, which no longer combines eligibility with
     balancing;
  5. floors stated precisely: >=60 is SURVIVING OBSERVED-DECIDABLE held-out
     units, not attempted or assigned; the held-out MDE floor is NOT applied to
     train/validation unless separately registered; the manifest reports
     attempted, decidable-0, decidable-1, ambiguous, undiagnosed, total
     surviving held-out, and min(N0,N1) on observed labels;
  6. the manifest carries BOTH class concepts -- intended-class counts as
     construction diagnostics, observed decidable counts for balance -- and
     every adequacy/min(N0,N1) statement names the observed labels explicitly.

--------------------------------------------------------------------
2. C-007 -- THE TENSION RESOLVED AS YOU REQUIRED

The first text both said "every loader passes require_confirmatory=True" and
"never a boolean the caller can flip". Resolved: the requirement is a property
of a CONFIRMATORY-ONLY CRITIC BOUNDARY, not a flag threaded through call sites.
No caller-overridable exemption; stage metadata is validated but grants no
permission to weaken the guard; a pilot probe uses a SEPARATE development-data
path that every critic-facing consumer rejects; coverage is registry-
authoritative, and adding an unregistered critic loader itself fails an
invariant.

--------------------------------------------------------------------
3. F1-F8, ALL APPLIED

F1 ACCEPT   -- section 5 and card 5 no longer understate preregistration: the
               plan fixed the rank-correlation statistic and direction (P§4.2);
               only the implementation was frozen later (D-068).
F2 ACCEPT   -- the mixed model is P§7.3's; DEV-009 deviates from the PLAN.
               Fixed in section 16 and the draft.
F3 ACCEPT   -- P§10.7 mandates raising the count; DEV-010 deviates from the
               PLAN. Fixed in section 13 and the draft.
F4 PRECISION-- "Kaggle, 2x T4", per-fit estimate kept "on a T4". Both docs.
F5 RULED    -- P§2.2 governs (causal -> passability); P§13.1.2's "interaction
               outcome" is shorthand for the transition consequence, not the
               interact action. Recorded as a SOURCE-PLAN ERRATUM in the
               correction index; one-line clarification in section 1 and card
               1. No code change.
F6 ACCEPT   -- plan Table 3's stale falsifying wording is superseded by P§4.2;
               recorded as a source erratum.
F7 MANDATORY-- the cleanly-separable-failures scope sentence is now in section
               15, as a scope statement and not a result.
F8 ACCEPT   -- no change.

--------------------------------------------------------------------
NUMBERS (D-011)

  tests          895 passing, 2 skipped, 0 xfailed -- unchanged, prose only
  compute        NONE. Registered total unchanged: 675 CPU fits, 0 GPU-hours.
  data seen      none
  base           c5c8e6f -- UNCHANGED and not announced as moved
  changed        docs/c005_c007_spec.md (rewritten), method_own_voice.md,
                 method_draft.md, rewrite_cards.md, plan_audit.md,
                 DECISIONS.md correction index. constants.py untouched.

=== END UPDATE ===
```
