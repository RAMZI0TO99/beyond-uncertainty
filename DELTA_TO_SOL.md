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

**Send delta + `SOL_BUNDLE.txt`.** `BASE` is **`801a33d`** — Sol certified
delta 56 on 2026-08-23 and named this exact commit. **Do not infer a later one.**

**Sol has ruled that no bundle is required for W4/W5.** The next bundle
accompanies the **next genuinely authorised change**. Delta 57 accumulates until
then.

```bash
EXCLUDE="PROJECT_STATE_ARCHIVE.md" BASE=801a33d ./scripts/sol_bundle.sh \
    docs/method_draft.md docs/decision_briefing.md > SOL_BUNDLE.txt
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 57 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-23 (delta-56 certification) · **Weeks 4 and 5 are COMPLETE**; the base moves; Q-012 ruled against me
> - 2026-08-23 (post-certification) · The decisions consolidated into a reading brief
> - 2026-08-23 (methodology completion) · The draft corrected to D-119/D-120 and the four missing mandated sections written
> - 2026-08-23 (rewrite cards) · Seventeen section cards for the student's own-voice rewrite
> - 2026-08-23 (own-voice §1) · The interview rewrite begins — section 1 built from the student's answers

```
=== UPDATE FOR SOL ===
DELTA_ID: 57
PREVIOUS_DELTA_ID: 56
DATE: 2026-08-23
BUNDLE_FILE: SOL_BUNDLE.txt -- regenerated at HEAD; the authorised change it
             accompanies is the methodology prose below (your allocation)
SUBJECT: Your delta-56 certification, filed. W4/W5 complete, base moved to
         801a33d, Q-012 closed. Plus one false locator of mine, found while
         filing it.

NOTHING WAS BUILT THIS SESSION. No code, no tests, no compute, no data. This
delta records the filing of your ruling and will accumulate until there is a
genuinely authorised change to carry.

--------------------------------------------------------------------
1. YOUR CERTIFICATION, FILED AS D-120

Verified before filing, per the standing rule: your quoted bundle sha256
ab9512ba...59c720 matches the delivered file exactly, the delta digest matches
the bundle header, and your reviewed head 801a33d is HEAD. You reviewed the
exact bytes at the exact commit.

Recorded exactly as you ruled:
  W4 COMPLETE and certified
  W5 COMPLETE and certified
  W5 balancer CERTIFIED for its current synthetic-input scope
  DEV-012 CERTIFIED exactly as recorded
  certified base: 801a33d2e10124f2ba7639b6108bce41d5948149, not inferred
  Gate 1 remains FAIL on the MDE
  condition 2 remains NOT ADJUDICABLE, never a PASS
  balancer synthetic-input-only until C-005 exists
  no expansion, recalibration, reserve, repair labels, real data, or Week 6

--------------------------------------------------------------------
2. Q-012 -- YOU RULED AGAINST ME, AND THE DISTINCTION IS THE POINT

Option (b) recorded. C-005 and C-007 are NOT being built.

The sentence I should have written myself, and did not:

  "Completing W4/W5 obligations repaired omissions; it did not authorise
   pulling later implementation forward."

I had those two acts one step apart -- I reasoned from "does it consume data?"
when the operative question was "is it this week's obligation or a later
week's?". Data consumption is a necessary bar, not a sufficient one. Filed in
D-120 in those terms so a reset cannot re-derive my version of it.

The lead is now allocated as you specified: methodology in the student's own
voice, consolidating certified decisions, checking prose against plan and
schedule, PROSE-ONLY interface and acceptance-criteria specs for C-005/C-007,
read-only audits, and resolving contradictions before they become code. No
source code, executable tests, real data, labels or reserve consumption.

--------------------------------------------------------------------
3. >>> A FALSE LOCATOR OF MINE, FOUND WHILE FILING THIS

DELTA_TO_SOL.md's header stated:

  "Deltas 1-7 and 10-54 are in PROJECT_STATE_ARCHIVE.md"

THEY ARE NOT. The archive holds 25 distinct delta ids, the highest being 33.
Deltas 34-55 were replaced without ever being archived -- including delta 55,
which I replaced myself one session ago while reading that same header.

Nothing is lost: every one is recoverable from git history at its delivering
commit, and I verified 34, 45, 54 and 55 individually rather than asserting it.
But a header that tells a reader where to find something it does not contain is
the D-072 defect -- a claim checked only against itself. Nothing compares the
header to the archive, so it stayed wrong through twenty-two replacements.

Corrected to state what is actually true, with the git-history recovery command
written into the header. Delta 56 was archived on replacement, and the
convention resumes from there.

--------------------------------------------------------------------
4. THE DECISIONS, CONSOLIDATED  [PROSE ONLY -- WITHIN YOUR ALLOCATION]

docs/decision_briefing.md. D-001 ... D-120 compressed into something the student
can read in one sitting: what is frozen and why, what the study is, the four
identities, where Gate 1 stands, WHICH ENTRIES ARE SUPERSEDED, the recurring
failure modes, and what is open. Explicitly a reading aid -- where it and the
ledger disagree, THE LEDGER WINS -- and every claim carries its D-number.

No code, no tests, no compute, no data. Squarely inside what you authorised:
"reviewing and consolidating the certified decisions".

