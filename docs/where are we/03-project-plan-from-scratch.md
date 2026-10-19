# Beyond Uncertainty: the project plan

A proposal-style explanation for our professor and teammates.

## The question

**When an AI model makes bad predictions, does it need more data, or does it need a different model?**

These problems require different repairs. A suitable model may need more examples. A model missing essential information, or lacking enough capacity, may need its inputs or structure changed.

For example, imagine that object shape determines whether an agent can pass through a cell, but its prediction model sees only colour. Collecting more colour-only examples cannot supply the missing shape information. We want to learn whether a diagnostic model can recognize when a model change is needed.

## What we want to test

We will study three hypotheses:

- **H1 — Limited data:** when the model can represent the task, disagreement between independently trained models should decrease as training data increases.
- **H2 — Structural limitation:** models sharing the same limitation may agree while making mistakes. Their disagreement relative to prediction error should be lower than in repair-verified limited-data failures.
- **H3 — Learned diagnosis:** a learned diagnostic model, called the **critic**, should outperform a fitted rule using only error and disagreement by more than **five percentage points of balanced accuracy**. Balanced accuracy gives both diagnosis classes equal weight.

These are predictions to test, rather than guaranteed outcomes.

## How we will carry out the project

1. **Build a controlled world.** Use a small gridworld with objects, movement rules and configurable visible features. A fixed scripted agent will collect observations, actions and next states.
2. **Train prediction models.** Train small neural networks to predict what happens next. Train several models as an ensemble, measuring both prediction error and disagreement.
3. **Create different failure conditions.** Vary data quantity, visible information, model capacity, layout and misleading correlations. Use a planned pool of 300 configuration-conditions.
4. **Try repairs separately.** Test ten times as much data with the same model, and a model repair with the original data. The model repair restores a missing feature or increases capacity. Evaluate both on the same baseline failure cases.
5. **Build diagnosis labels.** Assign labels from which repair actually passes the fixed acceptance test, rather than from the failure type we intended to create.
6. **Train and evaluate the critic.** Use permitted diagnostic traces to predict whether more data or a model change is required. Compare it with the fitted baseline on held-out configuration groups and run controlled comparisons to understand which information helps.

## How the labels will work

| Repair outcome | Diagnosis |
| --- | --- |
| Only the data repair passes | Estimation failure: more data is the successful repair. |
| Only the model repair passes | Hypothesis-class failure: a model change is the successful repair. |
| Both pass | Ambiguous; report separately. |
| Neither passes | Undiagnosed; report separately. |

Passing requires a statistically supported error reduction exceeding the fixed 20% relative-improvement threshold. The critic will predict the two broad repair categories. Ambiguous and undiagnosed cases will be reported and excluded from its binary evaluation.

## How we will make the comparison trustworthy

We will separate development and confirmatory seeds, fix analysis and repair-acceptance rules before their confirmatory use, and keep related configuration groups together when splitting data. The critic and baseline will be compared on the same held-out cases. Critic inputs will exclude construction labels, dataset size, model-capacity settings and the repair outcomes it must predict.

We will report observed class counts, exclusions, confidence intervals and the study's ability to resolve the five-point margin. If uncertainty is too wide, we will report an inconclusive result. A non-significant difference alone will not establish that the methods are equivalent.

## What the project will deliver

A controlled experimental pipeline, a repair-verified labelled dataset, a trained critic and baseline comparison, reproducible results, and a thesis explaining the findings and limitations. A negative or inconclusive finding can still complete the research.

Sources: [research design](../../README.md#research-status), [source plan](../thesis_project_plan_v1_2.docx), [methodology](../methodology_chapter.md), and [controlling decisions](../../DECISIONS.md).
