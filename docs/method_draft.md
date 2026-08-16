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

## What the first curves look like *(Schedule W3 Sat — written before any formal test)*

Six dataset sizes, three development seeds, one configuration (shape-causal,
uniform layout, no confound). Metrics on the fixed evaluation pool, movement
transitions only, per-dimension normalised. **Three seeds cannot support H1**;
the schedule calls this cell a look, and the trend test is Week 4 Monday.

| N | held-out error | mean pairwise disagreement | ratio |
|---|---|---|---|
| 100 | 1.302 ± 0.026 | 0.601 ± 0.110 | 0.462 ± 0.082 |
| 250 | 0.816 ± 0.195 | **0.815 ± 0.064** | 1.025 ± 0.178 |
| 500 | 0.571 ± 0.023 | 0.550 ± 0.044 | 0.963 ± 0.039 |
| 1,000 | 0.421 ± 0.020 | 0.416 ± 0.015 | 0.990 ± 0.072 |
| 2,500 | 0.302 ± 0.009 | 0.269 ± 0.016 | 0.889 ± 0.034 |
| 5,000 | 0.263 ± 0.007 | 0.213 ± 0.013 | 0.810 ± 0.041 |

**Error falls monotonically with dataset size.** That is the least interesting
line here and the one most expected.

**Disagreement does not.** It rises from N = 100 to N = 250 and falls thereafter.
The peak is not a seed artefact: the N = 250 standard deviation is smaller than
the gap, and the same non-monotonicity appeared in an independent earlier probe
at a different hidden size.

**The mechanism, measured rather than guessed.** At N = 100 the ensemble's mean
prediction has a standard deviation of 0.065 against the targets' 0.220 — 29% of
the variation in the thing it is predicting. By N = 5,000 that ratio is 96%. At
the smallest condition the members have not learned different wrong answers;
they have all collapsed toward the *same* near-constant. They agree because
there is nothing yet to disagree about.

**Why this matters more than the shape of one curve.** High error with low
disagreement is the H2 signature — the pattern the thesis proposes as evidence
of hypothesis-class failure. Here it is produced by an *estimation* failure, in
a condition where the model class is entirely adequate and more data demonstrably
fixes the problem. The disagreement-to-error ratio is **lowest at N = 100
(0.462)**, lower than at any other dataset size and lower than the large-data
conditions where the model is nearly correct.

If that survives replication at five seeds and confirmatory data, it does not
falsify H2, but it bounds it: the ratio would not discriminate failure types at
the extreme of estimation failure, and any critic trained on such conditions
would be learning a signature that points both ways. The honest reading is that
severe under-training and structural misspecification are not distinguishable by
ensemble disagreement alone — which is, if anything, a sharper statement of the
problem this thesis exists to address than the one in the introduction.

Two things follow for the schedule rather than for the thesis. The Week 4 Monday
trend test must be read knowing the curve is non-monotone at the small end; and
Week 5's minimum-detectable-effect simulation should be told which conditions
sit in the collapsed regime, because they carry a different disagreement
mechanism from the rest of the sweep.

*Figures:* `figures/w3_error_vs_data.png`, `figures/w3_disagreement_vs_data.png`.

