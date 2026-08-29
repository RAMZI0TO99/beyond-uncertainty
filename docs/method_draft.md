# Method — running draft

Drafted by Claude for the student to rewrite. **This is scaffolding, not final
prose.** The reasoning is checked against the plan and the implementation; the
voice is not yours yet. Rewrite it — a thesis that sounds like its author is
worth more than one that reads smoothly, and you will be defending these
sentences.

Written during the week each design decision was made, per Schedule W1 Thu and
W2 Thu and the plan's warning that leaving prose to Month 5 is the most common
way a project of this shape runs out of time.

---

## Environment design rationale *(Schedule W1 Thu, ~400 words)*

The experiments in this thesis require an environment in which the question
"could this model class have represented the true dynamics?" has a definite
answer. That requirement, rather than any consideration of task difficulty or
realism, determines every choice made below.

**Why a custom gridworld rather than a stock benchmark.** The central
manipulation of Experiment 2A is the withholding of a specific causal feature
from the model's input while the environment continues to depend on it. This
demands an environment in which the experimenter chooses which attribute is
causal — and can rotate that choice across attributes to show the effect is not
an artefact of one particular feature. Stock MiniGrid fixes its own transition
semantics, and Procgen offers no attribute-level control at all. Neither can be
made to support the manipulation without modification so extensive that the
result is a custom environment carrying a misleading name. A purpose-built
generator is the honest option, and it is also the smaller one: the environment
is roughly three hundred lines, where adapting a benchmark would cost more and
leave its original assumptions in place.

**Why symbolic state rather than pixels.** This is the choice on which the
validity of the whole design rests. The distinction the thesis studies is
whether the true transition function lies inside the model's hypothesis class.
Over a factored symbolic state that statement is precise: withholding an
attribute removes a set of dimensions from the input space, and no function of
the remaining dimensions can express a rule that depends on the removed ones.
The claim `f* ∉ H` is then true by construction and verifiable by inspection of
the encoder.

Over pixels the same claim becomes ill-posed. Shape is not absent from an image
that contains a triangle; it is merely encoded in a form a small convolutional
network may or may not recover. A failure to learn the rule could then reflect
insufficient capacity, insufficient data, or an unlucky initialisation — the
very confusion the thesis exists to separate. Choosing pixels would make the
independent variable unmeasurable.

The cost is external validity, and it should be stated rather than defended:
results established here concern factored symbolic dynamics, and their extension
to perceptual inputs is future work rather than a claim of this thesis.

**What the environment contains.** An eight-by-eight grid with boundary walls,
four to six objects carrying shape, colour and position, four movement actions
and one interaction action. Transitions are deterministic, because stochastic
dynamics would introduce an irreducible error component that the labelling
protocol has no category for: a failure that neither more data nor a model
change repairs would be recorded as *undiagnosed* whether it arose from
misspecification or from noise. Determinism removes that ambiguity by
construction.

---

## The configuration axes, and why they exist *(Schedule W2 Thu, ~400 words)*

A single environment configuration, however carefully built, cannot support the
central comparison of this thesis. The reason is a matter of effective sample
size rather than of thoroughness.

The diagnosis critic is evaluated on held-out data, and the unit of that hold-out
is the *configuration-condition* — an environment configuration together with the
manipulation applied to it — not the individual transition. Transitions drawn
from one training run are strongly correlated: they share a model, a dataset, an
initialisation and an environment. Treating them as independent observations
would produce confidence intervals far narrower than the evidence supports, and
would let an apparent five-point difference in balanced accuracy rest on what is
effectively a handful of independent draws. The equivalence margin that decides
H3 is five percentage points, so this is not a technicality: it determines
whether the headline result can be resolved at all.

Four axes therefore vary independently. The **causal attribute** rotates across
shape, colour and position, so that any result is a statement about withholding
*a* cause rather than about shape in particular. The **confound rate** — the
correlation between the decoy attribute and the causal one — varies from zero to
0.9, and is the manipulation of Experiment 2A: it controls how well a model
restricted to the decoy can imitate the true rule, and therefore how severe the
misspecification is. The **layout distribution** varies the spatial arrangement
of objects across three procedural generators, so that the diagnosis signal is
not an artefact of one placement pattern. The **manipulation level** — dataset
size, withheld feature, or capacity — defines the experimental condition itself.

