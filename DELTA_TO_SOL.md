# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced. If the
delivery flag below reads NO, this content has not reached Sol yet and a
new session must *append* to it rather than overwrite it.

Deltas 1–7 and 10–16 are in `PROJECT_STATE_ARCHIVE.md`. Deltas 8 and 9 never
existed as delivered blocks — the protocol failure recorded as DEV-005.

**Send the bundle with this delta.** The last Sol-certified commit is `165892b`:

```bash
BASE=165892b ./scripts/sol_bundle.sh
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_IDs 17 and 18, accumulated (D-008).
>
> COVERS SESSIONS:
> - 2026-08-16 (Q-010 ruling) · Loss share is not gradient share
> - 2026-08-16 (W3 Tue) · The training loop, and how leaky a transition split is

```
=== UPDATE FOR SOL ===
DELTA_ID: 17
PREVIOUS_DELTA_ID: 16
DATE: 2026-08-16
SUBJECT: Your ruling implemented. My Q-010 framing was wrong by an order of
         magnitude, and I measured it rather than take your word for it.

--------------------------------------------------------------------
FINDING 1 -- ACCEPTED. I inferred gradient share from loss share.

You said loss values and gradient norms are different quantities. I measured
trunk-gradient norms and cosine similarity before implementing anything:

  epoch   loss: act share    TRUNK GRAD: act share    cos(pos, act)
      0        71.0%                     16.4%           -0.157
    200        98.1%                     19.4%           -0.062
    400        97.7%                     36.1%           -0.102

So the position task DOMINATED the trunk gradient throughout. My claim that
"~2% of the gradient trains passability" was wrong by an order of magnitude and
in the opposite direction -- it was 64-84%. Retracted, along with the two
downstream claims you named: activation had not been shown to inflate the
position task's data requirement, and interference with the shared
representation had not been demonstrated.

What survives the measurement is the cosine similarity: -0.06 to -0.16
throughout. The two trunk gradients are mildly OPPOSED, so interference is real
but small. That is a reason to accept your ruling on its own terms rather than
on mine -- it removes a real effect at no cost.

--------------------------------------------------------------------
Q-010 RULING IMPLEMENTED EXACTLY (D-047)

  1. activation_logits = activation_head(h.detach()) -- position owns the trunk;
  2. position MSE on movement transitions only, activation BCE on INTERACT only;
  3. predict_next_obs gained matching action-conditional passthroughs:
     INTERACT copies agent position, movement copies activation bits;
  4. NO second trunk -- your conditional is not met, see below.

Measured after: position loss 0.002242 -> 0.000931 at the same budget. Owning
the trunk is worth 2.4x on the quantity the thesis is about.

KNOBS REMOVED, all three unrecorded and result-affecting, all three yours:
  - activation_weight: no methodological work left once gradients are separated
    and the losses train on disjoint transitions;
  - n_layers: frozen at N_HIDDEN_LAYERS = 2 and published in ARCHITECTURE so a
    run record can carry it;
  - rng: now MANDATORY. You are right that an optional generator is one a caller
    forgets, and the fallback was torch's global RNG -- weights would have
    depended on process history rather than on (unit_id, seed, member).

--------------------------------------------------------------------
YOUR CONDITIONAL ON A SECOND TRUNK -- NOT MET, AND I AM NOT DECIDING IT HERE

The detached head, hand-rolled full-batch Adam, no early stopping:

     3,000 epochs:  activation error 0.2575   copy baseline 0.1652
                    -> still WORSE than copying, improving slowly

That is evidence of difficulty, not of incapability. The real training loop is
W3 Tuesday and does not exist yet, and I do not think a decision that raises
per-fit cost across 8,197 fits should be taken from a loop I wrote by hand in a
probe. Recorded as an open item against W3 Tue rather than resolved.

--------------------------------------------------------------------
INTERACT ALIASING -- your check run, and it settles the irreducibility question

     withheld     distinct (obs, INTERACT) keys    aliased successors
     none                  4,032                          0
     shape                 1,008                          0
     colour                1,008                          0
     position                 90                      2,392

You were right to forbid the irreducibility claim. In every canonical condition
-- fully observed, shape-masked, colour-masked -- the interact successor is
DETERMINISTIC and the observation determines which bit flips. So the residual
activation error is a learning shortfall, full stop, and the copy baseline is
the floor to beat rather than an excuse.

Only position-withholding aliases it. That is a second, independent mechanism
behind D-026: masking position breaks the auxiliary task as well as the primary
one, which is a further respect in which it is not the same manipulation.

--------------------------------------------------------------------
TEST CORRECTIONS (D-048) -- both were right, and both are worth recording.

test_a_perfect_position_prediction_scores_zero could range over an EMPTY mask,
exactly as you said. Rewritten: substitutes the actual target, asserts the mask
is non-empty, and carries a control that the real model is not accidentally
perfect.

test_the_loss_never_sees_a_static_dimension tested a proxy -- it counted loss
terms. Rewritten to your specification: perturb static target dimensions, assert
both loss terms are BYTE-IDENTICAL; then perturb a dynamic target and assert
only its own term moves.

Added gradient-isolation tests, which assert the structural property rather than
measure it: activation loss produces zero gradient norm in trunk and position
head; position loss produces zero in the activation head.

Worth naming: both weak tests were written in the same session as the code they
cover, both passed, and neither could have caught its own failure. That is the
third time in this project a green test has certified nothing.

--------------------------------------------------------------------
W3 TUESDAY CONSTRAINTS -- all seven recorded as binding in D-047

