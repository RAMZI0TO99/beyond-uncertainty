# Method — the student's own-voice rewrite

**How this file is produced (method recorded for Sol in delta 57):** for each
section, Claude asks simple questions in chat; the student answers **in their
own words**; Claude assembles the section *from those answers* — keeping the
student's phrasings where they are right, correcting facts against the ledger,
adding the frozen numbers with their estimands — and the student reads and
confirms each section before it is marked accepted. Every section carries its
source answers below it, verbatim, as provenance of whose voice it is.

**Status: §1–§11 CONFIRMED by the student (2026-08-23). §12 and §13 drafted — awaiting student confirmation.**

---

## 1 · Why the environment looks like it does *(W1 Thu — CONFIRMED by the student 2026-08-23; replaces `method_draft.md` §1)*

The environment is a small gridworld, and the simplicity is a choice, not a
shortcut. A simple world gives us quick results: one world model trains in a
few seconds on an ordinary CPU, and the full design needs thousands of such
fits, because every failure condition is labelled by training extra repair
models. That labelling protocol is only affordable when a single training run
is cheap.

More important, a simple world is a world we can control. We wrote its rules,
so we know exactly what the model is supposed to learn, and we can cause each
failure type on purpose instead of waiting for it to appear. A world model can
fail for two different reasons. Sometimes it has not seen enough data — with
more data it recovers. Sometimes its tools are wrong: the model class cannot
represent the rule at all, for example because the one feature the rule depends
on is hidden from its inputs, and then no amount of extra data will ever fix
it. These two failures need opposite repairs, and telling them apart is the
point of this thesis.

The label that says which failure a condition really has is not guessed from
the model's behaviour. Instead of guessing, we test both repairs and see their
results: the data repair and the model-class repair each run separately, and an
acceptance test decides which one actually worked. If both work, the condition
is called ambiguous and is excluded rather than forced into a class. Running
repairs for every condition is only possible because the environment is small
enough to retrain many times.

The observation is factored — each attribute of each object is a separate
input feature — so that we can control the features and hide exactly one of
them on purpose. That clean switch is how the wrong-tools failure is
manufactured: the model is denied exactly the attribute the rule depends on.

One episode looks like this. A grid contains objects, and every object has
fixed attributes — a shape and a colour — that never change; some objects
block movement, depending on those attributes. The agent moves through the
grid and has one extra action, `interact`, which toggles the activation of an
object standing next to it — but only when the object satisfies a rule that
depends on one specific attribute, for example "only triangles can be
activated". Which attribute matters is a setting of the configuration, and it
is exactly what the world model must discover from data. The agent itself
never learns: a fixed scripted policy chooses its actions and only collects
experience. The learner is the world model, which must predict the agent's
next position after a move and any activation change after an `interact`.

**Source answers (student, 2026-08-23, verbatim):**
> 1- the simplicity gives us quick results and something we can build over to more complex systems.
> 2- if the agents dose not see enough data it fails or makes a mistake. if i uses the wrong tools as well.
> 3- insted of gussing we test both and see their results and see how will they do and if could work togather.
> 4- so we can control the featuers and hide things from the agnet so i can learn from mistakes.
> 5- the system teaches the agent to learn when to look for more data or use other tools when he fails.

**Corrections applied against the ledger:** "build over to more complex
systems" moved out — a generalisation claim the methodology must not make
(future-work material). "The agent learns" corrected: the agent never learns —
the scripted policy collects (D-020, D-051), the **world model** learns
(D-032), the **critic** diagnoses. "See if they could work together"
corrected: repairs run separately, and both-working is the **ambiguous**
exclusion (P§7.4), not a success case.

---

## 2 · The configuration axes, and why there are 300 of them *(W2 Thu — CONFIRMED by the student 2026-08-23; replaces `method_draft.md` §2)*

The study is not looking for one best configuration. Each configuration —
called a *unit* — changes a few settings on purpose: how much data the world
model gets, how the objects are laid out in the grid, which feature (if any) is
hidden from the model, how large the model is, and how strongly a misleading
decoy attribute imitates the true rule. Every unit is set up so that one
failure type should appear in it: either the not-enough-data failure or the
wrong-tools failure.

