"""The preregistration, in code.

Every value here is fixed before data collection and is not revised after seeing
data (Plan §4.2, §10.6). They live in one file, alone, for a specific reason:
in Plan v1.1 a withdrawn two-sigma acceptance rule survived in two sections and
would have produced a different ground-truth label depending on which section
the implementation happened to follow. Constants scattered across modules fail
the same way, silently.

Changing anything in this file requires a Change Record in DECISIONS.md
naming the constant, the new value, the reason, and whether any data has already
been seen. If data has been seen, the answer is almost certainly no.
"""

from __future__ import annotations

# --- Ground-truth labelling (Plan §7) -------------------------------------

#: Data repair enlarges the dataset by exactly this factor, drawn from the same
#: generating process. Fixed in Plan v1.1 -- v1.0 said "substantially larger",
#: which made the undiagnosed count in §7.4 an unreported degree of freedom.
DATA_REPAIR_MULTIPLIER = 10

#: A repair is accepted only if the mixed-effects fixed effect for repair is
#: negative, its 95% CI excludes zero, AND the reduction exceeds this fraction
#: of mean per-transition error. Relative rather than absolute because error
#: scales differ across configurations (Plan §7.3).
MIN_PRACTICAL_EFFECT = 0.20

#: Confidence level for every interval in the thesis.
CONFIDENCE_LEVEL = 0.95

#: Permutations used to calibrate the acceptance test against a synthetic null
#: (Plan §7.3, Schedule W5 Wed).
N_PERMUTATIONS = 200

# --- Hypothesis testing (Plan §4.2) ---------------------------------------

#: H3 equivalence margin, in percentage points of balanced accuracy. A
#: difference whose CI lies entirely inside +/- this is a match and falsifies
#: H3; one that spans it is inconclusive and reported as such.
EQUIVALENCE_MARGIN_PP = 5.0

# --- Seed policy (Plan §14.2) ---------------------------------------------
#
# Three counts, each load-bearing for a different claim. Conflating them is the
# specific mistake Schedule W9 Wed exists to prevent.

#: Every condition entering an H1 or H2 claim (Experiments 1, 2A, 2B).
SEEDS_HYPOTHESIS = 5

#: Canonical repair validation -- halves the standard error on the across-seed
#: component, and every label in the thesis rests on this test (Plan §7.3).
SEEDS_REPAIR_VALIDATION = 20

#: The configuration sweep and its repairs. Purpose is label diversity for H3,
#: not a reliability claim.
SEEDS_SWEEP = 3

#: Ablations.
SEEDS_ABLATION = 5

#: Seeds for the W4 Friday failure-threshold calibration (D-097).
#:
#: Added under a Change Record, authorised by Sol: *"Register a distinct
#: threshold_calibration stage with five seeds."* The threshold is a separate
#: obligation from Experiment 1 -- it trains reference models to define the
#: failure set rather than to test a hypothesis -- and `TrainConfig` is not part
#: of `run_id`, so reusing `exp1` would have given a threshold fit the SAME
#: recorded identity as the Experiment 1 fit at that unit and seed.
#: **No data had been seen when this was added.**
SEEDS_THRESHOLD = 5

#: THE FAILURE THRESHOLD. Calibrated once, promoted under the D-035 Change
#: Record, and **permanently frozen** (D-107). Sol authorised the promotion on
#: 2026-08-22 after independently extracting the delivered evidence archive,
#: verifying all 135 artefact digests, reconstructing the deterministic
#: selection, and recomputing this value with NumPy to a bit-identical result.
#:
#: A transition is a **failure** when its error is **STRICTLY GREATER** than
#: this value. The strict boundary is part of the registered definition, not a
#: convention: at equality the transition is *not* a failure. This is not
#: academic -- two transitions in the calibration pool sit exactly here.
#:
#: The estimand -- because a number without one is not a number (D-042, D-044):
#:
#:   * ensemble-mean normalised movement error, K=5;
#:   * fully observed n=5,000 reference models, no confound;
#:   * nine layout x causal-attribute strata, seeds 1000-1004;
#:   * equal stratum weighting by deterministic minimum-count subsampling
#:     without replacement at RNG seed 0 -- 9 x 4,103 = 36,927 of 37,406;
#:   * 95th percentile, NumPy method="linear".
#:
#: Evidence: execution commit 93dc29628ae798031acc74811dc0214ee2bc08cd;
#: immutable attempt runs/w4_threshold/attempt-001;
#: archive       sha256 4a2dd55562bd8d1f46afa074a7cd3961da3d0ffafc29ca1cf6356558c3dade1b
#: record        sha256 310a44839be2b9336248637413378c65c3fa8ed31b8fb309327e0772651e86dc
#: array digests sha256 01b390cb8aef41ca2740b343cef9f761d82121872a25d4e1cc8bfe42f5624002
#:
#: **Never recalibrate.** The attempt is final and the threshold has been
#: inspected, so Sol's invalidation protocol -- which requires declaring an
#: attempt invalid *before* its threshold is read -- can no longer be satisfied.
#: Every failure set, every repair label, and therefore H2 and H3 descend from
#: this single number.
FAILURE_THRESHOLD = 0.610702633857727

