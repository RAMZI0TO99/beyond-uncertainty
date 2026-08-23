# Method — the student's own-voice rewrite

**How this file is produced (method recorded for Sol in delta 57):** for each
section, Claude asks simple questions in chat; the student answers **in their
own words**; Claude assembles the section *from those answers* — keeping the
student's phrasings where they are right, correcting facts against the ledger,
adding the frozen numbers with their estimands — and the student reads and
confirms each section before it is marked accepted. Every section carries its
source answers below it, verbatim, as provenance of whose voice it is.

**Status: §1–§3 CONFIRMED by the student (2026-08-23). §4 and §5 drafted — awaiting student confirmation.**

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

## 4 · What the re-measured evidence can and cannot say *(D-051/D-054 — replaces `method_draft.md` §4 when confirmed)*

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

## 5 · What the first curves look like, and why they are not a result *(W3 Sat — replaces `method_draft.md` §5 when confirmed)*

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