The reason there are many units is that **the units themselves are the data of
this thesis**. Each unit ends with one label — which repair actually worked —
and the critic has to learn from these labelled examples and then be judged on
examples it has never seen. One configuration would be one data point; no
classifier can be trained or fairly tested on a handful of points. Three
hundred units give the critic enough variety to learn from and enough held-out
examples to be judged on honestly.

We did not run every possible combination of settings. The full crossing of
all the axes would be far larger, and most of those combinations would repeat
the same lesson at higher compute cost. Instead the design draws a **balanced
sample** from the crossing: every axis is covered fairly, and the two intended
failure classes are kept at 150 units each.

That 150/150 balance is not decoration. The critic is a classifier with two
possible answers, and if one class dominated — say 270 data-failures and 30
tool-failures — a useless critic that always answers "more data" would look
90% right while diagnosing nothing. Keeping the classes balanced, and scoring
with balanced accuracy, makes that cheat impossible.

Some units will still turn out unusable: the acceptance test can find that
both repairs work (*ambiguous*) or that neither does (*undiagnosed*), and such
units are excluded — they might fail to do what we need. For that case a
replacement list exists, drawn up and committed **before any result was
seen**. The order is fixed in advance for one reason: if we picked
replacements after seeing results, we could — even without meaning to — choose
units that flatter the hypothesis. A choice made before the data exists cannot
be bent by the data. The same principle runs through the whole thesis: the
thresholds, seed rules and test rules are all frozen in one file before use.

**Source answers (student, 2026-08-23, verbatim):**
> 1- so we can test how much change is good. it is not a fixed number or best configurations.
> 2- i do not know? tell me what we did and write it.
> 3- because we are testing both methods and we want to see which is better.
> 4- because they have not been tested yet. and they might fail to do what we need.

**Provenance notes:** "not looking for one best configuration" and "they might
fail to do what we need" are the student's, kept. The balanced-sample
explanation (paragraph 3) is Claude's, supplied at the student's explicit
request ("i do not know? tell me what we did") and recorded as such (D-018).
**Corrections applied:** Q1 — many units exist because they are the critic's
labelled examples, not to "test how much change is good"; Q3 — the half/half
balance is about fair classification (a dominant class lets a useless critic
score high), **not** about comparing the two repair methods against each other
— repairs are not competitors, each unit has one true label (D-031, D-044);
Q4 — the reserve is predeclared **so replacements cannot be cherry-picked
after seeing data** (D-092); "not tested yet" is why a reserve *exists*, not
why its order is fixed in advance.

---

## 3 · How the data is collected, and why the collector is a script *(W2 Sat — CONFIRMED by the student 2026-08-23; replaces `method_draft.md` §3)*

The world model learns from transitions: the agent was here, it did this, and
that happened next. The collector's only job is to produce transitions that
show the world well. There is no task to win and no reward to chase in this
study — the agent does not have to be clever, it has to be *everywhere*. It
must visit all parts of the grid, walk into things, and press `interact` next
to objects of every kind, because the model can only learn what the data lets
it see. A fixed script that wanders and pokes at everything does this job.

The original plan named PPO, a learning policy, as the collector. We replaced
it with the script, and the reason is the experiment's most important axis:
dataset size. The study compares world models trained on 100 transitions
against models trained on up to 5,000, and calls a failure *estimation
failure* when more data repairs it. That test is only clean if a big dataset
is the same kind of data as a small one — just more of it. A learning
collector changes its own behaviour while it collects: its early transitions
come from random wandering, its later ones from a confident routine. More data
would then also mean *different* data, and an improvement could no longer be
credited to the amount alone. The script behaves the same way in every
episode, so size is the only thing that changes between conditions.

We did not simply claim that the script explores well enough — the claim is
backed with real tests and results: coverage was measured, not asserted. And
when the script was later corrected — an early version changed slightly across
episodes, exactly the problem described above in miniature — every measurement
taken under the old version was declared void and re-measured under the fixed
one. A claim is only worth the setup it was measured on.

**Source answers (student, 2026-08-23, verbatim):**
> 1- i do not know why ?
> 2- also dont know.
> 3- because it can be backed with real tests and results.

