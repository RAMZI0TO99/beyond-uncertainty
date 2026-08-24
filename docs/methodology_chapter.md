# Chapter 3 — Methodology

> **Provenance (recorded 2026-08-23, D-132; this block is removed from the
> final thesis version):** drafted by the student from the rewrite cards, then
> polished by an AI assistant at the student's request — disclosed by the
> student unprompted. Audited by Claude against the certified record: **32/32
> checkable claims verified, zero factual errors found.** **Status: assisted
> draft.** It does **not** yet discharge the independent-rewrite obligation
> (D-125/D-131): the student's explain-and-defend walkthrough is pending, and
> until it is done and Sol has ruled, this document must not enter the thesis
> and must not be described as independently authored.


This chapter describes how the study constructs, measures, and diagnoses two different causes of world-model failure. The first is an **estimation failure**: the model class is capable of representing the transition rule, but the fitted model has not received enough data to estimate it reliably. The second is a **hypothesis-class failure**: the learner lacks the information or representational resources needed to express the rule, so adding data alone cannot solve the problem. These causes require different repairs. The study therefore does not assign ground truth from how a condition was designed or from the appearance of its error curve. It applies both repairs separately and uses their observed effects to determine the label.

Three components have deliberately separate roles. The **agent** is a fixed scripted collector. It does not learn; it only generates transitions. The **world model** is the learner: it is fitted to those transitions and predicts the dynamic part of the next state. The **critic** is a second learner that uses diagnostics from the fitted world model to predict which repair actually worked. Keeping these roles separate is essential. If the collector learned during data acquisition, dataset size would be confounded with changing behaviour. If intended construction were treated as ground truth, the critic would merely be trained to recover the experimenter's intention instead of diagnosing an observed failure.

The design is organised around preregistration: consequential choices are fixed before the data on which they could have an effect are inspected. This principle governs the threshold used to define failure, the seed boundary between development and confirmation, the order of reserve units, the repair-acceptance rule, and the sensitivity analysis. Development evidence is used to validate machinery and expose limitations; it is not reused as confirmatory evidence. The chapter consequently includes calibration and design-gate measurements where they determine what the method can support, but it does not report the substantive hypothesis results.

## 3.1 Environment design rationale

The experimental environment is a small gridworld with factored observations. Its simplicity is methodological rather than merely computational. Each failure condition must be constructed deliberately, and each label requires several additional model fits because both candidate repairs must be tested. A compact environment makes that counterfactual labelling procedure feasible while retaining complete control over the transition rules. Each environment is instantiated directly from its configuration-condition specification, so the manipulated factors are part of the design rather than adjustments made after model behaviour has been observed.

Factored observations expose the attributes of each object separately. This makes it possible to withhold one attribute while leaving the rest of the scene visible, which is needed to create a controlled hypothesis-class restriction. Every object has a shape, a colour, a position, and an activation state. A designated causal attribute controls **passability during movement**:

- when shape is causal, triangles are passable and squares block movement;
- when colour is causal, red objects are passable and blue objects block movement; and
- when position is causal, cells with even \((x+y)\) parity are passable and cells with odd parity block movement.

Position-causal conditions are part of the environment family, but they are not treated as canonical Experiment 2A conditions; Section 3.8 explains the structural reason for that boundary.

The environment also provides an `interact` action. It toggles the activation state of the first adjacent object and exists so that interaction has an observable transition consequence. Activation is deliberately orthogonal to passability: no shape, colour, or position rule governs whether `interact` toggles the object. It is therefore an auxiliary diagnostic rather than the transition rule that the primary analysis asks the world model to discover.

This environment supports the thesis's central counterfactual. An estimation failure should improve when the amount of training data is increased without changing the model class. A hypothesis-class failure should improve when the representational restriction is repaired, whereas additional data alone should not be sufficient. The environment is valuable because both interventions can be run on the same underlying configuration-condition, allowing the label to be based on repair outcomes rather than visual judgement.

## 3.2 Configuration axes and sampling design

The experiment varies dataset size, object layout, feature visibility, model capacity, and the strength of a misleading decoy or confounding attribute. These axes have distinct methodological purposes. Dataset size is the direct manipulation for producing and repairing estimation failure. Withheld causal features and capacity restrictions create hypothesis-class limitations. Layout and confound strength vary the context in which those failures appear and test whether the critic diagnoses the repair rather than relying on a superficial correlate.

