# Method — the student's own-voice rewrite

**How this file is produced (method recorded for Sol in delta 57):** for each
section, Claude asks simple questions in chat; the student answers **in their
own words**; Claude assembles the section *from those answers* — keeping the
student's phrasings where they are right, correcting facts against the ledger,
adding the frozen numbers with their estimands — and the student reads and
confirms each section before it is marked accepted. Every section carries its
source answers below it, verbatim, as provenance of whose voice it is.

**Status: §1 drafted from the student's answers — awaiting student confirmation.**

---

## 1 · Why the environment looks like it does *(W1 Thu — replaces `method_draft.md` §1 when confirmed)*

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
