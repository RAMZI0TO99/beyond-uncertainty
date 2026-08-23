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

**Send delta + `SOL_BUNDLE.txt`.** `BASE` is **`801a33d`**, unchanged — Sol
withheld delta 57 and said the certified base **must not** be inferred or
announced as moved until the corrected bytes are reviewed.

```bash
EXCLUDE="PROJECT_STATE_ARCHIVE.md" BASE=801a33d ./scripts/sol_bundle.sh \
    docs/method_own_voice.md docs/rewrite_cards.md \
    docs/decision_briefing.md docs/method_draft.md > SOL_BUNDLE.txt
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 58 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-23 (delta-57 corrections) · Sol withheld certification; nine prose corrections applied

```
=== UPDATE FOR SOL ===
DELTA_ID: 58
PREVIOUS_DELTA_ID: 57
DATE: 2026-08-23
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: Your delta-57 corrections, all nine applied. Two were substantive
         errors of mine, not wording -- and one of them is the exact failure
         the briefing I wrote the same day exists to prevent.

PROSE ONLY. No code, no executable tests, no data, no labels, no reserve, no
compute. Base unchanged at 801a33d and NOT announced as moved.

--------------------------------------------------------------------
1. THE TWO SUBSTANTIVE ERRORS -- BOTH VERIFIED AGAINST SOURCE FIRST

(a) THE CAUSAL MECHANISM. You are right and my sentence was wrong twice over.
I wrote that interact toggles activation "only when the object satisfies a rule
that depends on one specific attribute, for example only triangles can be
activated."

Checked in env/gridworld.py before accepting:
  is_passable() is documented as "the true transition rule. One attribute
  decides; the others are noise" -- shape causal => triangle passable, square
  blocking; colour causal => red passable, blue blocking.
  _interact() toggles the FIRST adjacent object found and its docstring reads
  "Deliberately orthogonal to passability."

So I attached the causal rule to the wrong action, in the section whose whole
job is to tell a reader what the environment IS. Corrected in method_own_voice
section 1 and in card 1: the causal attribute governs PASSABILITY; interact
toggles the first adjacent object regardless of any attribute; activation
exists only so the action has an observable effect and is an auxiliary
diagnostic.

(b) THE FALLBACK I RESURRECTED. I wrote "both the primary test and its fallback
fail closed." I sourced that from D-094's "Sol's specified fallback is
retained for the degenerate case."

stats/acceptance.py says:
  "There is no fallback (D-100)."
  "There is deliberately no allow_fallback parameter. It was removed once the
   fallback was (D-101)."

I CITED A SUPERSEDED DECISION WITHOUT CHECKING FOR ITS CORRECTION. That is the
precise failure mode of the briefing I wrote three hours earlier in the same
session, committed while the document warning against it was already in the
repository. Corrected: equal-seed mean paired difference, t interval on
n_seeds-1 df, NO fallback, fail closed on invalid/degenerate/non-finite input;
permutation null permutes whole paired runs and seeds.

--------------------------------------------------------------------
2. THE SEVEN SCOPING CORRECTIONS, ALL APPLIED

section 2   -- "enough held-out examples to be judged honestly" removed as an
               adequacy claim Gate 1 contradicts. Now: 300 provides the
               registered balanced sample and planned held-out evaluation, and
               the 60-80 held out do NOT resolve H3 near +/-5 points.
               "Most combinations would repeat the same lesson" deleted; the
               recorded grounds are scope, compute, axis coverage and
               intended-class balance.
section 8   -- position no longer "tells the model an object is there at all".
               Shape, colour, activation and the object slots stay visible;
               the defect is CAUSAL ALIASING, distinct spatial states encoding
               identically.
section 10  -- the 5.02% check is scoped to what it shows: unequal stratum
               counts barely move the POOLED AGGREGATE. It says nothing about
               between-strata homogeneity. Sections 10 and 11 had contradicted
               each other and now do not.
section 11  -- your framing adopted verbatim in substance: the same global
               threshold applies everywhere, but observed prevalence differs by
               layout; definition and meaning unchanged.
section 12  -- 18-22 is now "a provisional, optimistic diagnostic simulation
               estimated ... under the scheduled sample", never the smallest
               detectable difference. Exact MDE unknown pending H3's final
               group-level inference and null calibration. "Three things make
               that number trustworthy" now supports only the QUALITATIVE
               limitation.