**Provenance notes:** paragraphs 1 and 2 are Claude's explanations, supplied
after two honest "don't know"s and recorded as such (D-020, D-051, D-052); the
student was taught the content in chat before confirming. "Backed with real
tests and results" is the student's, kept in paragraph 3. The void-and-remeasure
sentence is the D-051 event (pre-D-051/D-052 numbers are void and are never
quoted).

---

## 4 · What the re-measured evidence can and cannot say *(D-051/D-054 — CONFIRMED by the student 2026-08-23; replaces `method_draft.md` §4)*

After the collector script was corrected, its evidence was measured again from
scratch. One of the new measurements looked for drift across episodes and
found none worth reporting — about one standard error, in a direction that
favours nothing. We recorded that measurement as **consistent with** stable
episodes, and deliberately not as proof of them.

The reason is simple: a test might pass while there are hidden things it
cannot see. A drift test that finds nothing has only shown that *this* test,
at *this* sensitivity, saw nothing — the drift could be smaller than the test
can detect, or live somewhere the test does not look. A null result never
proves the null. So wherever a property is true *by construction* — the
script is literally the same object in every episode — we state and check the
construction itself, and let the measurement be supporting evidence rather
than the foundation.

**Source answer (student, 2026-08-23, verbatim):**
> 1- because the test maight pass but there is are hiden things from it.