The design uses 300 configuration-conditions as a balanced sample from this space. It is **not** a complete crossing of every axis. A full factorial crossing would exceed the registered scope, while a balanced sample provides planned coverage of the axes and equal representation of the two intended failure classes. The initial allocation is 150 units intended to produce estimation failure and 150 intended to produce hypothesis-class failure.

This balance concerns the construction of the sample, not the final ground-truth labels. The **intended class** records how a unit was built and is used to control sampling. The **observed label** records which repair passed the acceptance test and is the target predicted by the critic. A unit intended to create one failure type is not forced into that class if its repairs do not support the label. This distinction prevents design intention from being mistaken for empirical ground truth.

Balance is also important for critic evaluation. With a strongly imbalanced sample, a critic could achieve high ordinary accuracy by repeatedly predicting the majority class. The design therefore preserves intended-class balance and uses balanced accuracy for the critic. When exclusions reduce the usable classes unequally, the effective critic sample is based on the surviving balanced count, \(\min(N_0,N_1)\), rather than the number of attempted units.

Because counterfactual labelling can yield ambiguous or undiagnosed units, a reserve list was declared before any real repair labels were observed. Its order was committed in advance. If replacements are authorised, they are drawn only in that order. The reserve is therefore a planned extension of the balanced sample, not a set from which favourable replacements can be selected after viewing outcomes.

## 3.3 Behaviour policy and data collection

The world model learns from transitions consisting of a current observation, an action, and the next observation. The collector's task is broad exposure rather than reward maximisation: it must traverse the grid, attempt movement around objects, and use `interact` beside different objects so that the data contain the relevant transition types. A fixed exploratory script is used for this purpose.

The original design proposed PPO as the behaviour policy. It was replaced because a learning collector would weaken the interpretation of the dataset-size manipulation. As PPO changes during training, early and late transitions come from different policies. A model trained on 5,000 transitions would then receive not only more data than a model trained on 100 transitions, but also data generated by a more developed collector. An improvement could not be attributed cleanly to quantity. The scripted policy instead remains stationary across episodes, so increasing the dataset size adds more transitions from the same collection mechanism.

The use of a script is supported by measured coverage rather than by assertion. Coverage evidence was re-collected after the stationary policy was fixed. Measurements from the earlier, non-stationary version were declared void and are not quoted or used. This correction matters because evidence is conditional on the procedure that generated it: once the policy changed, its previous coverage measurements no longer validated the current collector.

The collector remains fixed for all experimental roles. It does not update from reward, world-model error, or critic feedback. The agent therefore never learns. Learning occurs only in the world model and, later, in the diagnostic critic.

## 3.4 Correction and interpretation of collection evidence

The collection-policy correction was recorded explicitly rather than silently incorporated. Recording it preserves the distinction between the method originally evaluated and the method ultimately used, and it prevents invalid measurements from remaining in the evidential chain.

Under the corrected policy, the estimated trend by episode index was approximately \(+1.1\) standard errors. This is **consistent with** the absence of meaningful episode drift at the sensitivity of that diagnostic; it does not prove that episodes are independent and identically distributed. A null result can fail to reveal small, unmeasured, or differently structured departures from the null.

Where stationarity follows from construction, the claim is therefore grounded in construction: the same fixed policy object is used in every episode. The drift diagnostic is supporting evidence about its realised behaviour, not proof of an IID property. This distinction separates structural guarantees from empirical non-rejection and avoids turning an insensitive test into a stronger claim than it can support.

## 3.5 Development curves and preregistered confirmation

Before formal testing, development runs were used to inspect whether the pipeline produced plausible learning behaviour. The first curves showed lower prediction error as the training dataset grew and increasing agreement among ensemble members at larger sample sizes. These observations were recorded descriptively. They are not a verdict on Hypothesis 1.

The core Hypothesis 1 estimand and direction had been specified in advance: rank correlation between the six dataset sizes and ensemble disagreement, with uncertainty evaluated over seeds. The remaining implementation details—including the use of Spearman correlation, the exact paired seed-block bootstrap, the whole-interval decision rule, and the handling of degenerate cases—were frozen before the reliability gate and before any confirmatory test. This sequence prevents the formal rule from being adjusted to secure a preferred interpretation of the development curves.