Their product, restricted to the combinations that are meaningful, yields more
configuration-conditions than the compute budget permits, so the design draws a
balanced subset of three hundred. The subset is chosen deterministically and
stratified over every axis, because a truncated enumeration is not a sample: an
early implementation that stratified without the confound axis produced
ninety-nine conditions at zero confound and nine at 0.9, which would have left
the strongest shortcut condition — the one where the shortcut is most tempting
and most wrong — almost absent from the evaluation set.

The subset is also balanced across the two intended failure classes, because the
power of the H3 comparison depends on the smaller class rather than the total.
It should be read as an intention rather than a guarantee: the ground-truth label
of any condition is established by the repair protocol, not by how the condition
was built, and the ambiguous and undiagnosed cases removed at that stage will
reduce both classes by an amount that is not known in advance.

---

## The behaviour policy, and why it is not PPO *(Schedule W2 Sat, ~300 words + figure)*

*This section discharges Plan §13.2's requirement that the substitution be
recorded rather than hidden. It is a methodology section, not an appendix.*

The plan specifies a PPO agent for data collection. This thesis substitutes a
scripted exploratory policy: a coverage-biased random walk that seeks out
adjacent objects, attempts to move into them, and periodically interacts with
them. Plan §13.2 permits the substitution and requires it to be declared.

**The reason is scope, not convenience.** The policy is not an object of study.
No hypothesis in this thesis concerns behaviour, no result is reported per
policy, and the diagnosis critic never observes a return. What the policy must
do is produce transitions from which the true dynamics are learnable. PPO
integration and tuning was among the largest consumers of human time in the
original Month 1, and it would have bought nothing the design measures.

**The substitution also removes a confound.** The transition rule concerns
passability, so it can only be learned from transitions in which the agent
attempted to enter an occupied cell. Those are rare under undirected
exploration. Had a learned policy converged toward avoiding obstacles — the
usual outcome of any reward that penalises wasted steps — the informative
transitions would have become rarer as training progressed, and the resulting
dataset would have been systematically impoverished in exactly the events the
world model needs. A fixed, declared procedure is easier to defend than a
learned one whose data distribution drifts.

**The evidence.** Attempted moves into objects, by dataset size, under the
scripted policy and a uniform random baseline:

| dataset size | scripted: passable | scripted: blocking | random: passable | random: blocking |
|---:|---:|---:|---:|---:|
| 100 | 13 | 22 | 7 | 11 |
| 250 | 48 | 50 | 10 | 13 |
| 500 | 61 | 122 | 16 | 18 |
| 1000 | 172 | 200 | 33 | 36 |
| 2500 | 359 | 641 | 90 | 97 |
| 5000 | 760 | 1228 | 178 | 204 |

The scripted policy yields three to six times more rule-carrying transitions at
every dataset size, and both passability classes are represented throughout —
a dataset containing only walk-throughs would demonstrate half the rule.

**The one place this could have gone wrong.** If coverage were the binding
constraint at large dataset sizes, then Experiment 1's "estimation failure"
family would be measuring exploration quality rather than sample size, and H1
would be testing the wrong proposition. It is not: coverage rises monotonically
with dataset size and saturates well before the largest condition. The smallest
condition is genuinely thin, but Plan §3.2.1 defines estimation failure to
include data that "does not cover the relevant region of the state-action
space" provided more data from the same generating process repairs it — which
the table shows it does. Thin coverage at n=100 is therefore the manipulation
operating as intended rather than a confound within it.

A per-condition coverage report is written alongside every dataset, so this
property is checked for each condition rather than assumed from the pilot.

---

## Correction to the behaviour-policy evidence *(2026-08-16, D-051 / D-054)*

**The coverage figures reported in the W2 Sat section above were measured under
a policy that is no longer the one this thesis uses, and are superseded.**

The scripted policy carried its coverage counters *across* episodes. Because
Experiment 1's datasets are nested prefixes of one collection, that made dataset
size confounded with behaviour distribution: rule-carrying transitions per step
ran at 0.520 in the first hundred transitions and 0.280 by the five-thousandth,
and the action distribution at the smallest condition was far from uniform. The
smallest condition was therefore not a smaller sample of the same process — it
was a sample of a different one. A data-size sweep built on it would have varied
two things and attributed both to sample size.

The counters are now cleared at the start of every episode. Fixed action
probabilities and the within-episode coverage logic are unchanged, so the
substitution argument itself is unaffected: the policy still seeks the
rule-carrying transitions a uniform random walk starves.

**Evidence from the stationary generator**, over eight independent development
seeds, reported as mean ± sd:

| N | rule-carrying transitions per step | pass/block balance | (shape, action) coverage |
|---|---|---|---|
| 100 | 0.227 ± 0.082 | 0.608 ± 0.223 | 0.225 ± 0.083 |
| 1,000 | 0.252 ± 0.025 | 0.694 ± 0.129 | 1.000 ± 0.000 |
| 5,000 | 0.250 ± 0.006 | 0.686 ± 0.044 | 1.000 ± 0.000 |

The rate of rule-carrying transitions is now **flat in N** rather than falling
with it, which is the direct evidence that the confound is gone. Thin coverage
at N = 100 remains, and remains the manipulation working on Plan §3.2.1's own
definition — estimation failure includes data that does not cover the relevant
region, provided more data from the same generating process repairs it, which it
does.

Episode length was shortened from 50 steps to 10 at the same time, so that the
smallest condition contains ten independent episodes rather than two. That
matters for the ensemble rather than for coverage: a block bootstrap over one
training episode has exactly one possible sample. The measured cost is small —
at N = 5,000, rule-carrying transitions fell from 748/1,177 to 712/1,123 with
(shape, action) coverage complete either way.

**A note on how this was established.** The generator is *designed* to produce
episodes that are independent conditional on configuration and seed: environment
state resets independently, every adaptive counter resets, the action
probabilities and within-episode rules are fixed, and no mutable state other
than independent random-number progression crosses an episode boundary. An
episode-index diagnostic found no material residual drift. That diagnostic is
consistent with the design; it does not by itself prove independence, and is not
reported as though it did.

---

## What the first curves look like *(Schedule W3 Sat — written before any formal test, corrected after review)*

Six dataset sizes, three development seeds, one configuration (shape-causal,
uniform layout, no confound). Metrics on the fixed evaluation pool, movement
transitions only, per-dimension normalised. **Three seeds cannot support H1**;
the schedule calls this cell a look, and the trend test is Week 4 Monday.

| N | held-out error | mean pairwise disagreement | ratio\* |
|---|---|---|---|
| 100 | 1.302 ± 0.026 | 0.601 ± 0.110 | 0.462 ± 0.082 |
| 250 | 0.816 ± 0.195 | **0.815 ± 0.064** | 1.025 ± 0.178 |
| 500 | 0.571 ± 0.023 | 0.550 ± 0.044 | 0.963 ± 0.039 |
| 1,000 | 0.421 ± 0.020 | 0.416 ± 0.015 | 0.990 ± 0.072 |
| 2,500 | 0.302 ± 0.009 | 0.269 ± 0.016 | 0.889 ± 0.034 |
| 5,000 | 0.263 ± 0.007 | 0.213 ± 0.013 | 0.810 ± 0.041 |

\* **This is not the registered H2 ratio.** Plan §10.3 defines that endpoint
over a condition's *failure set* — the transitions whose error exceeds the
Week 4 Friday threshold, which does not exist yet. The column above is an
exploratory whole-pool ratio over all movement transitions. It is
hypothesis-generating, not evidence that an H2 signature occurred.

**Error falls monotonically with dataset size.** The least interesting line here
and the most expected.

**Disagreement does not.** It rises from N = 100 to N = 250 and falls thereafter.
Paired within seed, the N = 250 minus N = 100 difference is +0.179, +0.360 and
+0.102 — the direction reproduced in all three development seeds. That is the
whole claim; three seeds carry no inferential weight beyond it.

**What the members are doing, measured per member rather than inferred from
their average.** Standard deviation of each member's predictions as a fraction
of the targets':

| N | ensemble mean | least-contracted member | most-contracted member |
|---|---|---|---|
| 100 | 0.231 | 0.639 | 0.219 |
| 250 | 0.538 | 0.836 | 0.220 |
| 500 | 0.737 | 0.832 | 0.738 |
| 5,000 | 0.950 | 0.974 | 0.939 |

The story is **heterogeneity, not collapse**. At N = 100 most members contract
sharply, but at least one retains 64% of the target's variation; the ensemble
mean is more contracted than any individual member, so part of its flatness is
members cancelling rather than each member flattening. At N = 250 the spread
across members is widest — 0.220 to 0.836 — and that is exactly where
disagreement peaks: members disagree most when some have learned the rule and
others have not. By N = 5,000 they have converged on the same answer and
disagreement is low because they are all right rather than because they are all
flat.