#: Confirmatory runs start here; every seed below it is development/pilot data
#: and is permanently excluded from confirmatory runs, failure-threshold
#: calibration, repair acceptance, and critic training or evaluation (D-034).
#:
#: The exclusion is not hypothetical. Two design decisions were taken *after*
#: inspecting collected data: the Week 2 coverage evidence behind the PPO
#: substitution, and the identity-predictor probe that produced the
#: dynamic-target decision. Data that shaped a design choice cannot also test
#: it. A base offset rather than an inventory of tainted datasets, because an
#: inventory has to be maintained correctly forever and an offset does not --
#: everything ever looked at during development lies below the line by
#: construction.
CONFIRMATORY_SEED_BASE = 1000

#: The critic evaluation set's per-unit trace cap and its balancing seed
#: (D-115), frozen on Sol's authorisation **before any labelled data exists** --
#: which is the only circumstance in which they may be set at all.
#:
#: The cap is a **MAXIMUM, NOT AN ELIGIBILITY THRESHOLD.** A cleanly labelled
#: unit with fewer than 50 eligible traces stays in, with all of its traces.
#: It is never excluded for being small and never resampled with replacement to
#: reach 50 -- either would silently make unit inclusion a function of trace
#: count, which is not a registered criterion.
CRITIC_TRACE_CAP_PER_UNIT = 50

#: The balancing draw is deterministic. Selection uses a stable hash over
#: (seed, split, label, unit_id) -- never Python's `hash()`, which is
#: process-randomised by PYTHONHASHSEED and would make the evaluation set
#: irreproducible across runs while looking perfectly deterministic within one.
CRITIC_BALANCE_SEED = 0

#: How balanced accuracy weights the registered statistical unit (D-044).
#: "unit" gives every configuration-condition equal weight, which is what Plan
#: §10.4's unit-level balancing implies; "cluster" would give every comparison
#: group equal weight, making a six-unit canonical group count the same as one
#: sweep unit. These are different estimands with different effective sample
#: sizes at the same data -- 75/72.6 against 125/115 at ICC = 1 -- so the choice
#: is preregistered rather than settled by whichever number is convenient later.
#: Dependence is handled by group-bootstrap intervals, which does not change the
#: point estimate's estimand.
BALANCED_ACCURACY_WEIGHTING = "unit"

#: Steps per episode. **10, not 50** (D-052). At 50 the smallest condition
#: (N=100) contained two episodes, and after an internal split one *training*
#: episode -- an episode bootstrap over one episode has exactly one possible
#: sample, so ensemble diversity there came from initialisation alone. At 10 it
#: contains ten. Measured cost at N=5000: rule-carrying transitions 748/1177 ->
#: 712/1123 and (shape, action) coverage 100% either way, so the independence is
#: bought for ~5% of the informative transitions.
EPISODE_LENGTH = 10

#: Complete episodes in the fixed validation pool, used only for early stopping
#: and checkpoint selection. **Identical for every dataset size in a comparison
#: group**, and disjoint from training (D-052).
VALIDATION_EPISODES = 40

#: Complete episodes in the fixed evaluation pool: reported error, disagreement
#: curves and failure-set construction. Never used for stopping or selection,
#: and identical across dataset sizes *and* ensemble members.
EVALUATION_EPISODES = 100

#: What defines the per-dimension normalising scale (D-061, Sol's ruling).
#: Plan §10.3 requires per-dimension normalised error and never says which set
#: the normalisation is measured over. It matters: the scale is a **vector**, so
#: it does not cancel between the H2 ratio's numerator and denominator, and
#: recomputing it from a failure subset moved the registered endpoint by up to
#: 4.6%. Measured once from the full evaluation pool restricted to the movement
#: domain, **before any failure mask**, then reused for the whole pool and every
#: subset of it, across every member and dataset size sharing that pool.
NORMALISATION_SCALE_SOURCE = "evaluation_pool"
NORMALISATION_SCALE_DOMAIN = "movement"