The seed boundary supplies a second separation. Seeds below 1000 are permanently development data and may be used for debugging and method validation. Confirmatory seeds begin at 1000 and remain untouched until the registered hypothesis test. A visually convincing development curve can therefore motivate confidence that the machinery operates, but it cannot be promoted into confirmatory evidence after it has been inspected.

## 3.6 Construction of the normalising scale

Raw position errors are not directly comparable across dimensions and configurations. Different grids provide different ranges over which a prediction can be wrong, and the coordinate dimensions can have different empirical scales. The study therefore divides each error dimension by a corresponding scale before aggregating the primary movement error.

The scale is constructed from the **full movement evaluation pool before any failure mask exists**. The same scale object is reused for whole-pool statistics and for all statistics restricted to transitions subsequently marked as failures. It is not recalculated for a layout, repair arm, or failure subset.

This order avoids circularity. Failure status is defined by comparing normalised error with a fixed threshold. If the scale were recomputed after selecting failures, the selected observations would alter the ruler used to select them, and the same numerical threshold would acquire a different meaning in each subset. Building the scale first and reusing it fixes the metric before the failure set is known.

The registered evaluation path enforces this ordering structurally at the relevant call site: the scale constructor for the pool accepts no failure mask, and masked statistics receive the already-created object. The underlying type could still be misused elsewhere if handed a subset directly, so each scale also records the number of transitions from which it was built. The invariant is consequently both enforced in the registered path and auditable in derived artefacts.

## 3.7 Definition of model error

The world model predicts dynamic state components only. Shape, colour, and the fixed object descriptors are deterministic passthrough fields: they are copied into the predicted next observation and never enter the training loss. Including them would reward the model for reproducing quantities that cannot change, inflating apparent accuracy while diluting the dynamics errors of interest.

The dynamic targets are action-conditional. On movement transitions, the primary target is the agent's next position. On `interact` transitions, the dynamic target is the activation change of the affected object. Position is not scored on an interaction step, and activation is not used to decide movement failure, because both would award correct identity predictions on transitions where the quantity cannot change.

The primary error used to define failure is therefore the ensemble-mean, per-dimension-normalised error in next-agent position on movement transitions. Static attributes never contribute to this quantity. Activation is retained only as an auxiliary diagnostic. Its prediction head receives a detached representation, so its gradients do not update the shared trunk, and it is barred from early stopping, checkpoint selection, failure-set construction, repair labelling, and the residual features supplied to the critic. This isolation ensures that an auxiliary task cannot determine the labels or model selection decisions in the main experiment.

## 3.8 Exclusion of position-causal conditions from canonical Experiment 2A

Canonical Experiment 2A creates hypothesis-class failure by withholding the attribute on which the passability rule depends. Withholding shape or colour leaves the scene spatially complete: object slots, locations, and the other object attributes remain visible. The model can distinguish the relevant states, but the specific rule cannot be represented from its inputs because the causal attribute is absent.

Withholding position causes a different failure. Position tells the model where an object is; it does not tell the model that the object exists, because shape, colour, activation, and the fixed object slot remain present. Removing position causes distinct spatial states to share the same encoded observation. The same observation-action key can therefore correspond to different true outcomes, producing **causal aliasing** rather than a cleanly unrepresentable visible-object rule.

This difference was measured. When position was withheld, 37.5% of observation-action keys were aliased, compared with 10.0% when shape or colour was withheld, even though the position-withheld key space was 26 times smaller. Position-causal conditions were therefore removed from the canonical Experiment 2A set and retained as a declared three-seed robustness configuration. This is a boundary on the claim rather than a post hoc deletion: the canonical experiment concerns withheld attributes of otherwise visible objects, while the position condition tests a separate structural failure caused by spatial aliasing.

## 3.9 Reliability gate for ensemble disagreement

Before ensemble disagreement could be used in a hypothesis test, a development gate checked whether the registered estimator responded to dataset size in the expected direction. The gate used three predeclared configurations—uniform, clustered, and sparse layouts—and five development seeds per configuration. Across the six dataset sizes, Spearman's rank correlation between size and mean disagreement was \(\rho=-0.9429\) for all three configurations. The gate comprised 90 ensembles and 450 model fits and completed in 4 minutes 52 seconds on the local CPU system.