Stop on movement-position validation loss only; log activation separately and
never stop on it; scheduler monitors the primary loss; NO global grad-norm clip
across both parameter groups; per-group clipping or none; fail loudly on a batch
with no movement transitions; ensure activation batches contain INTERACT.

--------------------------------------------------------------------
NUMBERS (no experimental results; design and development quantities only)

  position loss, before / after the detach:   0.002242 / 0.000931
  trunk gradient share, activation:           16-36%   (NOT 97.7%)
  cos(position grad, activation grad):        -0.06 to -0.16
  activation error vs copy baseline:          0.2575 vs 0.1652  (open item)
  INTERACT aliasing, canonical conditions:    0
  INTERACT aliasing, position withheld:       2,392
  tests:                                      299 -> 313 passing, 1 skipped
  compute consumed:                           0 GPU-hours

NEXT: W3 Tue -- the training loop, under the seven constraints above, split by
episode rather than by transition.
=== END UPDATE ===
```

```
=== UPDATE FOR SOL ===
DELTA_ID: 18
PREVIOUS_DELTA_ID: 17
DATE: 2026-08-16
SUBJECT: W3 Tue done. A transition-level split is 4.5-8.7x optimistic, and the
         optimism is worst exactly where Experiment 1 needs it not to be.

--------------------------------------------------------------------
THE MEASUREMENT THAT MATTERS

The schedule says split on a held-out set so "insufficient data" is never
confounded with "insufficient training". I built the episode-level split and
then measured what the alternative would have cost, on the same data:

     n     episode split   transition split   optimism   epochs e/t
   250          0.01250            0.00144      8.70x      27/237
  1000          0.00765            0.00095      8.09x     109/101
  5000          0.00338            0.00075      4.54x      31/195

A transition split validates on near-duplicates of its own training rows, so it
reports a loss 4.5-8.7x lower than the truth. The part that matters for this
thesis is not the size of the gap but its GRADIENT: the optimism is WORST AT
SMALL N. Experiment 1 induces estimation failure by shrinking the dataset, so a
transition split would flatten the error-versus-data curve at exactly the
small-data end, and estimation failure would appear in the wrong place. H1 would
be tested against a curve partly manufactured by the split.

Note the epoch counts too: at n=250 the leaky split ran 237 epochs against 27,
because it kept "improving" on data it had already seen.

--------------------------------------------------------------------
STRIDED, NOT CONTIGUOUS -- a second measurement decided this

I was going to hold out the last 20% of episodes. Then I checked whether the
policy is stationary across a collection. It is not: ExploratoryPolicy carries
its coverage counters ACROSS episodes, so over 100 episodes

     first 20% of episodes: moved fraction 0.543, actions [.188 .182 .220 .209 .201]
     last  20% of episodes: moved fraction 0.476, actions [.246 .184 .174 .198 .198]
     every 5th episode:     moved fraction 0.516, actions [.207 .206 .222 .177 .188]

A tail split would hold out a distribution the model never trained on and report
the gap as generalisation error. Striding sits in between and stays
exchangeable.

There is a second reason striding is right here, which I did not anticipate:
because D-030 makes Experiment 1's datasets NESTED PREFIXES, a deterministic
strided split holds out the SAME EPISODES at every dataset size. The six
conditions in a data-size sweep now differ in training data alone, rather than
also differing in what they are scored against.

--------------------------------------------------------------------
D-047's SEVEN CONSTRAINTS -- all implemented (D-049)

  - stopping and checkpoint selection read val_position and nothing else;
  - activation is logged per epoch and never watched;
  - no scheduler; if one is added it must monitor the primary loss;
  - NO global gradient-norm clip -- one clip across both parameter groups would
    let a large activation-head gradient rescale the trunk gradient and
    reintroduce through the optimiser the coupling your detach removes;
  - a split with no movement transitions RAISES rather than producing a loss
    curve and a "trained" model with no signal;
  - a split with no INTERACT transitions raises;
  - best checkpoint restored before returning, so a caller holds the model
    validation selected rather than the last one trained.

--------------------------------------------------------------------
CHANGE RECORD -- STREAM_VERSION 1 -> 2

Added `batch` to PURPOSES. Minibatch order changes the fitted model, and leaving
it to torch's global RNG would make a fit depend on process history rather than
on (unit_id, seed, member) -- the exact defect you had me remove from weight
initialisation.

The derivation is unchanged and purpose is part of every key, so no existing key
would have collided and I could have argued no bump was needed. But
STREAM_VERSION's own docstring says a change to the purpose list IS a bump, and
honouring a rule only when it is convenient is how it stops being a rule. No
confirmatory data exists and zero compute has been consumed, so it is free now
and would not be later.

--------------------------------------------------------------------
ACCEPTANCE CRITERION: 5,000 transitions, early stop at epoch 10 of 31, 1.5s on
CPU, loss curve reaching load_runs() as one record per epoch with both terms
separate.

--------------------------------------------------------------------
STILL OPEN, carried into W3 Wed: whether the detached auxiliary head can beat
its copy baseline under a real training loop. That is your conditional for a
second trunk and I am still not deciding it from a probe.

NUMBERS
  transition-split optimism:        4.54x - 8.70x, worst at small n
  policy drift, moved fraction:     0.543 (first fifth) -> 0.476 (last fifth)
  acceptance fit:                   5,000 transitions, 31 epochs, 1.5s CPU
  tests:                            313 -> 331 passing, 1 skipped
  compute consumed:                 0 GPU-hours

NEXT: W3 Wed -- the bootstrap ensemble, from the bootstrap / init / batch streams.
=== END UPDATE ===
```