**What this does and does not say about H2.** High error with low disagreement
is the pattern the thesis proposes as evidence of hypothesis-class failure, and
the smallest condition here shows a version of it — the lowest whole-pool ratio
in the sweep (0.462) in a condition designed to induce estimation failure. But
two things have to happen before that sentence can be made properly. The failure
set must exist, so the registered ratio can be computed on the transitions it is
defined over. And the condition's label must come from the counterfactual repair
protocol rather than from how it was constructed — Plan §7.1 is explicit that a
condition is labelled by what repairs it, and data repair has not run.

So the honest statement is narrower than it first appeared, and worth stating
carefully: **in a small-data condition the disagreement-to-error ratio was lower
than in the well-fitted conditions, and the mechanism appears to be that
members contract heterogeneously rather than that the model class is
inadequate.** If that survives the failure-set definition, five seeds and
confirmatory data, it would bound where the H2 ratio can discriminate. It is not
yet evidence that it does not.

Two consequences for the schedule rather than for the thesis. Week 4 Monday's
trend test must be read knowing the curve is non-monotone at the small end. And
Week 5's minimum-detectable-effect simulation should know which conditions sit
in the heterogeneous-contraction regime, because their disagreement has a
different mechanism from the rest of the sweep.

*Figures:* `figures/w3_error_vs_data.png`, `figures/w3_disagreement_vs_data.png`.
*Per-transition exports:* `runs/w3_pilot/attempt-001/transitions_n*_seed*.npz`,
accounted for with their digests in `runs/w3_pilot/attempt-001/manifest.json`.

## The normalising scale, and why it is fixed to the evaluation pool *(2026-08-17, D-061 as corrected by D-064; call site enforced by D-076)*

Plan §10.3 requires per-dimension normalised error and does not say which set
defines the normalisation. That omission is not cosmetic. Because the scale is a
**vector**, it does not cancel between the numerator and the denominator of the
disagreement-to-error ratio: dividing each dimension by a different amount
reshapes both vectors, so their norms share no common factor. Recomputing the
scale from a failure subset rather than from the evaluation pool therefore moves
the registered H2 endpoint — measured on pilot data, by up to **4.6%** at a 5%
failure set, with the pool scale at [0.229, 0.224] against [0.294, 0.348] over
the worst 5%. Week 4 Friday's failure set is exactly such a subset.

The scale is therefore fixed by preregistration: the per-dimension standard
deviation of the targets, computed **once from the full evaluation pool
restricted to movement transitions, before any failure mask**, and reused
unchanged for the whole-pool and failure-subset statistics alike, across every
ensemble member and every dataset size that shares that evaluation pool. It is
recorded alongside every result it produced, with the number of transitions it
was measured over. Restricting attention to a failure set changes *what* is
measured; it does not change the units it is measured in.

This is a definition rather than a result, and it does not move any number
reported above: the pilot scores the whole movement pool, so the pool scale and
the scored-set scale coincide there, and a complete rerun reproduces every
figure in the table exactly. It takes effect from Week 4 Friday, when a failure
mask first exists.

---

## What the error is, and what it is not *(DEV-007, D-032 — mandated in the methodology)*

Plan §10.2 defines the primary metric as held-out one-step prediction error,
`E_t = ||s_{t+1} − f_θ(s_t, a_t)||`, and leaves the dimension set of that norm
unspecified. The omission matters more than it looks. The observation is a
factored vector in which most components — object shapes, colours, positions —
are static across a transition and are reproduced by a deterministic
passthrough. Averaging the norm over all of them dilutes the manipulated
mechanism roughly fifteen-fold, and worse, it rescales the metric *between*
experimental families: withholding a feature changes the observation width, so
the same model quality yields a different number depending on which condition
it was measured in.

The error is therefore computed on the **next agent position only, over
movement-action transitions only**, each dimension divided by the fixed scale
described above — the per-dimension standard deviation of the evaluation pool's
targets, not the grid extent. (The deviation log records this as
"grid-normalised", which is loose: the implementation measures a standard
deviation, and the distinction matters because that scale is a *vector* and does
not cancel in the H2 ratio.) Activation accuracy is
reported separately as a secondary metric, and static components never enter the
score. This is a deviation from a literal reading of the plan, recorded as such,
and it defines what every error number in this thesis means.

Two consequences are worth stating because they are easy to miss. Blocked
movement transitions carry **1.67×** the position error of free moves, so
layouts that block more are harder in a way unrelated to the manipulation. And
the `interact` action is deterministic and perfectly predictable in every
canonical condition — zero aliased successors — but becomes aliased when
position is withheld, which is a second mechanism by which withholding position
differs in kind from withholding an attribute.

