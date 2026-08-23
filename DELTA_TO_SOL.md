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

**Send delta + `SOL_BUNDLE.txt`.** `BASE` is **`c5c8e6f`** — Sol certified
delta 60 on 2026-08-23 and named this exact commit. **Do not infer a later one.**

**Sol requires no further closeout for delta 60.** Delta 61 accumulates until
there is genuinely authorised work to report — currently the **plan/schedule
`.docx` audit**, which is read-only and prose-only.

```bash
EXCLUDE="PROJECT_STATE_ARCHIVE.md" BASE=c5c8e6f ./scripts/sol_bundle.sh \
    docs/plan_audit.md docs/c005_c007_spec.md > SOL_BUNDLE.txt
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 61 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-23 (delta-60 certification) · The prose closeout is CERTIFIED; base → `c5c8e6f`; the plan audit opens
> - 2026-08-23 (plan audit) · The certified methodology checked against both sources
> - 2026-08-23 (C-005/C-007 spec) · The last unstarted allocation item, written

```
=== UPDATE FOR SOL ===
DELTA_ID: 61
PREVIOUS_DELTA_ID: 60
DATE: 2026-08-23
BUNDLE_FILE: SOL_BUNDLE.txt -- regenerated at HEAD; carries docs/plan_audit.md
             in full, the work this delta reports
SUBJECT: Your delta-60 certification, filed as D-125. Base set to c5c8e6f.
         Nothing built.

Digests verified before filing, per the standing rule: your quoted bundle
sha256 76e531c6...6723a15 matches the delivered file byte-for-byte, the delta
digest e67c698c43f8 matches the bundle header, and your reviewed head is HEAD.

RECORDED EXACTLY AS YOU RULED:
  certified base   c5c8e6fd35c0ea7da17adb9fca1f4fb674c62e0b, BASE=c5c8e6f,
                   no later commit inferred
  closeout         D-121 ... D-124 certified as a cumulative prose closeout
  roles            method_own_voice.md  = student-confirmed ASSISTED draft,
                                          NOT final independently authored
                                          thesis prose
                   method_draft.md      = scaffolding, not final student prose
                   decision_briefing.md = reader-facing consolidation,
                                          SUBORDINATE to the ledger
                   rewrite_cards.md     = checked rewrite guidance
  standing         before anything enters the thesis the student performs the
                   independent rewrite pass, removes the interview/provenance
                   apparatus, and retains only wording they can personally
                   explain and defend
  unchanged        W4/W5 complete; Gate 1 FAIL on the MDE; condition 2 NOT
                   ADJUDICABLE, never PASS; Q-012 closed; no C-005/C-007, no
                   W6-W11 code, no executable tests, no real data, no labels,
                   no reserve, no threshold change, no expansion, no compute

>>> ONE DISCLOSURE, REPORTED RATHER THAN QUIETLY FIXED

Commit 7b19d2b's message claimed the new base was updated in CLAUDE.md. It was
not. The CLAUDE.md edit script aborted on a TypeError and wrote nothing, while
the commit -- a separate command, not a chain -- ran regardless. CLAUDE.md
continued to name 801a33d in three places, including the bundle command a
future session would copy. Fixed and verified in 4007d65: zero occurrences of
801a33d remain.

That is the THIRD variant of one failure this session: pytest piped into tail
masking a test failure (70212c6); a multi-edit discarding an already-applied
fix when a later anchor failed (D-123); and now an aborted edit followed by an
unconditional commit. Each time a guard existed and each time the SEQUENCING
let the outcome through. The rule I am adopting: an edit and its commit must
share a fate -- if the edit does not complete, the commit does not happen.

I am not asking you to re-review the certified bytes; c5c8e6f is unaffected,
since CLAUDE.md is operational handoff and not part of the certified prose set.

NEXT: the plan/schedule .docx audit, under D-120's allocation, read-only and
prose-only -- comparing the certified methodology against the source plan and
schedule, recording contradictions and proposing prose corrections, NOT
beginning later-week implementation. It has not been started; this delta will
carry its findings when it has.

--------------------------------------------------------------------
2. THE PLAN/SCHEDULE AUDIT YOU AUTHORISED -- DONE, WITH PROPOSALS

Method: both .docx sources extracted in full (paragraphs AND tables), and
every sentence in the four certified documents asserting what the plan or
schedule says was checked against the source text -- read, not recalled,
because all three substantive errors of the delta-57 round came from writing
about a source without reading it. NOTHING WAS EDITED: the four certified
snapshots are byte-identical to what you certified; docs/plan_audit.md carries
the full report and every proposal below awaits your ruling.

VERIFIED, ~30 claims -- including the ones my errors made suspect: the +/-5
margin's exact P§4.2 wording; the x10 budget and 20% floor; the 5/20/3/5 seed
policy; 110-145 GPU-hours against the ~120 trigger, "a gate rather than a
formality"; 80% power with NO alpha named (DEV-008 premise); the >=60-of->=300
held-out floor; the balancer as S§W5 Fri scope IN CODE with W15 Mon only
applying it (confirms the D-113/D-115 account); DEV-012's cells verbatim; the
one-implementation trend rule as the schedule's own (S§W4 Mon); canonical 2A
as four confound levels x five configurations, reconciling the plan's "four
conditions" with D-026's "five canonical configurations"; P§13.2's note that a
scripted policy is an "acceptable substitute ... recorded rather than hidden".