The item I want you to check, because it is the one most likely to put a
withdrawn claim into the thesis:

  D-098's SIGNED GATE RECORD still reads "condition 2 | Compute within budget |
  PASS". Section 5 is append-only, so it will always read that way. It was
  corrected to NOT ADJUDICABLE by D-119 and D-120.

A student reading the gate record directly -- which is the natural thing to do
when writing up a gate -- finds PASS in a signed record and no marker at the
point of reading. The brief flags it explicitly. The same shape applies to
D-039/D-042 -> D-044, D-108 -> D-109, and D-114/D-115 -> D-119.

I am not proposing to edit any append-only record. I am asking whether you want
a standing SUPERSEDED marker convention at the point of reading, or whether the
brief plus the correction chain in section 3 is sufficient.

--------------------------------------------------------------------
5. THE METHODOLOGY DRAFT -- CORRECTED, COMPLETED, REVIEW REQUESTED

docs/method_draft.md, 609 -> 695 lines, 14 -> 17 sections. Prose only, Claude's
half of D-019; the student's own-voice rewrite is untouched and remains the
student's allocated work.

TWO THINGS YOU SHOULD CHECK, BECAUSE ONE IS THE ERROR YOU ORDERED CORRECTED:

  a. The Gate 1 section still said the compute estimate was "WITHIN BUDGET" --
     in the one prose document headed for the thesis, surviving your delta-55
     instruction because that instruction was applied to the state files and
     never grepped for in docs/. Now: measured 5.72/6.91 local wall-hours,
     registered 120 GPU-hour trigger, NOT ADJUDICABLE, gate fails on the MDE
     alone. Please confirm the wording.

  b. Four deviations marked "goes in methodology: yes" had NO section:
     DEV-010 (the declined remedy -- written with the 18.75x-33.3x multiplier
             kept as a unit-count ratio and the cross-host prohibition stated
             in prose, so the thesis cannot repeat my D-115 error)
     DEV-011 (local execution host; thread-count non-neutrality recorded)
     DEV-012 (the zero-inflation convention, its estimand and its falsifiable
             W6 checkpoint, in exactly your ratified terms)
     DEV-008 (alpha = 0.05 two-sided, folded into the Gate 1 section)

REQUEST: review the corrected Gate 1 section and the three new sections against
your rulings (D-089, D-098, D-119, D-120, DEV-012). The student rewrites from
reviewed material, not from my unreviewed prose.

Also in the diff: docs/rewrite_cards.md -- seventeen per-section cards (must
say / must never say / frozen numbers with estimands) the student writes from,
fresh, without my draft open; I then check their text against the ledger
without rewriting it. If a card misstates a ruling, that error propagates into
the student's voice, so flag any card you disagree with.

--------------------------------------------------------------------
6. THE OWN-VOICE REWRITE HAS STARTED -- METHOD ON THE RECORD

Per section: Claude asks simple questions in chat; the student answers IN
THEIR OWN WORDS; Claude assembles the section FROM those answers -- keeping
the student's phrasings where right, correcting facts against the ledger,
adding frozen numbers -- and the student reads and confirms each section
before it is accepted. docs/method_own_voice.md carries the sections WITH THE
SOURCE ANSWERS STORED VERBATIM below each one, as provenance of whose voice
it is.

Section 1 (environment rationale) is built and awaiting the student's
confirmation. Corrected on the way, and recorded in the file: the student
described the agent as learning; the agent never learns -- the scripted
policy collects (D-020/D-051), the world model learns (D-032), the critic
diagnoses. Also corrected: "repairs working together" is the AMBIGUOUS
exclusion, not a success case.

If you consider this method outside your Q-012 allocation ("rewriting the
methodology in their own voice"), say so and we stop -- the sections are
clearly marked unconfirmed until then.

UPDATE (same day): section 3 is CONFIRMED; sections 4 and 5 are drafted --
the student's null-result answer ("the test might pass but there are hidden
things from it") is kept nearly verbatim in section 4; the development-vs-
confirmatory-seeds explanation in section 5 is Claude's after a recorded
"don't know", taught in chat before confirmation. Earlier: sections 1 and 2
are CONFIRMED by the student. Section 3
(the scripted collector) is drafted: the student answered two questions with
honest "don't know"s, so paragraphs 1-2 are Claude's explanations, marked as
such in the file, and the student is being taught the content in chat before
confirming. Section 2 note: section 2 (configuration axes) drafted the same way.
Notable: the student answered one question "i do not know? tell me what we
did" -- that paragraph (the balanced sample, D-018) is Claude's explanation,
recorded as such in the file's provenance notes. Corrections recorded: the
half/half balance is fair classification, not a repair-vs-repair contest;
the reserve is predeclared against cherry-picking (D-092). Sections 1-2 both
await student confirmation.

--------------------------------------------------------------------
NUMBERS (D-011)

  tests          895 passing, 2 skipped, 0 xfailed -- UNCHANGED, no code touched
  compute        NONE. Registered total unchanged: 675 CPU fits, 0 GPU-hours.
  data seen      none
  base           801a33d (moved from 51907c6 on your certification)
  built          prose only: method_draft.md corrected + 4 mandated
                 sections; decision_briefing.md. No source code, no tests.

=== END UPDATE ===
```
