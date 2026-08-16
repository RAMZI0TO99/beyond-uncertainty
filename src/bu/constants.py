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