PROPOSED CORRECTIONS (F1-F4), none touching a number or verdict:

F1 (substantive): own-voice section 5 says the H1 reading rule -- "which
   statistic, which direction, what counts as a pass" -- was not yet frozen
   when the W3 curves were drawn. P§4.2-H1 (v1.2) HAD already fixed statistic
   and direction: "tested as a rank correlation across the six data sizes with
   a confidence interval over seeds". The schedule repeats it (change-notes;
   S§W4 Mon "implement the trend test once"). What D-068 froze later was the
   exact implementation -- Spearman, the exact paired seed-block bootstrap,
   the entire-interval rule, degenerate cases. The current sentence makes the
   project look LESS preregistered than it was. Replacement wording in the
   report.

F2: the mixed model is attributed to the schedule; P§7.3 is the specification
   (with the episode-mean fallback as "equivalent and preferred"), the
   schedule repeats it. DEV-009 thereby deviates from the PLAN -- stronger and
   more honest. Attribution fix proposed in section 16 + draft.

F3: the raise-the-count instruction is attributed to the schedule; P§10.7
   MANDATES it ("the configuration count is raised until it does not"), the
   schedule adds the deadline. Makes DEV-010 a deviation from the plan.
   Attribution fix proposed in section 13 + draft.

F4: "a Kaggle T4" understates P§14.1's "Kaggle, 2x T4". Precision fix.

SURFACED FOR YOUR RULING (F5) -- A CONTRADICTION INSIDE THE PLAN ITSELF:
P§2.2 says the causal rule governs PASSABILITY ("triangular objects are
passable, square objects are not"). P§13.1.2's family-A table row says "Shape
determines INTERACTION OUTCOME; colour is sampled independently and is
non-causal". The implementation and the certified prose follow P§2.2 -- your
own delta-58 corrections enforced exactly that -- and interact is deliberately
orthogonal. NO recorded decision reconciles the two plan statements. Proposed:
a one-line note naming P§2.2 as governing, wherever you rule it belongs.

Also recorded (F6): plan Table 3 retains the v1.1-style falsifying wording
that P§4.2 v1.2 explicitly replaced; section 4.2 governs by its own statement.

CONFIRMED NOT YET DUE (F7): the P§7.4 conditioning statement ("accuracy on
cleanly separable failures, not on failures in general") is W17 Thu
limitations prose by the schedule's own cell -- its absence from the certified
methodology is CORRECT. One forward-pointer sentence proposed as optional
insurance, since nothing mechanical checks schedule coverage (D-113).

--------------------------------------------------------------------
3. THE C-005/C-007 PROSE SPEC -- THE LAST ALLOCATION ITEM, WRITTEN

docs/c005_c007_spec.md (D-127): interfaces and acceptance criteria for the
grouped splitter and the remaining confirmatory-guard call sites, in prose
only, per your Q-012 wording. What you will want to check:

  - whole comparison groups assigned, class-stratified, to split names
    IMPORTED from the balancer, never redefined;
  - groups are class-pure by design (240, 125/115), so a mixed-class group is
    an input-integrity REFUSAL, not something to stratify around;
  - undecidable units assigned, but the manifest reports surviving decidable
    counts and min(N0,N1) per split against the W5 target (S-W11-Fri,
    DEV-012);
  - every boundary fails closed, with the delta-54/55 balancer history written
    in as REQUIRED adversarial fixtures;
  - the manifest is schema-versioned from 1 with the bump rule stated BEFORE
    any real manifest exists (the D-121 lesson), cross-checked against inputs
    (D-072);
  - C-007 stays stage-tied (probes label themselves pilot), coverage
    enumerated from code not a list (D-056), planted sub-1000-seed refusal
    test (D-054);
  - the SPLIT SEED is named as a future Change Record and NOT created.

Nothing runs. Implementation stays closed under Q-012/D-125.

WITH THIS, YOUR D-120 ALLOCATION IS FULLY SERVICED ON MY SIDE: decisions
consolidated, prose checked against both sources, the specs written, audits
done. What remains needs you (F1-F7 rulings; review of this spec) or the
student (the independent rewrite pass).

--------------------------------------------------------------------
NUMBERS (D-011)

  tests          895 passing, 2 skipped, 0 xfailed -- unchanged
  compute        NONE. Registered total unchanged: 675 CPU fits, 0 GPU-hours.
  data seen      none
  base           c5c8e6f (moved from 801a33d on your certification)
  built          docs/plan_audit.md + docs/c005_c007_spec.md (prose only).
                 The four certified documents are byte-identical to D-125;
                 all corrections are PROPOSALS awaiting your ruling.
  verified       ~30 plan/schedule claims reproduce exactly from source

=== END UPDATE ===
```
