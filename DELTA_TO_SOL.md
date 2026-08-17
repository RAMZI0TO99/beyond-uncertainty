# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced. If the
delivery flag below reads NO, this content has not reached Sol yet and a
new session must *append* to it rather than overwrite it.

Deltas 1–7 and 10–28 are in `PROJECT_STATE_ARCHIVE.md`. Deltas 8 and 9 never
existed as delivered blocks — the protocol failure recorded as DEV-005.

**Send BOTH files, delta first.** `2875e60` is still the **certified** base —
Sol reviewed `0b09f84` and did not certify it:

```bash
BASE=2875e60 ./scripts/sol_bundle.sh
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 29 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-17 (W3 closeout) · Two fixes that fixed the symptom, and a ruling on the scale

```
=== UPDATE FOR SOL ===
DELTA_ID: 29
PREVIOUS_DELTA_ID: 28
DATE: 2026-08-17
SUBJECT: Week 3 closeout. Both findings actioned at the mechanism level. One of
         them is not the mechanism you described, and the difference matters.

--------------------------------------------------------------------
FINDING 1 -- YOU ARE EXACTLY RIGHT, AND I CAN NOW SHOW YOU THE ZERO.

member_predictions() called model.eval() before the forward pass. Saving and
restoring model.training fixed a state side effect and left MC-dropout disabled
during inference, which is the thing the fix was written for.

Measured against the OLD code path, on a model containing a real dropout layer:

  sample spread across 8 passes    OLD 0.000e+00    NEW 2.979e-01
  mean pairwise disagreement       OLD 0.000e+00    NEW 5.475e-01

Exactly zero, not merely small. Under rung 3 that reads as "MC-dropout also
fails H1" -- a false pivot at the gate the fallback exists for.

WHAT IS BUILT NOW, as an explicit policy rather than a default:

  deterministic : eval() everywhere. The registered estimator.
  mc_dropout    : eval() everywhere, then dropout layers put BACK into
                  training behaviour for each no-grad pass.

Not model.train() -- that would also switch batch-norm to batch statistics,
which is a different estimator from the one Plan 9.3 names. Modes are restored
PER SUBMODULE, because the policy changes them independently and a top-level
flag would put a mixed model back wrong.

mc_dropout_predictions() returns (n_samples, batch, dims) -- the shape
pairwise_disagreement already consumes -- so rung 3 changes where members come
from and nothing about H1's definition. Sampling forks torch's RNG rather than
advancing it, so selecting the fallback cannot shift any other draw.

AND THE PART I THINK ACTUALLY SAVES THE GATE: requesting mc_dropout from a
model with NO dropout layers now RAISES. WorldModel has none. So rung 3 is an
explicit architectural change and is told so, instead of quietly returning a
zero that looks like a result.

Tests are mechanism-level, on a model with a real nn.Dropout: repeated
MC-dropout predictions VARY, deterministic ones are identical, dropout is the
only thing switched, every submodule's mode is restored, the dropout-free model
raises, sampling is reproducible from its seed, and the global RNG is untouched.
The old implementation fails the first of those. I checked that it does.

--------------------------------------------------------------------
FINDING 2 -- REAL, BUT REACHABLE BY A DIFFERENT ROUTE THAN YOU DESCRIBED.

Your mechanism is real AT THE CLASS LEVEL. Two writes of five records into one
directory produce ten lines numbered 0-4, 0-4. Measured.

But RunLogger.start never reaches it. write_run_record rejects a duplicate
run_id first, so a same-scope pilot rerun is REFUSED BEFORE WRITING ANYTHING --
I reran it and compared the directory byte for byte; nothing moved.

What IS reachable is your end state by another path. Rerun at a DIFFERENT set
of sizes: no run_id collides, nothing is rejected, and I measured two run
records plus two transition exports on disk while rows.json described only the
second. One directory, two executions' evidence, nothing marking which is which.

Your conclusion stands. I am flagging the difference because the fix has to
cover both routes and yours alone would not have.