## Why position-causal conditions are not canonical Experiment 2A *(DEV-006, D-026 — mandated)*

Experiment 2A withholds the feature that causes the dynamics, so the true
function leaves the hypothesis class. The five canonical configurations cover
**shape and colour only**. Position-causal conditions are run, but in the
three-seed configuration sweep as a declared robustness configuration rather
than as canonical 2A conditions.

The reason is that withholding position is not the same manipulation. It removes
object *occupancy* rather than an attribute of a visible object. Measured:
withholding position leaves **37.5%** of (observation, action) keys aliased,
against **10.0%** for shape and colour, in a key space **26× smaller**. That is a
different structural failure from the one Plan §8.2.1 describes, and pooling the
two would let a qualitatively different mechanism drive an Experiment 2A result.
This bounds what the Experiment 2A finding is a finding *about*, so the
measurement belongs beside the claim.

## The reliability gate, and the rung it passed at *(Schedule W4 Tue, D-074/D-075 — mandated)*

Before any hypothesis is tested, the estimator must be shown capable of tracking
estimation failure at all. The gate asks a narrow question: on well-specified
conditions, where more data genuinely is the repair, does ensemble disagreement
*fall* as the dataset grows? If it does not at any rung of the estimator ladder,
H1 is recorded as falsified for ensembles and the thesis becomes a
characterisation study — a decision made here, in Month 1, rather than in
Month 4.

The test is Spearman's rho between mean pairwise disagreement and the six
registered dataset sizes, with an exact paired seed-block bootstrap interval
enumerated over all resamples rather than sampled. It passes only if the
**whole** 95% interval lies below zero. The rule was frozen before it saw data.

**The gate passed at rung 0** — the default five-member ensemble, episode-level
block bootstrap at ratio 1.0 — on all three predeclared configurations
independently, so the ladder stopped there and rungs 1 and 2 were never run.
Ninety ensembles, 450 fits, four minutes fifty-two seconds on CPU.

| configuration | rho | 95% interval |
|---|---|---|
| uniform | −0.9429 | [−0.9429, −0.9429] |
| clustered | −0.9429 | [−0.9429, −0.8286] |
| sparse | −0.9429 | [−0.9429, −0.9429] |

The three coefficients are identical because Spearman reads ranks only and all
three mean curves carry the same rank pattern. −0.9429 is exactly one adjacent
transposition away from perfect reversal.

**On the zero-width intervals.** Two of the three are a single point, and that
must not be read as zero uncertainty:

> Exact paired seed-block bootstrap percentile intervals were computed over all
> 3,125 resamples. Because Spearman correlation over six dataset sizes has
> highly discrete support, the bootstrap distributions contained only two or
> three distinct values. A zero-width percentile interval therefore reflects
> quantile discreteness, not zero sampling uncertainty.

The supporting structure, which must accompany that sentence rather than be
omitted as detail:

| configuration | −0.9429 | −0.8286 | −0.7714 | distinct values |
|---|---|---|---|---|
| uniform | 98.37% | 1.63% | — | 2 |
| clustered | 81.86% | 17.82% | 0.32% | 3 |
| sparse | 97.86% | 2.14% | — | 2 |

Uniform and sparse are degenerate only just: their second atoms sit at 1.63% and
2.14% against a 2.5% quantile threshold, so sparse is within 0.36 percentage
points of its upper bound moving to −0.8286. The **verdict** does not depend on
this — every atom in every configuration is far below zero, so the registered
rule passes under any of them — but the reported *width* does, and a reader
taking the interval as a precision claim would be misled. The intervals are
reported exactly as the frozen procedure produced them; widening them after
seeing their discreteness is precisely what preregistration exists to prevent.

**Disagreement is not monotone in dataset size.** In **14 of the 15**
seed-configuration curves it peaks at N=250 rather than falling throughout. The
exception is clustered seed 4, which peaks at N=500 with N=250 falling below
N=100. That curve is reported as observed — not smoothed, not rerun, not
supplemented with extra seeds — because investigating one development curve
after seeing it is post-result exploration. The gate passes because Spearman
tolerates exactly one inversion; substantive confirmation is left to the
untouched confirmatory seeds. This is a reliability result about the
*estimator*, not a test of H1.

## The failure threshold *(Schedule W4 Fri, D-103/D-107)*

