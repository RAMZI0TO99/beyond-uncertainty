# Week 6 student closeout — drafting aid and action reminder

**Status:** AI-authored drafting aid created by Sol2 on 2026-08-30. This is
**not** the student's own-voice Week 6 deliverable and does not close Week 6.
The student must rewrite the explanation independently, keep only wording they
can personally explain and defend, and return approximately 400 words for a
fact check. Sol2 may check factual accuracy but must not relabel this draft as
student-authored prose.

## Draft to rewrite in your own words

The critic needs labels that describe why a world model failed. Those labels
cannot come from the class that was intended when a configuration was built,
because that would make the conclusion circular: the experiment would simply
recover the category that the design assigned in advance. Instead, the label
comes from counterfactual repair outcomes. Starting from the same observed
failure, I test two separate interventions and ask which one actually reduces
the model's error. The observed result, rather than the construction label, is
therefore what teaches the critic.

The first intervention is a data repair. If the baseline model was trained on
\(n\) transitions, this repair trains it on exactly \(10n\) transitions from
the same fixed data-generating process. The original \(n\) observations are
retained as a nested prefix of the larger dataset. This matters because the
comparison should isolate the effect of receiving more evidence; changing the
generator or replacing the original sample would introduce another possible
cause. The tenfold budget is fixed before observing repair results, so it
cannot be increased only for difficult cases or stopped early when a preferred
answer appears.

The second intervention is the model-class repair. It changes only the
predeclared model restriction assigned to the unit: feature access is restored
for a feature-restriction condition, or capacity is raised to the registered
maximum for a capacity condition. It does not also add data or change the
evaluation set. Both repairs are tested separately on the baseline model's
recorded failure set, which keeps the target of the comparison fixed.

A repair is accepted only when all three registered conditions are satisfied.
First, its mean error reduction must be positive. Second, the 95% confidence
interval must exclude zero in the improvement direction. Third, the mean
reduction must be greater than 20% of the baseline mean error. The first two
conditions require evidence of a real improvement, while the relative 20%
floor prevents a tiny but precisely estimated change from becoming a
scientifically meaningful label.

The two decisions produce four possible outcomes. If only data repair works,
the unit receives observed label 0, estimation failure. If only model-class
repair works, it receives observed label 1, hypothesis-class failure. If both
work, the unit is ambiguous; if neither works, it is undiagnosed. Ambiguous and
undiagnosed units are reported but not forced into critic training or
evaluation. This rule makes the ground truth empirical and keeps uncertainty
visible instead of hiding it inside a convenient binary label.

## What the student still needs to do

- Rewrite the draft independently in approximately 400 words and in your own
  normal voice; do not submit the text above unchanged.
- Make sure your version explains the observed-outcome rationale, exact
  \(10n\) nested-prefix data repair, isolated model-class repair, all three
  acceptance conditions, and all four label outcomes.
- Send your version to Sol2 for a factual check and be ready to explain and
  defend each statement.
- After that check is recorded, Week 6 can be marked complete locally; external
  Sol's review of D-141–D-151 and DEV-015–017 will still remain pending.