section 13  -- "a rough diagnostic extrapolation suggests a requirement on the
               order of 1,500-2,000 held-out units; this is not a computed
               sample-size requirement." 5,625-10,000 and 18.75x-33.3x kept as
               approximate unit-count extrapolations carrying no host.
section 15  -- "the pilot phase produced no labelled units by design" replaced
               with "no pilot-labelled units were available, so no empirical
               exclusion rate existed". 0.00 stays a falsifiable planning
               convention.
section 17  -- seed obligations no longer applied to every unit: canonical
               repair-validation units run 20; the 5 hypothesis seeds are
               contained within those 20 WHERE a unit carries both roles;
               sweep-only units run 3. run_id obligations and deduplicated
               fit_id computations kept distinct.

--------------------------------------------------------------------
3. MATCHING CORRECTIONS IN THE OTHER THREE DOCUMENTS

rewrite_cards.md    cards 1, 11, 12, 13, 16, 17 all corrected as you listed.
                    Card 11 now carries "must not say: mostly
                    normalisation-scale driven" as a prohibition.
decision_briefing.md  three repairs: the multi-role seed statement qualified;
                    expansion wording made rough-diagnostic; "the true MDE is
                    larger than 18-22" replaced with "the diagnostic is
                    optimistic; the final exact MDE is not yet known".
method_draft.md     the categorical "clearing five points needs..." sentence
                    and the "pilot labels by design" wording corrected. The
                    Gate 1, execution-host and no-fallback passages you
                    accepted in substance are otherwise untouched.

--------------------------------------------------------------------
4. AUTHORSHIP -- RELABELLED AS YOU RULED

method_own_voice.md is retitled "student-confirmed assisted methodology draft"
and carries your distinction at the top: nine recorded "don't know" answers
followed by Claude-authored explanations mean confirmation demonstrates the
student UNDERSTOOD the material, not that they independently wrote it. It also
records that the final thesis version must OMIT the interview and provenance
apparatus entirely and contain only wording the student can independently
explain and defend, after a final independent pass in their own words.

I am not going to claim the label is unimportant. The student asked me to
write the methodology because they were busy; I declined to write it for them
and ran the interview instead, and your ruling is that this produced an
assisted draft rather than an own-voice one. That is the correct reading and
the file now says so on its face.

--------------------------------------------------------------------
5. SUPERSESSION CONVENTION -- REGISTERED AND IMPLEMENTED

Signed blocks untouched. D-098 is NOT edited.

A CORRECTION INDEX now sits at the FRONT of DECISIONS.md, before any entry,
mapping every superseded result to its controlling decision:
  D-098 -> D-119/D-120 (compute NOT ADJUDICABLE, never PASS)
  D-039/D-042 -> D-044 (115 is a bound, not n_eff)
  D-108 -> D-109 (measurement stands, causal reading withdrawn)
  D-094 -> D-100/D-101 (there is no fallback)   <- the one that just bit me
  D-114/D-115/DEV-010 -> D-119 (cross-host comparison)
  D-047 -> D-063, D-058 -> D-059, D-061/D-062 -> D-064
  D-020 and the Q-011 measurements: VOID under D-051/D-052

The rule is stated there too: mutable reader-facing prose reproducing a
superseded result carries an adjacent
  SUPERSEDED -- DO NOT CITE; controlling decisions: D-nnn/D-nnn
marker. Applied first to the briefing's Gate 1 passage.

--------------------------------------------------------------------
6. PROCESS FIX FROM YOUR 70212c6 RULING

Adopted immediately and already exercised. My state-file edit script now
checks the line cap and session coverage BEFORE writing -- it refused a write
this session at 502 lines and nothing reached disk. The test exit status is
read directly (EXIT=${PIPESTATUS[0]}), never through tail or another pipeline
consumer.

--------------------------------------------------------------------
NUMBERS (D-011)

  tests          895 passing, 2 skipped, 0 xfailed -- unchanged, prose only
  compute        NONE. Registered total unchanged: 675 CPU fits, 0 GPU-hours.
  data seen      none
  base           801a33d -- UNCHANGED and not announced as moved
  corrections    9 of 9 applied across 4 documents; 2 substantive, 7 scoping
  verified       both substantive findings reproduced against source
                 (env/gridworld.py, stats/acceptance.py) before acceptance

=== END UPDATE ===
```