**Provenance notes:** the student's answer is the core of paragraph 2, kept
nearly verbatim ("a test might pass while there are hidden things it cannot
see"). The structural-property rule is D-054's.

---

## 5 · What the first curves look like, and why they are not a result *(W3 Sat — CONFIRMED by the student 2026-08-23; replaces `method_draft.md` §5)*

At the end of Week 3 we drew the first pictures of the system working. They
showed what we hoped to see: prediction error falls as the dataset grows, and
the members of an ensemble agree with each other more as data increases. It
is tempting to call that an early confirmation of Hypothesis 1. We did not,
for two reasons.

First, the seeds. Those curves were made with development seeds — the ones we
were free to look at while building and debugging. The confirmatory seeds,
numbered from 1000 upward, had never been touched, and they are the only
seeds the registered tests are allowed to use. Data that was looked at while
the system was being shaped cannot also be its judge, the same way a student
cannot be graded on the practice problems they studied from.

Second, the rule. At the time the curves were drawn, the formal reading rule
for Hypothesis 1 — which statistic, which direction, what counts as a pass —
had not yet been frozen. A curve without a pre-committed rule is a picture,
not a result. The rule was frozen afterwards, before the gate that used it
ran, precisely so that nobody could bend the rule around a curve already
seen. Changing things after peeking, and then testing them, is not an
approach — it is the mistake the whole preregistration discipline exists to
prevent. So the Week 3 curves stand in this thesis as description only.

**Source answers (student, 2026-08-23, verbatim):**
> 2- i  do not know.
> 3- the formal test tests more and changeing tihngs before testing them is not a good aporutch.

**Provenance notes:** the seeds explanation (paragraph 2) is Claude's, after
an honest "don't know", taught in chat before confirmation (D-034). The
student's answer 3 is the seed of paragraph 3's closing ("changing things
before testing them is not an approach"), refined; the frozen-rule fact is
D-068.

---

## 6 · The normalising scale, and why it is fixed before anything is marked *(D-061/D-076 — CONFIRMED by the student 2026-08-23; replaces `method_draft.md` §6)*

Errors from different configurations are not directly comparable. A large grid
produces larger position mistakes than a small one simply because there is
more room to be wrong, and different prediction dimensions have different
natural sizes. Before any comparison, each error is divided by a per-dimension
scale, so the scales are normalised and the numbers become comparable — the
same idea as converting two exam marks, one out of 20 and one out of 100, to
percentages before deciding which student did better.

Where that scale comes from is a registered decision, not an implementation
detail. The scale is computed from the **full evaluation pool**, before any
transition has been marked as a failure, and the identical scale object is
then reused for every statistic that follows — the whole-pool numbers and the
failure-only numbers alike.

The reason is circularity. A transition is called a failure when its
*normalised* error exceeds a fixed threshold, so the failure set is defined
using the scale. If the scale were then recomputed from the failures alone, it
would depend on the very selection it was used to make, and the threshold
would quietly mean something different in every subset — a moving ruler used
to measure the thing that moved it. Fixing the scale first breaks the loop,
and it is the same discipline as the sealed seeds and the predeclared reserve:
the quantity is settled before the data can influence it.

This is enforced by construction rather than by care. The routine that builds
a scale from a pool accepts no failure mask at all, so a subset-derived scale
cannot be requested, and the masked view reuses the identical object it was
built from. The ordering is not something a future user has to remember —
it is the only thing the code allows.

**Source answers (student, 2026-08-23, verbatim):**
> 1- so the sacles are normalized and become compaerable.
> 2- i do not know.

**Provenance notes:** the student's answer 1 is paragraph 1's core, kept
("so the scales are normalised and the numbers become comparable"). The
circularity argument (paragraph 3) is Claude's after a recorded "don't know",
taught in chat before confirmation (D-061, wording corrected by D-064;
enforced structurally by D-076).

---

## 7 · What the error is, and what it is not *(DEV-007/D-032/D-047 — CONFIRMED by the student 2026-08-23; replaces `method_draft.md` §7)*

The world model predicts only what can change. In this environment an object's
shape and colour are fixed for the whole episode: nothing any action does will
ever alter them. They are therefore copied straight from the current
observation into the predicted next one, and they never enter the training
loss.

Asking the model to *predict* them instead would be worse than merely
pointless. Those outputs are correct for free — copying the input scores
perfectly — so they would inflate the model's apparent accuracy while teaching
it nothing, and a model that looks accurate for a trivial reason hides the
dynamics errors this study exists to measure. The failure we care about must
show up in the score, not be diluted by a large block of guaranteed wins.

The same argument decides how the two real predictions are scored. Each action
changes only certain things: a movement can change the agent's position but
never toggles an object's activation, and an `interact` can toggle an
activation but never moves the agent. So the position error is measured on
movement steps and the activation error on `interact` steps, each on the
transitions where that quantity is actually at stake. Scoring position on an
`interact` step would be marking the model for predicting that nothing moved —
true by construction, and free marks again.

The primary error for the whole study is the one that follows from this: the
error in the predicted next agent position, over movement transitions,
per-dimension normalised. The activation prediction remains a diagnostic and
is deliberately kept out of every decision — it does not train the shared
trunk, does not influence early stopping or model selection, and plays no part
in defining failures, labels or the critic's inputs.

**Source answers (student, 2026-08-23, verbatim):**
> 3- i do not know.
> 4-so see what happens when interation is used and when movements is changed.

**Provenance notes:** answer 4's instinct — that the two actions do different
things and should be looked at separately — is paragraph 3's argument,
sharpened to the registered reason (each action can only change certain
quantities, so scoring elsewhere marks a free win). Paragraph 2 is Claude's
after a recorded "don't know", taught in chat (D-032; the rejected full-delta
target). The diagnostic-only status of the activation head is D-047/D-063.

---

## 8 · Why hiding position is a different experiment *(DEV-006/D-026 — CONFIRMED by the student 2026-08-23; replaces `method_draft.md` §8)*

Experiment 2A manufactures the wrong-tools failure by hiding from the model
exactly the attribute the rule depends on. Hiding shape or colour does this
cleanly: the model still sees the whole scene and knows where everything is,
it simply cannot tell which objects satisfy a rule it can no longer express.
The failure is that the rule is unrepresentable, which is the failure the
experiment is about.

Hiding *position* is not the same thing, and the difference is not a matter of
degree. Position is not one property of a visible object — it is what tells
the model that an object is there at all. Remove it and situations that are
genuinely different start to look identical in the data: the same observation
and action now correspond to more than one true outcome. Measured, **37.5% of
(observation, action) keys are aliased when position is withheld, against
10.0% for shape and colour**, in a key space **26× smaller**.

A model in that condition is not failing because the rule cannot be written
down; it is failing because it cannot tell two different situations apart. That
is a different structural failure, so position-causal conditions are not
counted among the five canonical Experiment 2A configurations. They still run,
as a declared robustness configuration in the three-seed sweep, and are
reported as such. The point of recording this as a deviation is to bound the
claim: Experiment 2A's result is a result about withheld *attributes of visible
objects*, and the measurement that justifies the boundary is reported beside
it.

**Source answer (student, 2026-08-23, verbatim):**
> 1- because they are not the same thnig. i think. i do not really get it.

**Provenance notes:** the student identified correctly that the two cases are
not the same but could not say why; the aliasing explanation is Claude's,
taught in chat before confirmation, with the 37.5% / 10.0% / 26× measurement
from DEV-006 and D-026 quoted rather than paraphrased.

---

## 9 · The reliability gate, and what its intervals really say *(W4 Tue, D-074/D-075 — CONFIRMED by the student 2026-08-23; replaces `method_draft.md` §9)*

Before Hypothesis 1 could be tested at all, the machinery had to be shown to
work: does ensemble disagreement actually fall as the dataset grows, in a way
the registered statistic can read? The gate answers that question on three
predeclared layouts — uniform, clustered and sparse — with five development
seeds each, and it passed on all three, at the first rung of a difficulty
ladder that was then correctly stopped: 90 ensembles, 450 model fits, 4
minutes 52 seconds on CPU.

The reasoning behind the statistic is the reasoning behind Hypothesis 1. When
the members of an ensemble disagree with each other, it means the data did not
pin the answer down: several different models fit what was seen equally well,
and the disagreement is what is left over. Give the model more data and the
possibilities narrow, so disagreement should fall. Spearman's rank correlation
between dataset size and mean disagreement was **−0.9429** in all three
configurations — identical because the statistic reads ranks only, and all
three mean curves share the same rank pattern.

Two of the three reported intervals are a single point, `[−0.9429, −0.9429]`,
and that must never be presented without its explanation:

> Exact paired seed-block bootstrap percentile intervals were computed over all
> 3,125 resamples. Because Spearman correlation over six dataset sizes has
> highly discrete support, the bootstrap distributions contained only two or
> three distinct values. A zero-width percentile interval therefore reflects
> quantile discreteness, not zero sampling uncertainty.

The atom table belongs with that sentence, because it shows how narrowly the
width is decided: the uniform distribution puts 98.37% of its mass on −0.9429
and 1.63% on −0.8286, sparse 97.86% and 2.14%, against a 2.5% quantile
threshold — sparse is within 0.36 percentage points of its upper bound
flipping. The verdict does not depend on this in the slightest, since every
atom in every configuration lies far below zero, but the reported *width*
does, and a reader taking a zero-width interval as a precise estimate would be
misled.

Two honesty notes travel with the result. Disagreement is **not** monotone in
dataset size: in 14 of the 15 seed-configuration curves it peaks at N=250
before falling, and the gate passes because the registered statistic tolerates
exactly one inversion. The exception, clustered seed 4, peaks at N=500 with
N=250 below N=100; it is kept and reported exactly as observed, not smoothed,
not rerun, and not investigated — doing so now would be exploring after seeing
the result, and confirmation waits for the untouched confirmatory seeds.

And the gate is not the hypothesis. It ran on development seeds, below the
confirmatory line at 1000, so it establishes that the estimator behaves as
registered — not that Hypothesis 1 is true. That verdict is taken later, on
seeds nobody has looked at.

**Source answers (student, 2026-08-23, verbatim):**
> 2- that the data was contradeted.
> 3- we have not tested it on high seeds(>1000).
> 4- because it could be that there is a hiden error or somthing we mised.

**Provenance notes:** answer 3 is correct and is paragraph 6's content in the
student's own understanding. Answer 2 is corrected: disagreement means the data
**underdetermined** the answer — several models fit it equally well — rather
than that the data was contradictory (D-069/D-074). Answer 4's suspicion is
right in spirit but the actual cause is specific and is Claude's: the bootstrap
has only two or three atoms because a rank correlation over six points has very
coarse support (D-075, whose wording Sol required verbatim and which is quoted
above as a block).

---

## 10 · The failure threshold *(W4 Fri, D-103/D-107 — CONFIRMED by the student 2026-08-23; replaces `method_draft.md` §10)*

Everything downstream of this section depends on one number. A transition is
called a *failure* when its normalised prediction error is **strictly greater
than 0.610702633857727**. Every failure set is built with that line, every
repair label is assigned by testing repairs on those failure sets, and
Hypotheses 2 and 3 are claims about those labels. It is the most irreversible
quantity in the study, and it is permanently frozen.

The line is calibrated on **healthy** models, not broken ones, because its job
is to say what abnormally bad looks like — and "abnormal" is only meaningful
against a reference of normal. The reference models are fully observed,
trained on the largest dataset size with no confound: models given every
chance to be right. Their errors are what this environment looks like when
nothing is wrong, and the threshold is the 95th percentile of that
distribution — the worst 5% of healthy behaviour. Calibrating on broken models
instead would define failure relative to failure: the worse the reference, the
higher the line, and the fewer failures anything would appear to have.

The calibration was run once. Nine strata — layout crossed with causal
attribute — at five seeds each, 225 model fits at n=5,000, about four minutes
on CPU. The strata were weighted equally by deterministic subsampling without
replacement to the smallest stratum's count, giving 9 × 4,103 = 36,927 of
37,406 transitions, so that no layout could dominate the reference simply by
contributing more data. Applying the rule to the unbalanced pool instead gives
5.02% failures against the 5% the balanced pool has by construction — a sanity
check that the strata are not wildly different in the upper tail, reported as
a check and not as a criterion.

The threshold may never be re-tuned, and the reason is one the student put
plainly: changing it would change a great many results that accumulate on top
of it. Because failure sets feed repair labels, and repair labels feed the
critic, a later adjustment would not simply move one number — it would
silently redefine every label in the study. But the stronger reason is the one
that governs the whole design: a quantity that can be adjusted after seeing
results can be adjusted, however unintentionally, toward the result one hopes
for. The threshold was therefore fixed before its consequences were known, its
calibration run given exactly one attempt with the preconditions checked
first, and its value verified independently in review — the reviewer
re-extracted the stored evidence, checked every artefact digest, and recomputed
the percentile to a bit-identical floating-point value. There is no longer a
procedure by which the number could be legitimately replaced.

One detail of the definition is not a formality. The comparison is **strictly
greater**: a transition whose error is exactly equal to the threshold is *not*
a failure. That has to be written into the registered definition rather than
left to whoever implements it, because **two transitions in the calibration
pool sit exactly on the value**. The boundary rule therefore decides the label
of real data. A specification that left it implicit would produce different
labels depending on which implementation, or which reading of the
specification, happened to be followed — which is precisely the failure the
preregistration file exists to prevent.

Finally, the number is meaningless without saying what it is a percentile
*of*. Reported in full, it is: the 95th percentile (`method="linear"`) of
ensemble-mean, per-dimension-normalised agent-position error over movement
transitions, from five-member ensembles of fully observed reference models
trained at n=5,000 with no confound, pooled across nine layout × causal-
attribute strata at confirmatory seeds 1000–1004, equally weighted by
deterministic minimum-count subsampling at RNG seed 0.

**Source answers (student, 2026-08-23, verbatim):**
> 1- so they can have real reuslts rather than broken.
> 2- because it will cahnge alot of results that are acoumalive.
> 3- beacuse we must defain the failuer line before.

**Provenance notes:** answer 2 is the student's own insight and is stated as
theirs in paragraph 4 — the cascade from failure sets to labels to hypotheses
is exactly right, and it was not prompted. Answer 1 is correct in direction and
was sharpened to the reference-of-normal argument. Answer 3 has the right
principle; the specific boundary reasoning — that two real transitions sit on
the value, so the strict rule decides actual labels — is Claude's, from
`constants.py` and D-107.

---

## 11 · A limitation: failure is not spread evenly across layouts *(D-108/D-109 — CONFIRMED by the student 2026-08-23; replaces `method_draft.md` §11)*

The threshold is one global number, but it does not mean one thing everywhere.
Measured across the nine calibration strata, the proportion of transitions
called failures ranges from **1.58% to 8.77%** — a **5.5-fold** spread, ordered
systematically by layout: clustered lowest, then uniform, then sparse. This is
reported because it is a finding, and nothing here is hidden merely because it
makes the design look less tidy.

The measurement is reported without an accompanying explanation, and the reason
is worth stating openly, because an earlier version of this section did offer
one. It claimed the spread was mostly an artefact of the per-dimension
normalising scale. In review that claim was withdrawn while the numbers were
confirmed, and the fault was not arithmetic. The evidence offered was about
the *average* size of errors in each layout; prevalence is a statement about
the *upper tail* of the error distribution. Overlapping bounds on averages
cannot establish why tails differ, so the evidence could not reach the claim it
was made to support. A measurement is a fact that can be re-derived from stored
artefacts; an explanation is a causal claim, and it needs evidence aimed at the
thing being explained. So the honest report is what was measured, plus the
explicit statement that the mechanism behind it is not established here.

Two smaller lessons from the same correction are carried into the reporting
rules. A prevalence figure has to name how it was aggregated — pooling all
rows and averaging the per-cell rates are different quantities, and the first
version of this analysis mixed the two without naming either; both are now
reported and labelled. And a per-dimension scale is a vector, not a single
number: collapsing it to one figure per layout made the layouts look cleanly
separated when, reported honestly as per-dimension ranges, two of them overlap.

The consequence for the analysis is a set of registered rules rather than a
change to the design. The failure set is not redefined and the registered
primary weighting is not replaced. Layout-stratified estimates for Hypothesis 2
are reported as a secondary robustness diagnostic, and for Hypothesis 3
balanced accuracy and confusion behaviour are reported both overall and
separately by layout. The student's own reading of the risk is the right one:
if failures are far more common in some layouts than others, the labelled
material can end up leaning on a subset of layouts rather than representing all
of them — so the layout breakdown is reported alongside the headline number,
where a reader can see it.

**Source answers (student, 2026-08-23, verbatim):**
> 1- it is a finding we are not going to hide anything.
> 2-we just need to show the findings . right?
> 3-to count on one layer rather than all layers.

**Provenance notes:** answer 1 is the section's opening principle, kept in the
student's terms. Answer 3 is correct in substance — the risk of leaning on a
subset of layouts — and drives the closing paragraph; it was unprompted.
Answer 2 was tentative and is sharpened: the distinction is not that findings
should be shown, but that a **measurement** can be re-derived from stored
evidence while an **explanation** is a causal claim needing evidence aimed at
the quantity it explains (D-108, withdrawn by D-109; the aggregation and
vector-scale lessons are D-109's).

---

## 12 · What this design can and cannot detect *(Gate 1 — replaces `method_draft.md` §12 when confirmed)*

Gate 1 was a scheduled checkpoint asking whether the study was fit to
continue. It put four questions, and the design **failed the fourth**, which
is recorded here rather than softened.

The reliability gate passed. The repair-acceptance test is calibrated against
its permutation null. The compute condition returned **no verdict at all**:
the design's cost was measured at 5.72 median and 6.91 conservative-maximum
**local wall-hours**, but the registered budget is denominated in **GPU-hours**
on a device this study never used, and those are different quantities. The
condition is therefore recorded as **not adjudicable across hosts** — neither
a pass nor a failure — and Gate 1's failure rests on the fourth condition
alone.

That fourth condition asked whether the design can resolve a five-percentage-
point difference in balanced accuracy, which is the margin Hypothesis 3 is
stated against. It cannot. The smallest difference the design can reliably
detect is **18 to 22 percentage points**. The instrument works — it is simply
too coarse for the question: like a scale that weighs correctly but only in
twenty-kilogram steps, it will register a large change and cannot see a small
one. The study is doing well at what it does; it is not sensitive enough for
the difference that matters.

Three things make that number trustworthy as a limitation rather than a
guess. First, the shortfall is driven by **sample size**, not by uncertain
assumptions: even with no correlation between related units at all — the
parameter least knowable before data — the detectable difference is still 18
points. Second, every available lever was tested and none closes the gap:
strong pairing between critic and baseline reaches eight points, and holding
out *all three hundred* units reaches six. Third, the estimate is
**optimistic**, so the true limitation is worse. The simulation uses a
provisional normal-approximation rejection rule rather than the interval the
registered analysis will use, and that rule over-rejects — a measured false-
positive rate of 6.1–9.2% against a nominal 5%. A significance level of
α = 0.05, two-sided, is itself a recorded deviation, since the plan fixes
power but never named one.

Two statements of scope keep this honest. The figure is reported as a
**diagnostic**, not as an exact result: no exact minimum detectable difference
will be quoted until the simulation uses the same final inference Hypothesis 3
is tested with and its false-positive rate is validated. And comparing a
detectable difference against the five-point margin is a **necessary
sensitivity check, not an equivalence test** — the two share units, so a
detectable difference above five points does mean the study cannot resolve
that region, but the reverse would not follow: a figure below five would not
by itself establish adequate power.

The design therefore continues unchanged, under an explicit and pre-registered
power limitation: **Hypothesis 3 can detect only comparatively large
differences and may be inconclusive around ±5 points.** No equivalence claim
will be made that the final interval cannot support.

**Source answers (student, 2026-08-23, verbatim):**
> 1- it is doing good but not enough
> 2- because it will save alot of time and effort
> 4-i do not know.

**Provenance notes:** answer 1 is paragraph 3's closing sentence, kept in the
student's terms and sharpened with the coarse-scale image. The four-condition
account, the anti-conservatism, and the diagnostic/equivalence scope
statements are Claude's from D-078, D-082, D-089 and D-098. **Note for the
student:** D-098's signed gate record still reads *"condition 2 · compute ·
PASS"* because gate records are append-only; it was corrected to *not
adjudicable* by D-119 and D-120, and the corrected value is the one used here.

---

## 13 · The remedy the schedule prescribed, and why it was declined *(DEV-010 — replaces `method_draft.md` §13 when confirmed)*

The schedule anticipated this exact situation and gave an instruction: if the
detectable difference does not clear five points, **raise the configuration
count now**, because discovering the shortfall in Week 15 costs the thesis.
The count was not raised. That was a deliberate, reviewed decision, and it is
recorded as a deviation because declining a scheduled remedy is a
design-relevant act rather than an omission.

Finding the limit in Week 4 rather than Week 15 is what made a considered
decision possible at all, and this is the schedule's own reasoning. A
limitation discovered early can be measured, reported, and planned around: the
scope of the claim is set before the results exist, and the reader is told what
the study can and cannot resolve as part of its design. The same fact
discovered after all the data was collected would arrive as an excuse for a
disappointing result, indistinguishable from one — and by then no remedy would
be available at all. Early discovery converts a potential embarrassment into a
stated limitation, and it saves the effort that would otherwise be spent
running a study toward a question it could not answer.

The reason the remedy was declined is the scale of it. Clearing five points
needs on the order of **1,500 to 2,000 held-out units**; the schedule holds out
sixty to eighty of three hundred. Preserving that fraction, the design would
need roughly **5,625 to 10,000 total units — an eighteen- to thirty-three-fold
expansion**. That multiplier is a ratio of unit counts and deliberately carries
no execution host with it: converting it into hours and comparing the result
against the registered compute trigger would repeat, in prose, exactly the
cross-host comparison the previous section refuses to make.

An expansion of that order is not a larger version of this study — it is a
different study, on a different timescale, and it is incompatible with the
registered scope. That, together with the registered compute design estimate,
is the ground for refusing it; the ground is never arithmetic across hosts.
The student's summary is the correct one: the remedy is not worth what it
costs, once the cost is understood as a twenty- to thirty-fold expansion rather
than an adjustment.

The consequence is carried forward rather than repaired. The study proceeds at
its registered size and reports what it cannot resolve. An inconclusive
Hypothesis 3 is therefore a legitimate and reportable outcome, not a failure of
the work: the thesis asks whether a critic can distinguish the two repairs, and
a well-conducted study that answers *"not at this sensitivity, and here is
precisely the sensitivity that would be required"* has answered something real.
What would make it a failure is hiding the limitation, or steering the analysis
toward the answer that was hoped for — which is what the frozen thresholds,
sealed seeds and predeclared reserve exist to prevent.

**Source answer (student, 2026-08-23, verbatim):**
> 3- it is not worth the effort.

**Provenance notes:** the student's answer is the section's verdict and is
stated as theirs in paragraph 4, qualified with the multiplier that justifies
it. The Week-4-versus-Week-15 argument in paragraph 2 develops the student's
"saves a lot of time and effort" from §12's answer 2. The negative-result
paragraph is Claude's, after the student answered "I do not know" — taught in
chat before confirmation.