All three configurations passed at the initial gate rung. The difficulty ladder was therefore stopped; rungs 1 and 2 were not run. Stopping is part of the registered procedure and avoids converting a successful validation check into an unplanned search for more favourable evidence.

Two of the three paired-bootstrap percentile intervals had identical reported endpoints. They must not be interpreted as showing the absence of sampling uncertainty:

> Exact paired seed-block bootstrap percentile intervals were computed over all 3,125 resamples. Because Spearman correlation over six dataset sizes has highly discrete support, the bootstrap distributions contained only two or three distinct values. A zero-width percentile interval therefore reflects quantile discreteness, not zero sampling uncertainty.

For the two zero-width cases, the relevant atom masses were:

| Layout | \(\rho=-0.9429\) | \(\rho=-0.8286\) |
|---|---:|---:|
| Uniform | 98.37% | 1.63% |
| Sparse | 97.86% | 2.14% |

The 2.5% percentile boundary makes the sparse interval particularly sensitive to the discreteness of the bootstrap distribution: its secondary atom is only 0.36 percentage points below that boundary. All atoms nevertheless remain below zero, so this issue concerns the apparent precision of the interval rather than the gate verdict.

The individual curves were not smoothed or selectively rerun. Fourteen of the fifteen seed-by-configuration curves peaked in disagreement at \(N=250\) before declining. Clustered seed 4 instead peaked at \(N=500\), with its \(N=250\) value below \(N=100\). That observation is reported but not investigated using the same development evidence. Any confirmation belongs to the untouched confirmatory seeds.

Passing this gate validates the operation of the estimator under development conditions; it does not establish Hypothesis 1. The gate and the hypothesis use different evidential roles, and only the latter may use the confirmatory seeds.

## 3.10 Calibration and permanent freezing of the failure threshold

A movement transition is defined as a failure when its primary normalised error is **strictly greater than**

\[
0.610702633857727.
\]

Equality is not a failure. This boundary convention is consequential rather than cosmetic because two transitions in the calibration pool have errors exactly equal to the threshold.

The threshold was calibrated against healthy reference models, providing a definition of unusually large error relative to conditions in which the model is given the strongest opportunity to succeed. The full estimand is the 95th percentile, using `method="linear"`, of ensemble-mean per-dimension-normalised agent-position error on movement transitions from five-member, fully observed reference ensembles trained on \(n=5{,}000\) transitions with no confound. Calibration used seeds 1000–1004 and nine layout-by-causal-attribute strata.

The strata were equally weighted using deterministic subsampling without replacement to the smallest stratum count at random-number-generator seed 0. This produced \(9\times4{,}103=36{,}927\) calibration transitions from an available 37,406. Equal weighting prevents a stratum with more transitions from determining the pooled 95th percentile simply through its size. The calibration required 225 individual model fits: five ensemble members for each of five seeds in each of nine strata.

The unbalanced full-pool check yields 5.02% failures, close to the 5% induced in the balanced reference by construction. This is evidence about the effect of unequal stratum counts on the pooled aggregate only. It does not imply that the error tails or failure rates are homogeneous between strata.

The threshold was computed once under prechecked conditions, verified independently to the bit-identical floating-point value, and permanently frozen before downstream repair labels were observed. It cannot be rounded, replaced by per-layout thresholds, or recalibrated. This irreversibility is necessary because the threshold defines failure sets, failure sets determine repair labels, and those labels train and evaluate the critic. Recalibrating after observing downstream behaviour would silently redefine the target of the study.

## 3.11 Layout variation in failure prevalence

The same global threshold applies in every layout, and its definition does not change. However, the proportion of calibration transitions above that threshold is not uniform. Across the nine calibration strata, prevalence ranges from 1.58% to 8.77%, a 5.5-fold spread, ordered from clustered to uniform to sparse layouts.

This measurement is retained without a causal explanation. An earlier interpretation attributed the spread mainly to the normalising scale, but that claim was withdrawn in review. Evidence about average scale or average error cannot establish why the upper tails of the distributions differ. The stored artefacts support the prevalence measurement; they do not support the proposed mechanism.