A transition counts as a failure when its error exceeds one **global** threshold,
calibrated once and then frozen permanently. One threshold across all families —
never one per family or per withheld-feature schema — because family-specific
percentiles would mechanically normalise away genuine differences in failure
prevalence and would make the failure set partly a function of the construction
label, which is the leakage Plan §7.5 forbids arriving through the threshold
rather than through a feature column.

Calibration used well-fitted, fully observed reference models at n = 5,000, one
per stratum across the nine (layout, causal attribute) combinations, at five
seeds each: 45 cells, 225 fits, 4.3 minutes. The strata were balanced by
deterministic minimum-count subsampling without replacement, retaining
9 × 4,103 = **36,927** of 37,406 movement transitions (1.28% discarded to the
smallest stratum). The threshold is the **95th percentile** of the resulting
balanced error distribution, taken with an explicitly named quantile
method rather than a library default. How much that matters depends on the
vector: on one short probe vector the five NumPy methods returned 5.0, 7.0, 7.8,
9.0 and 9.0 — a spread of 1.8× — while on a smooth ten-point vector they span
only 9.00 to 10.00. The point is not the size of any particular gap but that a
permanently frozen constant must not inherit a library default that could change
between versions.

    FAILURE_THRESHOLD = 0.610702633857727

A transition fails when its error is **strictly greater** than this value; at
exact equality it does not fail. That is part of the definition rather than a
convention, and it is not academic — two transitions in the calibration pool
itself sit exactly at the value. The calibration ran once, into an immutable
attempt directory, and is never repeated: the threshold has been inspected, so
no later re-attempt could satisfy the invalidation protocol.

## A limitation: failure prevalence is not uniform across layouts *(D-108/D-109)*

The normalising scale is fixed to each evaluation pool, and evaluation pools
differ by layout. Under the frozen normalisation, failure prevalence in the
calibration evidence differs materially by layout:

| layout | prevalence |
|---|---|
| clustered | 8.77% |
| uniform | 4.68% |
| sparse | 1.58% |

a 5.53-fold spread behind a pooled rate of 5%. Stated at the limit of what the
evidence supports: *this establishes layout-conditioned base-rate heterogeneity
and raises a measurement-invariance limitation. The available aggregate
mean-error bounds do not identify how much of the tail difference is caused by
normalisation versus by differences in the underlying error distributions.*
Prevalence is an upper-tail probability, and bounds on mean error cannot explain
tail behaviour.

Nothing about the registered analysis changes in response. The failure
definition, the threshold, the scale rule and the primary endpoints stand.
Prevalence is reported by layout, causal attribute and seed alongside the pooled
result; layout-stratified H2 and H3 results are reported as **secondary
robustness diagnostics** and never redefine the failure set or replace the
primary weighting. Layout remains experimenter-only metadata: it is excluded
from the critic's inputs by the frozen feature whitelist. Layout does not
determine a layout-specific threshold and will not be used for later retuning,
label overrides, or post-hoc reweighting. Its only role in the frozen calibration
was as a preregistered balancing stratum for the single global threshold.

## What this design can and cannot detect *(Gate 1, D-078/D-089; D-098 as corrected by D-119/D-120 — condition 2 is NOT ADJUDICABLE, not PASS)*

Gate 1 asked four questions and the design **failed** the fourth, which is
recorded here rather than softened. The reliability gate passed and the
repair-acceptance test is calibrated against its permutation null. The compute
condition returned **no verdict**: the design's cost was measured — 5.72 median
/ 6.91 conservative-maximum **local wall-hours** — but the registered trigger is
denominated in **GPU-hours** on a device the study never used, and the two are
not adjudicable against each other (the deviation on execution host, below).
The condition is therefore recorded as **not adjudicable**, which is neither a
pass nor a failure, and Gate 1's failure rests on the fourth condition alone. But a diagnostic simulation of the scheduled
unit-weighted, paired H3 comparison, using a provisional Wald/normal rejection
approximation rather than the final H3 inference, produced optimistic
minimum-detectable differences of **18–22 percentage points** at the scheduled
held-out counts, against a registered equivalence margin of ±5.

Sample size remains the principal limitation across the tested dependence
assumptions. Zero intra-cluster correlation still gives an 18-point diagnostic
MDE; extremely strong pairing improves it to eight points, but neither the
scheduled sample nor any tested dependence assumption resolves five points.
Holding out all 300 units reaches six. A rough diagnostic extrapolation puts the
requirement on the order of 1,500–2,000 held-out units against the 60–80
scheduled — an approximate figure rather than a computed sample-size
requirement — and that expansion is incompatible with the registered scope.

