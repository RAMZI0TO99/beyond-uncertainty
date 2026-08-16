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

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 17.
>
> COVERS SESSIONS:
> - 2026-08-16 (Q-010 ruling) · Loss share is not gradient share

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