# --- The H1 trend test (Plan §4.2, Schedule W4 Mon; frozen by D-068) ------
#
# One function serves the Week 4 reliability gate and the Week 10 H1 verdict.
# The reading rule below was fixed by Sol **before** the function was applied to
# any data, which is the whole point of it: a rank correlation over six sizes
# bends on a non-monotone small end, and the pilot's disagreement curve peaks at
# N=250. Choosing a friendlier instrument after seeing that is exactly what
# preregistration exists to prevent.

#: H1 predicts disagreement **falls** as data grows. A positive trend is a
#: reversal and fails; it is not an alternative form of success.
TREND_EXPECTED_DIRECTION = "negative"

#: Pass only when the whole interval is below zero. Touching zero fails.
TREND_PASS_REQUIRES_UPPER_BOUND_BELOW = 0.0

#: The interval is a **paired seed-block bootstrap**: one seed's complete
#: six-size curve is one block. With 3 development and 5 confirmatory seeds the
#: resample space is small enough to **enumerate exactly** (3³ = 27, 5⁵ = 3,125)
#: rather than sample, so no bootstrap RNG exists to seed, drift or forget.
TREND_BOOTSTRAP = "exact_paired_seed_block"

#: Declared rather than left to a library default, because the default has
#: changed across numpy versions and the interval is a registered endpoint.
TREND_QUANTILE_METHOD = "linear"

# --- The Week 4 reliability gate (S§W4 Tue, Plan §11.3; frozen by D-070) ---
#
# Predeclared **before** Tuesday's run. The gate tests the estimator across
# three layouts while holding the causal rule and the confounding fixed, so a
# failure is attributable to the estimator rather than to the manipulation.

#: The three gate configurations differ only in layout.
GATE_CAUSAL_ATTRIBUTE = "shape"
GATE_CONFOUND_RATE = 0.0
GATE_LAYOUTS = ("uniform", "clustered", "sparse")

#: Five **development** seeds per configuration. Development because the gate is
#: estimator *selection*: spending confirmatory seeds to choose an estimator
#: consumes the evidence the Week 10 verdict needs (D-034, D-068).
GATE_SEEDS = (0, 1, 2, 3, 4)

#: Rung 0 passes only if **all three** configuration-level trend tests pass. No
#: majority vote and no pooled curve: this is a reliability gate, and
#: sensitivity to configuration is itself a failure of reliability.
GATE_AGGREGATION = "all_configurations_must_pass"

# --- Design scale (Plan §10.7) --------------------------------------------

#: Minimum labelled configuration-conditions, and minimum held out. Power
#: depends on min(N_0, N_1), not the total, because balancing is at unit level.
MIN_LABELLED_UNITS = 300
MIN_HELDOUT_UNITS = 60

# --- Experimental grids (Plan §8) -----------------------------------------

#: Experiment 1 -- estimation failure, dataset size sweep.
DATA_SIZES = (100, 250, 500, 1000, 2500, 5000)

#: Experiment 2B -- capacity sweep, at complete input features.
HIDDEN_SIZES = (16, 32, 64, 128, 256)

#: Experiment 2A -- the four non-zero confound levels between the decoy
#: attribute and the withheld causal attribute (Plan §8.2.1). Note that
#: confound is ALSO a configuration axis (Plan §13.1.2); whether these are the
#: same units or additional ones is PROJECT_STATE.md Q-003, due Week 2 Wed.
CONFOUND_LEVELS_2A = (0.25, 0.5, 0.75, 0.9)

#: Confound as a configuration axis, including the zero level.
CONFOUND_LEVELS_SWEEP = (0.0, 0.25, 0.5, 0.75, 0.9)

# --- Defaults that are swept, not frozen ----------------------------------

#: Ensemble size. Default 5, swept at 3/5/10 in the Week 14 ablation.
DEFAULT_ENSEMBLE_SIZE = 5

#: Critic trace window. Default 5, ablated at 1 and 20 in Week 14.
DEFAULT_WINDOW = 5

# --- Compute (Plan §14.3) -------------------------------------------------

#: Above this measured total, take reductions in the documented order:
#: ablations, then full Experiment 5, then configuration count down to the
#: measured MDE. Seeds are NOT a lever -- withdrawn in Plan v1.2.
COMPUTE_ESCALATION_TRIGGER_GPU_HOURS = 120