One assumption of the simulation is itself a recorded deviation: the plan
fixes power at eighty percent but names no significance level, and the
simulation uses **α = 0.05, two-sided**, for consistency with every other
interval in the study — repair acceptance is a 95% interval excluding zero, and
the H1 trend statistic reports a 95% interval. A one-sided test would shrink
the diagnostic MDE by roughly 11% and change no conclusion.

The design therefore continues unchanged, under an explicit power limitation:
**H3 can detect only comparatively large differences and may be inconclusive
around ±5 points.** No equivalence claim will be made that the final interval
cannot resolve. The 18–22 figure is itself reported as a diagnostic rather than
an exact result, because the simulation's rejection rule is anti-conservative —
it uses a Wald interval where the registered analysis uses a group-bootstrap
percentile, with measured null rejection of 6.1–9.2% against a nominal 5% — so
the measured over-rejection indicates that the provisional diagnostic is
optimistic. **The final exact MDE is not yet known**; it awaits H3's final
group-level inference and validated null calibration. A study that
reports what it cannot resolve is a complete study; one that discovers the limit
after the fact is not.

## The remedy the plan mandated and the schedule repeated, and why it was declined *(DEV-010, D-089/D-115/D-119 — mandated)*

The plan mandates the remedy for exactly this situation: P§10.7 requires that
if the minimum detectable difference exceeds the five-point margin, *"the
configuration count is raised until it does not"*, so declining it is a
deviation from the plan. The schedule supplies the deadline —
*raise the configuration count now* — the
reasoning being that configuration count is machine time, while discovering the
shortfall in Week 15 costs the thesis. The count was **not** raised. That was a
deliberate, reviewed decision rather than an oversight, and it is recorded as a
deviation because declining a scheduled remedy is a design-relevant act.

The scale of the required expansion is what decided it. A **rough diagnostic
extrapolation** suggests a requirement on the order of **1,500–2,000 held-out
units**; this is *not* a computed sample-size requirement. The schedule holds
out 60–80 of 300, so preserving the scheduled held-out fraction gives an
approximate **5,625–10,000 total units, or an 18.75×–33.3× unit-count
extrapolation carrying no execution host**. Because it is a ratio of unit
counts, converting it
into hours and comparing the result against the registered compute trigger would
repeat, in prose, the cross-host comparison the previous section declines to
make. The refusal rests on two grounds, both of which survive the compute
measurement: the expansion is incompatible with the registered scope, and the
budget position rests on the registered GPU-hour design estimate together with
the scope decision — never on arithmetic across hosts. An expansion of that
order is not a larger version of this study; it is a different study.

The consequence is the stated power limitation, carried forward rather than
repaired: the study proceeds at its registered size, reports what it cannot
resolve, and treats an inconclusive H3 as a legitimate, reportable outcome.

## Where the results were produced *(DEV-011, D-116/D-119 — mandated)*

The plan's compute model names Kaggle **2× T4**, with a budget denominated in
GPU-hours and an escalation trigger near 120 (P§14.1; the per-fit estimate is
expressed on a single T4, which is what the source calculation describes). **Every fit in this study has in
fact run on a local CPU workstation, and no Kaggle job has ever been
submitted.** This is recorded as a deviation not because the local machine is
inadequate — the certified timing evidence puts the full design at **5.72
(median) to 6.91 (conservative maximum) local wall-hours** — but because a
compute claim inherits the host it was measured on. Local CPU wall-hours and
Kaggle GPU-hours are different quantities, and no verdict in this study compares
one against the other.

Two reproducibility consequences follow. First, every timing figure reported
here is a local wall-hour figure at a recorded thread count; thread count is
part of the record because it is **not numerically neutral** — re-running
certified cells at four threads instead of eight reproduced one cell exactly and
moved another by 0.19%, since floating-point reduction order differs. Second,
the timing evidence itself is provenance-bound: the certified record names the
exact source commit it ran from, required a clean tree before execution, and
carries a content digest verified independently in review.

## The exclusion-rate assumption *(DEV-012 — mandated)*

Ground-truth labelling can exclude a unit: a repair outcome can be *ambiguous*
(both repairs help, or the acceptance test cannot separate them) or
*undiagnosed* (neither does). The schedule asks for the configuration target to
be inflated by a **pilot** exclusion rate, with the assumption stated, and for
the first labelled batch to be checked against that assumption. No pilot
exclusion rate existed when the count was set: **no pilot-labelled units were
available, so no empirical exclusion rate existed**, and there was nothing to
inflate by.

