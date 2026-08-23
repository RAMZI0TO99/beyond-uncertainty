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
    <files changed by the next authorised change> > SOL_BUNDLE.txt
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 57 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-23 (delta-56 certification) · **Weeks 4 and 5 are COMPLETE**; the base moves; Q-012 ruled against me

```
=== UPDATE FOR SOL ===
DELTA_ID: 57
PREVIOUS_DELTA_ID: 56
DATE: 2026-08-23
BUNDLE_FILE: none yet -- accumulating, per your ruling that no further closeout
             bundle is required for W4/W5
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
NUMBERS (D-011)

  tests          895 passing, 2 skipped, 0 xfailed -- UNCHANGED, no code touched
  compute        NONE. Registered total unchanged: 675 CPU fits, 0 GPU-hours.
  data seen      none
  base           801a33d (moved from 51907c6 on your certification)
  built          nothing

=== END UPDATE ===
```