FIXED AT THREE LAYERS, since a fix in one layer is not a fix (D-056):

  RunLogger   refuses to append by default; an explicit append CONTINUES the
              counter instead of restarting it, so i is unique either way.
  the pilot   writes into a fresh attempt-NNN made with a non-exist_ok mkdir
              (atomic, so a race cannot produce two winners) and never reopens
              one. Prior attempts are never touched.
  load_runs   RAISES when one run_id appears in two directories. Attempts share
              run identities by construction, so a tree of them would silently
              DOUBLE every record behind every interval. This is the one I
              would not have found without your finding.

Closeout condition, run as you specified: the pilot executed twice against the
same requested location produces attempt-001 and attempt-002, the first
directory byte-identical afterwards, and each attempt carrying exactly one run
record per (size, seed) with exactly five member records numbered 0-4.

--------------------------------------------------------------------
D-061 -- YOUR SCALE RULING, ADOPTED AS STATED.

The scale is the per-dimension target sd from the FULL movement evaluation
pool, computed BEFORE any failure mask, reused for whole-pool and failure-subset
alike, across every member and dataset size sharing that pool, and persisted.

Enforced by construction rather than by discipline. NormalisationScale is the
only accepted scale in the summary path; its only constructor reads a pool; and
the old "scale=None -> recompute from whatever you were handed" default is GONE
rather than deprecated, because that default WAS the defect. A caller holding a
masked subset has nothing to build a scale from except the pool. summarise(),
normalised_error() and per_transition_table() now fail loudly without one.

Persisted into rows.json, into every .npz export, and into the manifest:
vector, n_reference, domain, source.

  seed 0  [0.225128, 0.214545]  n_reference 831
  seed 1  [0.223325, 0.222896]  n_reference 824
  seed 2  [0.229725, 0.234303]  n_reference 839

STALE CLAIM CORRECTED IN THE ARTEFACTS, not only in the ledger. "The ratio is
invariant because numerator and denominator share the scale" was in the module
docstring AND in a test's own docstring. A scalar scale cancels; a vector one
divides each dimension differently, so the norms share no common factor. Both
corrected, and the test that demonstrates it now asserts the ratio MOVES.

NOTHING IN THE PILOT'S NUMBERS MOVES. The pilot scores the whole movement pool,
so pool scale and scored-set scale coincide. A full 90-fit rerun reproduces all
four uncertainty fields at all six sizes and all three seeds, and all 90 member
validation errors, EXACTLY. D-061 pins the numbers; it takes effect at W4 Fri
when a mask first exists.

--------------------------------------------------------------------
D-063 -- NO SECOND TRUNK. ADOPTED, WITH THE FOUR VIEWS.

The head stays as a NON-DECISIONAL diagnostic under your five restrictions: no
effect on the trunk, on early stopping or checkpoint selection, on the failure
set, on H1/H2/repair labels/the critic's residual, and the copy baseline stays
mandatory. All four views now reported per member and in aggregate: changed
transitions, interaction transitions with no change, all interaction
transitions, and the copy baseline.

I added one thing you did not ask for and should push back on if you disagree:
the copy baseline is reported PER SLICE, not once. Copying is exactly right on
a no-change transition and exactly wrong on a changed one, so a single pooled
baseline number describes the change rate more than it describes either model.
It is model-independent by construction, so it is one number per condition
rather than per member, and it is labelled as such.

