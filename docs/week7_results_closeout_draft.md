# Week-7 results — updated AI drafting aid
Prepared by Sol2 from independently verified E1 labels on 2026-08-31.
**This is AI-authored, not the student's own-voice deliverable.** The student
must rewrite, check and personally explain it. It supplements the earlier
pre-label `week7_results_draft.md`; that dated draft is preserved.

Draft length: 484 whitespace-separated words. This is an E1 results-section
aid, not a claim that every Week-7 task or external review is complete.

## Draft for independent rewriting

Experiment 1 examined how ensemble disagreement changes with training-data availability and whether observed failures are repaired by more data or greater model capacity. Five configurations covered six dataset sizes, giving 30 configuration-conditions. The original trend analysis used five confirmatory seeds per condition. Its 150 baseline fits are repeated measurements of those conditions, not 150 independent statistical units. Historical fits were preserved and reused rather than replaced.

Repair labels came from two separate interventions evaluated on each baseline's original failure transitions. Data repair used the fixed tenfold data budget. Model repair used the documented capacity extension from 256 to 512 hidden units without adding data. A repair passed only when its equal-seed mean error difference was negative, the 95% seed-level t interval lay wholly below zero, and the relative error reduction exceeded 20%. A favorable point estimate alone was insufficient.

The six shape/uniform conditions used their already-specified 20-seed validation ladders, advanced from Week 9 under the recorded schedule amendment. The remaining 24 conditions used three seeds each. Their intervals therefore have different precision and degrees of freedom; they should not be pooled into one effect estimate. Baseline ensembles, individual repair models, transitions and copied evidence files were not counted as additional statistical units.

Independent source-by-source verification completed all 30 labels, with no missing or blocked condition. Twenty-nine received observed label 0 because data repair passed and capacity repair did not. One was undiagnosed because neither intervention met every acceptance condition. There were no observed label-1 or ambiguous outcomes in this E1 subset. These are operational classifications under the tested budgets and decision rule, not a proof that all possible capacity changes are ineffective.

The undiagnosed condition was shape/sparse with 5,000 training transitions and three seeds. Data repair showed a 51.9% point-estimated reduction, but its error-difference interval extended from approximately -0.9856 to 0.3116. The interval crossed zero, so the repair was not accepted. Model repair showed a smaller 6.4% reduction and also failed the uncertainty requirement. The result was retained without adding seeds, increasing budgets or replacing the condition.

The existing disagreement analysis is unchanged: all five configurations met the amended operational negative-trend criterion. These pointwise results are not a simultaneous confidence statement or full H1 confirmation. The exact paired seed bootstrap has discrete support, which the accompanying coefficient and probability-mass tables preserve. New repair labels do not authorize dropping the undiagnosed condition, adding the higher-seed baselines to that analysis, or conducting another statistical look.

Interpretation remains limited by the small seed counts and disclosed exposure. The capacity extension and all-five reporting amendment were fixed after collection and partial prior inspection. Earlier untrained engineering fixtures also regenerated some registered input pools; later isolation does not erase that exposure. No threshold recalibration, outcome-driven subset selection or repair-width adjustment followed these results. H2 and H3 were not adjudicated, and the recorded power limitation remains. Week 10 must interpret the same immutable trend report together with this repair evidence.

## Required accompanying evidence and corrections

Use `week7_repair_label_results.md` for every unit's effect, seed count,
95% t interval, relative reduction, observed label and exact source pins.
Use `week7_experiment_1_results.md` for the unchanged D-156 coefficient
report and its full discrete-bootstrap support/mass tables. The two interval
procedures must not be conflated.

Three legacy model-repair reason strings inaccurately say “includes zero”
for intervals entirely above zero. The detailed label report explicitly
corrects this wording without changing numbers, decisions or immutable files.
The draft above uses the correct negative-interval requirement.

## Student reminders

- Return your own approximately 500-word Week-7 results section, retaining the
  uncertainty, exposure and interpretation limits. Do not simply relabel this
  AI draft as student-authored.
- Complete the separate approximately 400-word Week-6 explanation of repair
  labelling and the fixed 10x data budget; be ready to explain and defend it.
- Carry the cumulative delta, mandatory closeout companion and review packet
  to external Sol when ready. Generated, delivered and certified are separate
  states. Sol2 remains the implementation role, not the reviewer/certifier.