The registered convention, ratified in review **before any real labels
existed**, is a planning assumption of **0.00**: the gross configuration target
is `ceil(300 / (1 − 0.00)) = 300`, with no anticipatory oversampling of either
class. This is a **zero-inflation planning convention, not an empirical
prediction that exclusion will be zero** — it is never described as observed,
estimated, or pilot-derived, because it is none of those things.

The convention is falsifiable at a scheduled checkpoint. The observed exclusion
rate is defined as **(ambiguous + undiagnosed) / all attempted labelled units**,
reported both pooled and by intended class; any observed exclusion above zero
means the planning assumption was missed, and the response is fixed in advance:
report the shortfall first, then draw replacements exclusively from the
predeclared reserve in its committed order, under its own authorisation gate.
Effective sample sizes for the critic are always reported as the surviving
`min(N₀, N₁)` after exclusions — never as the attempted total.

## The repair-acceptance test, and why it is not the registered mixed model *(DEV-009, D-094/D-100 — mandated)*

The plan specifies the acceptance test as a mixed-effects model (P§7.3, the
schedule repeating it) — per-transition error, a fixed effect for the repair,
random intercepts for seed and for episode within seed — with an episode-mean
fallback for when the nested fit is unstable. The deviation is therefore from
the plan, not merely from a schedule cell.
The implemented test is neither of those. It is an **equal-seed mean paired
difference with a t interval on `n_seeds − 1` degrees of freedom, and no
fallback**.

The change was made because the literal specification was found **degenerate**
for this design. Every repair is evaluated on the *same recorded failure set* as
its unrepaired baseline, at the same seeds, so the comparison is paired
per transition within seed by construction. A model with random intercepts for
seed and episode does not charge for that pairing — it treats the two arms as
exchangeable draws sharing a grouping structure, which discards exactly the
dependence the design creates on purpose. The paired difference uses it directly.

Removing the fallback matters more than replacing the model. A fallback that
substitutes a different estimator when the primary one fails to converge makes
the reported method a function of numerical luck: two conditions could be
analysed by two different tests, and nothing in the output would say which. The
implemented test **fails closed** instead — if the paired arrays cannot be
assembled, or any per-seed error is non-finite, it raises rather than degrading
to a second method.

Both changes were authorised as amendments to the preregistration **before any
data was seen**, which is the only circumstance in which a registered analysis
choice may move. The acceptance criteria themselves are untouched: a negative
effect, a 95% interval excluding zero, and at least a 20% relative reduction in
mean per-transition error, all three required.

## One unit, several roles: why the Experiment 2A conditions are not extra units *(Schedule W2 Wed, D-007 — mandated)*

Experiment 2A varies the confound rate at four non-zero levels, and the same
configuration-conditions also appear in the broader configuration sweep. The
schedule requires a recorded decision on whether these are the *same* units run
more intensively, or *additional* units. They are the same units.

The reason is that a configuration-condition must have exactly one identity. If
a unit were counted once as an Experiment 2A condition and again as a sweep
condition, the effective sample size behind every confidence interval would be
inflated by the duplication — the two entries are not independent observations,
they are the same environment specification written down twice. The registered design contains 75
canonical units, including 20 Experiment 2A units, plus 225 non-canonical sweep
units, for 300 distinct units. Treating the entire 300-unit sweep as additional
to all 75 canonical units would produce the erroneous total of 375; duplicating
only the 20 Experiment 2A units would produce 320. Either way, every interval
computed on the inflated count would be too narrow.

Running them at a higher seed count is the correct expression of their extra
importance: additional repeated measurements strengthen the estimate *for those
units* without manufacturing new labels. Seed count is therefore a property of a
unit's **role** — five seeds for a unit entering an H1 or H2 claim, three for a
sweep-only unit, twenty for canonical repair validation — rather than a property
of a separate run list. Where one unit carries several roles, the roles share one
set of fits; they do not each commission their own.

This is enforced structurally rather than by convention. The unit identifier is a
content hash of the preregistered configuration fields, so two descriptions of
the same configuration collide by construction and cannot be distinguished by
naming. The enumerator deduplicates on it, and the sweep draws only from the
matrix *minus* the canonical units. The arithmetic closes: 75 canonical
configuration-conditions — of which 20 are the Experiment 2A conditions — plus
225 drawn for the sweep, giving exactly 300 distinct units, which is the
registered target. The plan's own run-count table agrees, which is the check that
matters: had the 2A conditions been additional, the plan's budget and its stated
target would not have reconciled.