The correction also fixes two reporting rules. First, prevalence must identify its aggregation: pooling transitions and averaging stratum-specific rates are different estimands and are reported as such. Second, a per-dimension scale is a vector and is not collapsed into a single layout-level value when doing so would hide overlap between dimensions.

The global failure definition remains unchanged. Instead, layout is carried into downstream robustness reporting. Hypothesis 2 includes layout-stratified secondary estimates, while critic balanced accuracy and confusion behaviour are reported overall and by layout. These analyses reveal whether the labelled sample or critic performance depends disproportionately on a particular layout without changing the primary weighting or redefining failure after the fact.

## 3.12 Gate 1: detectable effects and design limits

Gate 1 was a scheduled pre-confirmatory assessment of whether the design and its instruments were adequate to continue. It comprised four conditions:

| Condition | Gate 1 status | Basis |
|---|---|---|
| Reliability of ensemble disagreement | Pass | All three predeclared development configurations passed the registered rank-correlation gate. |
| Compute trigger | Not adjudicable | Cost was measured in local wall-hours, while the trigger was defined in GPU-hours on hardware never used. |
| Repair-test permutation calibration | Pass | The registered rule behaved within its admissible null-calibration bounds. |
| Sensitivity to the Hypothesis 3 margin | Fail | The scheduled sample could not resolve a five-percentage-point difference. |

The compute condition is neither a pass nor a failure. The measured estimates were 5.72 median and 6.91 conservative-maximum **local wall-hours**. The registered trigger was 120 **GPU-hours** on a device that did not produce these measurements. Because host and unit differ, comparing the numbers would not adjudicate the trigger.

At first assessment, a **provisional, optimistic diagnostic** simulation estimated a detectable difference of 18–22 percentage points under the scheduled sample. This is not an exact minimum detectable difference and is not described as the smallest difference the design can detect. The simulation used a provisional Wald rejection rule that over-rejected under the null: measured false-positive rates were 6.1–9.2% against a nominal 5%. The final exact MDE cannot be computed until the final group-level inference for Hypothesis 3 is fixed and calibrated under its null.

The qualitative conclusion is nevertheless clear. Sample size, rather than an uncertain intraclass-correlation assumption, drives the shortfall: even with \(ICC=0\), the diagnostic estimate remains 18 percentage points. Strong critic-baseline pairing reduces the diagnostic estimate only to eight points, and placing all 300 units in the held-out set reduces it only to six. None reaches the registered five-point margin under a valid train-and-evaluate design.

The diagnostic MDE-to-margin comparison is a necessary sensitivity check, not an equivalence test. A diagnostic MDE above five points shows that the current design cannot resolve the five-point region. The converse would not establish equivalence or adequate power by itself. The two-sided \(\alpha=0.05\) rule used in the diagnostic is also recorded as a deviation because the plan specified power but did not specify alpha.

Gate 1 therefore fails on sensitivity alone. The study may detect comparatively large differences in Hypothesis 3, but it may be inconclusive around \(\pm5\) percentage points. No equivalence claim will be made unless the final interval itself can support it. This limitation was established before confirmatory results and is part of the method's scope, not an explanation introduced after seeing an unfavourable outcome.

## 3.13 Prescribed expansion and the decision not to apply it

The original plan prescribed an increase in configuration count if detectable sensitivity exceeded the five-point margin, and the schedule required that increase to be made at Gate 1. The count was not raised. This was a deliberate, reviewed deviation and is recorded as such.

A rough diagnostic extrapolation suggested that approximately 1,500–2,000 held-out units might be needed, compared with the scheduled 60–80. This range is not a computed sample-size requirement because the final Hypothesis 3 inference and its exact MDE are not yet available. Preserving the registered held-out fraction would imply approximately 5,625–10,000 total units, or 18.75–33.3 times the current unit count.

That multiplier is a unit-count extrapolation only. It has no execution host and is not converted into hours or compared with the 120 GPU-hour trigger. The decision to decline expansion rests on the registered scope and on the budget position established by the planning-stage GPU-hour design estimate. It does not rest on invalid arithmetic between measured local wall-hours and planned GPU-hours.

The limitation is therefore carried forward rather than repaired. This does not make an inconclusive Hypothesis 3 a failed thesis. The method can establish whether a sufficiently large diagnostic advantage is present and, if the final interval is inconclusive near five points, can state the sensitivity boundary discovered in advance. What it cannot do is turn absence of resolution into evidence of equivalence. Recording that distinction before confirmation is one of the safeguards against analysis choices being steered by the eventual result.