# --- The W4 fallback ladder, frozen before rung 0 runs (D-071) -------------
#
# Sol's ruling, 2026-08-18: freeze every rung's training parameters **before**
# observing the rung-0 result. Otherwise Wednesday picks the repair after having
# watched Tuesday fail, which is choosing a repair after seeing the result --
# the same class of error the preregistration exists to prevent.
#
# The rungs are **cumulative**: each is the previous estimator with one
# parameter changed, so a pass at rung n names exactly what had to be added.
#
# THE RUNG-2 SEMANTIC CORRECTION (pre-data, D-071). Plan §11.3 says to raise
# inter-member diversity by increasing the bootstrap ratio. In the implemented
# API `bootstrap_ratio` is the number of with-replacement draws divided by the
# episode count, so expected unique-pool coverage is 1 - e^-ratio: measured
# 0.395 at 0.5, 0.635 at 1.0, 0.866 at 2.0. Raising the ratio therefore makes
# members MORE alike, not less. Rung 2 is subbagging at 0.5 -- the parameter
# move that actually implements the plan's stated intent. Recorded as a
# correction to the plan rather than applied silently (P§ wins on design; §4).

#: Rungs whose parameters are frozen and which may therefore be executed.
#: Rungs 3 and 4 are deliberately absent: they are secondary estimators, and
#: Sol's ruling is that their method-specific parameters are frozen before
#: either is executed, not now. Reaching rung 3 also means H1 is falsified for
#: ensembles (P§11.3) -- an architectural decision, not a run (D-062).
#
# EVERY training parameter is frozen, not only the two the rung varies (D-072).
# Sol: "Parameters such as learning rate, batch size, epoch budget and patience
# currently remain unchecked. A run altered through one of those settings could
# pass the present gate." They are pinned here rather than inherited from
# `TrainConfig`'s defaults, so that changing a default cannot silently move what
# the frozen ladder means.
#
# (Sol's list also named validation fraction. `val_fraction` was REMOVED in the
# Week 3 audit -- the validation pool is generated independently under D-052 --
# so there is no such knob to check. Noted rather than silently skipped.)
RUNG_SPECS: dict[int, dict] = {
    0: {
        "estimator": "ensemble",
        "ensemble_size": 5,
        "bootstrap_ratio": 1.0,
        "granularity": "episode",
        "lr": 1e-3,
        "batch_size": 128,
        "max_epochs": 500,
        "patience": 20,
        "description": "episode-bootstrap deep ensemble, the registered default",
    },
    1: {
        "estimator": "ensemble",
        "ensemble_size": 10,
        "bootstrap_ratio": 1.0,
        "granularity": "episode",
        "lr": 1e-3,
        "batch_size": 128,
        "max_epochs": 500,
        "patience": 20,
        "description": "episode-bootstrap deep ensemble, ensemble size doubled",
    },
    2: {
        "estimator": "ensemble",
        "ensemble_size": 10,
        "bootstrap_ratio": 0.5,
        "granularity": "episode",
        "lr": 1e-3,
        "batch_size": 128,
        "max_epochs": 500,
        "patience": 20,
        "description": "episode SUBBAGGING at ratio 0.5 -- see the semantic "
        "correction above; this raises member diversity, raising the ratio lowers it",
    },
}

#: The training fields a rung freezes, in the order they are hashed. Adding a
#: field to `TrainConfig` without adding it here leaves it unchecked, so the
#: gate asserts this list covers `TrainConfig` exhaustively.
RUNG_TRAIN_FIELDS: tuple[str, ...] = (
    "lr", "batch_size", "max_epochs", "patience", "ensemble_size", "bootstrap_ratio",
)

#: Schema versions deliberately do NOT live here (Sol, 2026-08-18). This file is
#: the preregistration: everything in it is a scientific choice frozen before
#: data. The evidence contract, manifest and metric-row versions are
#: implementation compatibility versions that must stay *evolvable* through
#: explicit bumps, which is the opposite property. They are in
#: `bu.stats.gate` -- EVIDENCE_CONTRACT_VERSION, MANIFEST_VERSION,
#: METRIC_SCHEMA_VERSION.

#: Named for refusal messages and for the record. A rung in this tuple exists in
#: the ladder but cannot be executed until its parameters are frozen.
RUNG_NAMES: dict[int, str] = {
    0: "ensemble",
    1: "ensemble_10",
    2: "subbagging_10_at_0.5",
    3: "mc_dropout",
    4: "last_layer_laplace",
}

#: Rungs that exist but whose parameters are NOT frozen, and which therefore
#: fail closed if a gate is asked to produce a verdict at them.
RUNG_PARAMETERS_UNFROZEN: tuple[int, ...] = (3, 4)