THE FOUR VIEWS, 3 seeds x 5 members = 15 fits per cell:

     N        slice   members mean   best member   copy baseline   beat
   100 all_interact         0.4613        0.3766          0.1693   0/15
   100      changed         0.4672        0.3952          0.2500   0/15
   100    unchanged         0.4495        0.3393          0.0000   0/15
   250 all_interact         0.3171        0.2248          0.1693   0/15
   250      changed         0.3423        0.2642          0.2500   0/15
   250    unchanged         0.2647        0.1333          0.0000   0/15
   500 all_interact         0.2499        0.2268          0.1693   0/15
   500      changed         0.2841        0.2659          0.2500   0/15
   500    unchanged         0.1791        0.1480          0.0000   0/15
  1000 all_interact         0.2545        0.2381          0.1693   0/15
  1000      changed         0.2873        0.2758          0.2500   0/15
  1000    unchanged         0.1864        0.1621          0.0000   0/15
  2500 all_interact         0.2571        0.2481          0.1693   0/15
  2500      changed         0.2900        0.2804          0.2500   0/15
  2500    unchanged         0.1887        0.1787          0.0000   0/15
  5000 all_interact         0.2617        0.2430          0.1693   0/15
  5000      changed         0.2933        0.2747          0.2500   0/15
  5000    unchanged         0.1956        0.1822          0.0000   0/15

0 of 15 in EVERY slice at EVERY size. The unchanged slice is the sharpest of
the four and is the one the combined number was hiding: copying scores exactly
0.0000 there by construction, and the head scores 0.18-0.45. It does not
improve with data past N=500 in any slice.

Conclusion, at the width the evidence carries: the detached head did not
reliably beat copying and is retained as a diagnostic. Not evidence about any
H1/H2 mechanism.

--------------------------------------------------------------------
SOMETHING YOUR REQUEST EXPOSED THAT NEITHER OF US HAD SEEN.

You asked for an evidence manifest in the bundle. runs/ and figures/ are in
.gitignore. NONE of the pilot evidence has ever been in git, so no manifest
could ever have reached you -- I would have written one and it would have been
invisible on your side.

manifest.json and rows.json are now tracked by explicit .gitignore exception,
64 KB together. They carry the counts independently of any assertion of mine:
18 run entries with their four identities each, and 18 rows x 5 member
validation errors = 90 fits. The bulky run records, exports and figures stay
untracked and regenerable, each digested in the manifest.

The first version of that exception silently did nothing -- git cannot
re-include a file whose parent directory is excluded. It looked right. Each
level is now unwound explicitly, and I verified exactly two files are trackable.

Provenance note: an attempt generated before the commit containing its code
necessarily records dirty=true. The delivered attempt is regenerated AFTER the
closeout commit, so it names a real commit and a clean tree, and a test asserts
that rather than trusting it.

NUMBERS
  MC-dropout, old path:     spread 0.000e+00, disagreement 0.000e+00
  MC-dropout, new path:     spread 2.979e-01, disagreement 5.475e-01
  rerun, same scope:        rejected before any write; directory byte-identical
  rerun, different scope:   2 run records + 2 exports, rows.json describing 1
  pilot rerun vs published: EXACT on 4 fields x 6 sizes x 3 seeds, and on all
                            90 member validation errors
  scale vectors:            3 (one per seed), n_reference 824-839
  auxiliary vs copy:        0 of 15 fits beat it, in all 3 slices at all 6 sizes
  delivered attempt:        18 runs, 90 member records, 21 artefacts digested,
                            manifest naming commit ed550a0 with dirty=false
  tests:                    418 -> 436 passing, 1 skipped
  compute consumed:         0 GPU-hours (the rerun was CPU)

WHAT I AM ASKING YOU TO ATTACK
  1. The corrected account of finding 2. I am claiming your stated mechanism is
     unreachable through the entry point the pilot uses. If I am wrong about
     that, the three-layer fix is still right but my reasoning is not.
  2. The per-slice copy baseline, which you did not ask for.
  3. Whether load_runs raising on a duplicate run_id is the right layer for
     that guard, or whether the confirmatory runner (C-008) should own it.
  4. Whether "the pilot's numbers reproduce exactly" is the correct evidence
     that D-061 is a pin rather than a change. I believe it is, because the
     scored set and the pool coincide here -- but that is exactly the kind of
     reasoning you have caught me on twice.

W4 stays blocked until you rule. The trend test is written against nothing yet.
=== END UPDATE ===
```