## 3.14 Computational environment and provenance

The planning model assumed Kaggle GPU execution, with access to two T4 devices and a budget expressed in GPU-hours. In practice, every model fit used in the study was produced on a local CPU workstation. No Kaggle job was submitted, and zero GPU-hours were consumed.

The certified full-design estimate is 5.72 median to 6.91 conservative-maximum local wall-hours. These values describe the environment in which the work was actually produced, but they do not answer whether the design satisfies a GPU-hour trigger. Computational quantities retain the hardware and measurement unit of the system on which they were obtained.

Thread count is included in the provenance record because it is not numerically neutral. Re-execution with four rather than eight threads reproduced one certified cell exactly and shifted another by 0.19%, consistent with a change in floating-point reduction order. Reproducibility therefore requires more than naming the processor: the execution configuration must also be recorded.

Timing evidence is bound to its source provenance. Each certified record identifies the exact source commit, requires a clean working tree, and verifies a content digest during review. This links the reported time and numerical outputs to the implementation that generated them and prevents results from being attributed to an unrecorded code state.

## 3.15 Exclusion-rate assumption and reserve procedure

Counterfactual labelling can produce four outcomes. If only the data repair is accepted, the observed label is estimation failure. If only the model-class repair is accepted, the observed label is hypothesis-class failure. If both repairs are accepted, the unit is ambiguous; if neither is accepted, it is undiagnosed. Ambiguous and undiagnosed units are excluded from critic training and evaluation rather than forced into one of the two classes.

The schedule called for the configuration target to be inflated using a pilot exclusion rate. No pilot-labelled units existed, so there was no empirical rate from which to estimate inflation. Before any real labels were observed, the study therefore registered a value of 0.00 as a **zero-inflation planning convention**, not as a prediction or observation. The target was

\[
\left\lceil \frac{300}{1-0.00} \right\rceil = 300,
\]

with no anticipatory oversampling.

The realised exclusion estimand is

\[
\frac{N_{\text{ambiguous}}+N_{\text{undiagnosed}}}{N_{\text{all attempted labelled units}}},
\]

reported both pooled and by intended class. Any observed exclusion above zero means that the planning assumption was missed. The shortfall is reported before a replacement is drawn, preserving evidence about how accurately the original plan anticipated labelling loss.

Only after that report may replacements be drawn from the predeclared reserve, under its gate and in its committed order. Attempted totals are never substituted for usable sample size. The critic's class-balanced sample is the surviving \(\min(N_0,N_1)\), and all Hypothesis 3 accuracy estimates are explicitly scoped to cleanly separable failures—units for which exactly one repair was accepted. They are not generalised to ambiguous, undiagnosed, or all possible failures.

## 3.16 Repair-acceptance test and counterfactual labels

Every observed failure label is determined by the same repair-acceptance test. The baseline and repaired models are evaluated on the baseline model's fixed failure set, using paired per-transition primary errors. A repair is accepted only if all three registered conditions hold:

1. the repaired model has a positive mean reduction in error;
2. the 95% confidence interval for that reduction excludes zero in the improvement direction; and
3. the mean reduction is greater than 20% of the original mean error.

The third condition separates statistical detectability from practical importance. With a sufficiently large number of transitions, a negligible reduction could be estimated precisely and still have little diagnostic meaning. The relative 20% floor defines the least improvement the study is willing to call a successful repair and remains comparable across configurations with different baseline error scales.

The original plan specified a mixed-effects model with random intercepts for seed and episode within seed. The literal specification was replaced under a recorded change because it is degenerate for this design. Where a reduced version could be fitted, it could yield anti-conservative intervals, which is especially unsafe here because false repair successes become ground-truth labels for every downstream analysis.

The registered replacement respects both pairing and the level of replication. Transition-level errors are paired between the baseline and repaired arms. Their differences are averaged within seed, and the repair effect is the equal-seed mean of those paired differences. Its confidence interval is a t interval with \(n_{\text{seeds}}-1\) degrees of freedom. Transitions contribute to the within-seed estimate; they are not treated as independent experimental replicates.

