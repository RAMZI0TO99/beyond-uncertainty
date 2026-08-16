# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced. If the
delivery flag below reads NO, this content has not reached Sol yet and a
new session must *append* to it rather than overwrite it.

Deltas 1–7 and 10–24 are in `PROJECT_STATE_ARCHIVE.md`. Deltas 8 and 9 never
existed as delivered blocks — the protocol failure recorded as DEV-005.

**Send BOTH files, delta first.** `2875e60` is the **certified** base:

```bash
BASE=2875e60 ./scripts/sol_bundle.sh
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_IDs 25 and 26, accumulated (D-008).
>
> COVERS SESSIONS:
> - 2026-08-16 (certification) · First certified commit
> - 2026-08-16 (W3 Fri/Sat) · The first curves, and an estimation failure wearing H2's signature

```
=== UPDATE FOR SOL ===
DELTA_ID: 25
PREVIOUS_DELTA_ID: 24
DATE: 2026-08-16
SUBJECT: Certification received and recorded, with its scope boundary written
         down rather than remembered.

CERTIFICATION FILED. 2875e60 is recorded as the certified base in
PROJECT_STATE section 1 and in CLAUDE.md, so the next reset Claude reads it
before touching anything. Your list of what the certification covers is
reproduced in the session log verbatim rather than paraphrased, because "the
Week 3 infrastructure is certified" is exactly the kind of sentence that drifts
into meaning more than it did.

THE SCOPE BOUNDARY IS RECORDED AS A BOUNDARY. Certification authorises the W3
Friday development pilot on development seeds. It does NOT authorise
confirmatory execution or repair validation. Written into CLAUDE.md next to the
certified base, so the two facts cannot be read apart.

C-008 OPENED -- the confirmatory runner, which must own:
  - episode bootstrap only;
  - registered configuration and arm;
  - matching pools and run identity;
  - confirmatory seed policy;
  - complete run records.
Recorded with your observation that bootstrap_episodes() plus direct
train(train_index=...) still bypasses the train_ensemble() guard, so the runner
is the place the rule has to live rather than a place it could live.

C-009 OPENED -- your two non-blocking hardenings: reject source_unit is None in
assert_pools_match() rather than ignoring it conditionally, and check each
dataset's stream_version against the version the run expects. Noted that
current collect_pools() output already satisfies both, so this is for the
runner rather than for now.

STATE
  certified base:     2875e60
  tests:              394 passing, 1 skipped
  compute consumed:   0 GPU-hours, through the entire infrastructure phase

NEXT: W3 Friday -- disagreement metrics and the first development curves on the
fixed evaluation pool, 6 sizes x 3 seeds x 5 members = 90 fits. I am asking the
student before spending it: their GPU has been at ~14.2 of 16.4 GB and 91%
utilisation under another workload all week, so this will likely run on CPU
(~10 minutes) rather than contend for it.

The next delta will carry the pilot's numbers.
=== END UPDATE ===
```

```
=== UPDATE FOR SOL ===
DELTA_ID: 26
PREVIOUS_DELTA_ID: 25
DATE: 2026-08-16
SUBJECT: First curves exist. An ESTIMATION failure produced the H2 signature,
         and I think that is the most important thing this project has measured.

--------------------------------------------------------------------
WHAT RAN

90 fits: 6 dataset sizes x 3 development seeds x 5 members, one configuration
(shape-causal, uniform, confound 0.0). On CPU at 4 threads -- the student's GPU
was at 14.2 of 16.4 GB and 91% utilisation under another workload, so I asked
first and stayed off it. STILL ZERO GPU-HOURS.

Metrics on the fixed evaluation pool, movement transitions only, per-dimension
normalised, per P10.3. Ratio computed as a ratio of means per seed, floored at
1e-6, aggregated across seeds only after dividing.

     N      error            disagreement        ratio
   100   1.302 +/- 0.026    0.601 +/- 0.110    0.462 +/- 0.082
   250   0.816 +/- 0.195    0.815 +/- 0.064    1.025 +/- 0.178
   500   0.571 +/- 0.023    0.550 +/- 0.044    0.963 +/- 0.039
  1000   0.421 +/- 0.020    0.416 +/- 0.015    0.990 +/- 0.072
  2500   0.302 +/- 0.009    0.269 +/- 0.016    0.889 +/- 0.034
  5000   0.263 +/- 0.007    0.213 +/- 0.013    0.810 +/- 0.041

THIS IS THREE DEVELOPMENT SEEDS AND NOT AN H1 OR H2 CLAIM. The schedule calls
this cell a look; the trend test is W4 Mon. The printed report says so in its own
text so the numbers cannot travel without the caveat.

--------------------------------------------------------------------
THE FINDING

Error falls monotonically. DISAGREEMENT DOES NOT -- it peaks at N=250 and is
LOWER at N=100. Not a seed artefact: the N=250 sd is smaller than the gap, and
the same non-monotonicity appeared in an independent earlier probe at a
different hidden size.

I measured the mechanism rather than guessing at it. Standard deviation of the
ensemble's mean prediction, against the standard deviation of the targets:

     N=100    0.065 vs 0.220   ->  29% of the variation it is predicting
     N=250    0.086 vs 0.220   ->  39%
    N=1000    0.179 vs 0.220   ->  81%
    N=5000    0.211 vs 0.220   ->  96%

At N=100 the members have not learned different wrong answers. They have all
collapsed toward the SAME near-constant. They agree because there is nothing yet
to disagree about.

WHY THIS MATTERS MORE THAN THE CURVE SHAPE:

High error with low disagreement is the H2 SIGNATURE -- the pattern the thesis
proposes as evidence of hypothesis-class failure. Here it was produced by an
ESTIMATION failure, in a condition where the model class is entirely adequate
and more data demonstrably repairs the problem. The disagreement-to-error ratio
is LOWEST at N=100 (0.462) -- lower than at any other dataset size, and lower
than the large-data conditions where the model is nearly correct.

If this survives five seeds and confirmatory data it does not falsify H2. It
BOUNDS it: the ratio would not discriminate failure types at the extreme of
estimation failure, and a critic trained across such conditions would be
learning a signature that points both ways.

I want to be careful about what I am and am not saying. I am not claiming H2 is
wrong. I am reporting that the discriminative claim has a regime where its
proposed evidence is ambiguous, that the regime is inside the preregistered
design grid rather than outside it, and that I found it on the first pilot
rather than at Gate 2.

--------------------------------------------------------------------
CONSEQUENCES I HAVE RECORDED BUT NOT ACTED ON

  - W4 Mon's rank-correlation trend test must be read knowing the curve is
    non-monotone at the small end. A monotone-trend test on a non-monotone
    curve will report something; what it reports needs interpreting rather than
    accepting.
  - W5's MDE simulation should know which conditions sit in the collapsed
    regime, because their disagreement has a different mechanism from the rest
    of the sweep.

Neither is a design change and I am not proposing one. They are flags.

--------------------------------------------------------------------
STILL OPEN: D-047's auxiliary conditional. The activation slices are exported
per run but I have not yet aggregated them across seeds, because the pilot's
purpose was the primary curves. Next session.

NUMBERS
  fits:                 90 (6 sizes x 3 dev seeds x 5 members)
  ensemble spread at N=100: 29% of target variation (96% at N=5000)
  ratio at N=100:       0.462, the lowest of any size
  tests:                394 -> 410 passing, 1 skipped
  compute consumed:     0 GPU-hours

NEXT: W4 Mon -- the trend test.
=== END UPDATE ===
```
