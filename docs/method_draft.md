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