There is no episode-mean fallback or alternative analysis path. Invalid, degenerate, or non-finite input fails closed and cannot produce an accepted repair. Removing the fallback prevents the analysis from switching estimators after observing which one supplies a label.

Null calibration preserves the same dependence structure. Permutations operate on whole paired runs and seeds and never shuffle individual transitions, because transitions within a run are not exchangeable. In 200 null permutations, the full three-condition rule accepted zero repairs. The confidence-interval condition alone fired in 5–7 of 200 permutations, within the predeclared admissible range of 1–10. This calibration is why Gate 1 records the repair test as passed.

The two repairs are then converted into a single counterfactual label:

| Data repair | Model-class repair | Observed outcome |
|---|---|---|
| Accepted | Not accepted | Estimation failure |
| Not accepted | Accepted | Hypothesis-class failure |
| Accepted | Accepted | Ambiguous; excluded |
| Not accepted | Not accepted | Undiagnosed; excluded |

This table is the operational definition of ground truth. Intended class determines how a unit enters the balanced sample; observed repair outcome determines what the unit teaches the critic.

## 3.17 Statistical unit, seed obligations, and held-out evaluation

The statistical unit is the **configuration-condition**: one environment setting together with one failure condition. The baseline failure condition and both repair arms belong to that same unit. This shared identity is what makes a counterfactual label assignable, because the interventions are compared on the condition that originally failed.

Four related identifiers serve different purposes:

| Identity | Composition | Purpose |
|---|---|---|
| Configuration-condition | Environment setting + failure condition | Statistical unit and label target |
| Configuration | Configuration-condition + repair arm | Distinguishes baseline and intervention arms |
| `run_id` | Configuration + stage + seed | Records an experimental obligation |
| `fit_id` | Configuration + seed, without stage | Identifies a unique model computation for deduplication |

The distinction between `run_id` and `fit_id` prevents one computation from being counted more than once when it serves several analytical roles. Canonical repair-validation units use 20 seeds because they determine ground truth. If such a unit also serves a Hypothesis 1 or Hypothesis 2 role, the five hypothesis seeds are contained within those 20; the requirement is not 20 plus 5. Sweep-only units use three seeds and carry neither the repair-validation nor hypothesis-specific obligation. Conflating roles with unique computations previously produced 375 phantom fits, which is why both identities are retained in the execution ledger.

The larger seed count for repair validation reflects the consequence of its decision. A hypothesis estimate can present uncertainty around a measured effect. A repair decision creates a categorical label inherited by the critic and every downstream analysis. Twenty seeds reduce the across-seed standard error to roughly half that of five seeds and provide a more stable foundation for the label.

Seed roles are also sealed by number. Confirmatory seeds are 1000 or greater. Every seed below 1000 is permanently classified as development data, even if a development run was not inspected at the time. This rule prevents unused development computations from being relabelled as confirmatory evidence after their surrounding pipeline has been tuned.

Some units share data by design and therefore belong to the same comparison group. A comparison group is kept whole across every critic train/test boundary and every cross-validation fold. If related units appeared in both training and evaluation, the critic could score well by recognising a familiar comparison group rather than learning a diagnostic relation between world-model evidence and repair outcome. Group-preserving splits make the held-out score an estimate of performance on genuinely unseen configuration groups.

The primary weighting is the registered **unit** estimand. Effective sample-size quantities are consequently reported only with that estimand attached. At the \(ICC=1\) boundary, the relevant values are 75 and 72.6 under unit weighting. Counts of 125 and 115 comparison groups belong to a different estimand that the thesis does not use and are not substituted into the primary sensitivity argument.

Taken together, the unit definition, nested seed obligations, deduplicated computations, and group-preserving splits prevent three forms of leakage: treating transitions as independent units, counting the same fit twice, and testing the critic on close relatives of its training examples. The resulting held-out evaluation asks the intended question: whether the critic can diagnose which counterfactual repair worked on configurations it has not previously seen.

The methodology therefore supports a deliberately bounded claim. It can compare two empirically tested repair outcomes on cleanly separable, held-out configuration-conditions under a fixed measurement and labelling protocol. It cannot establish equivalence near a five-point margin with the scheduled sample, infer a mechanism for layout-specific failure prevalence, or generalise critic accuracy to units for which neither or both repairs work. Those limits are part of the design and were recorded before the confirmatory evidence was opened.
