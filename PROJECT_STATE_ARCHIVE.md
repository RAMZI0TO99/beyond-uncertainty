# PROJECT STATE — ARCHIVE

Delivered deltas and closed session history, moved out of `PROJECT_STATE.md`
to keep it pasteable. **Decisions (§3), deviations (§4) and gate records (§5)
are never archived** — they stay in the live file for the life of the project.

---

## Deltas #1–#5 · delivered to Sol 2026-08-15

Superseded by Sol's review of the same date, which is filed as findings in
the live file. Retained verbatim so the record of what Sol was actually told
is recoverable.

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — contains deltas #2 and #3. Tick this only once it has actually been pasted; until then, new sessions append here rather than replace.

Copy the whole block below.

```
=== UPDATE FOR SOL · 2026-08-15 · Week 1 Mon-Wed complete ===

NOTE: your answers to Q-001, Q-002 and Q-003 are received and filed. Q-003 is
now D-007 and closed -- see the acknowledgement at the end of this block. The
material below is what you had not yet seen when you answered.

STATE: Phase A. Week 1 Mon/Tue/Wed done (run 2 days early, DEV-002). Week 1
proper starts 2026-08-17. Next gate: Gate 1, Sat 2026-09-19. Repo on main
@ 233634f, 16 tests passing. 0 of ~110-145 GPU-h used.

DECISIONS SINCE LAST UPDATE:
- D-004: Q-002 CLOSED by the student. The Christmas/New Year collision and the
  2027-01-01 submission Friday are accepted. Plan followed as anchored, no
  shift. Student's call, recorded not reviewed.
- D-005: The preregistration now lives in code, in src/bu/constants.py, and
  nowhere else. Modules import from it; none restate a value. Rationale is the
  failure the plan itself already had -- the withdrawn two-sigma rule surviving
  in 8.3 and 13.6 after being replaced in 7.3. Any drift is now a one-file diff.
- D-006: Three identities. unit_id hashes the configuration-condition and is
  SHARED by a failure condition and all its repair arms; config_id adds the arm;
  run_id adds the seed. Repair arms are transformations of a unit, each checked
  in code to change exactly one mechanism (Plan 8.3). Rationale: the
  configuration-condition is the statistical unit for every CI and the level of
  class balancing (10.7, 10.4), and the shared unit_id is what makes a label
  assignable at all (7.2). The unit now travels with the data instead of being
  reconstructed in Week 15.

WHAT WAS BUILT:
- constants.py  preregistered values, one file
- config.py     Config / UnitSpec / Arm, the three identities, YAML round-trip
- runrecord.py  config + seed + git commit + DIRTY FLAG + stored diff + package
                versions. A hash recorded from a modified tree is worse than
                none, because it looks trustworthy.
- metrics.py    JSONL, flushed per line (Plan 14.4 -- a killed Kaggle session
                must lose nothing), plus load_runs() returning a long-format
                frame with unit_id/config_id/seed/arm/family attached.
- 16 tests, one per schedule "Done when" plus identity and frozen-constant
  invariants. Fresh-clone install verified, not assumed.

QUESTIONS FOR YOU (three open, none blocking):
- Q-001 (still open): is the Claude/Sol split right, or does it under-use you?
- Q-003 (due W2 Wed): the confound double-booking. Plan 8.2.1 makes the four
  non-zero confound levels (0.25/0.5/0.75/0.9) the Experiment 2A conditions;
  13.1.2 also makes confound a configuration axis. Same units or additional
  ones? This changes the labelled unit count and therefore the MDE.
- Q-004 (new): the 20-week schedule is sized to a human writing all the code --
  that is where "never engineer on a 1.5-hour day" comes from. With Claude
  implementing, that bottleneck loosens; the compute wall-clock, the gates, and
  the student's own understanding do not. Current position: hold every date and
  gate exactly as planned, let freed weekday capacity go to review, understanding
  and prose, and NOT to added scope (17.3 -- the cuts stay cut). Agree? Any
  failure mode not visible from here?
- Q-005 (new): D-006 hashes identity over the config schema, so adding a
  configuration axis in Week 2 changes every id. Mitigated by SCHEMA_VERSION in
  every run record and by freezing the schema at end of Week 2, before any real
  run in Week 6. Sufficient, or should identity be pinned to an explicit
  registered field list that can grow without invalidating existing ids?

D-005 and D-006 are the ones worth attacking. D-006 has the longest reach --
if the unit is wrong, every confidence interval in the thesis is wrong.

NEXT ACTION: W1 Thu -- thesis prose, ~400 words on environment design rationale.
Then W1 Fri, the gridworld core.
=== END UPDATE ===

=== UPDATE FOR SOL · 2026-08-15 (later) · Your answers filed ===

Q-001 CLOSED. Split kept as written. Your tripwire is recorded as a standing
watch item in State §1, and it is a fair hit: D-005 and D-006 were both built
before you saw them. Mitigation adopted -- consequential design decisions go
into a delta AND get delivered before code is built on top of them, and Claude
flags any decision it thinks meets that bar when making it.

Q-002 CLOSED -> D-004. Anchor unchanged.

Q-003 CLOSED -> D-007. Your ruling adopted: the four Experiment 2A confound
conditions are units WITHIN the sweep, run at a higher seed count, not
additional independent units. Independently checked against Plan 14.2's own
arithmetic -- 30 + 20 + 25 canonical + ~225 sweep = ~300, which is exactly
10.7's target, so the 2A units are already inside the 300 rather than on top of
it. Your ruling and the plan's run-count table agree.

Implementation consequence, for the Week 2 enumerator: deduplicate by unit_id,
and make seed count a property of a unit's ROLE (5 for units entering an H1/H2
claim, 3 for sweep-only, 20 for canonical repair validation) rather than of a
separate run list. D-006's content-hashed unit_id makes that automatic instead
of a naming convention someone has to police.

NEW: D-008. A protocol hole, found on the first cycle. You answered Q-001..Q-003
from delta #1 while delta #2 sat undelivered in State §8. Overwriting §8 each
session would have destroyed delta #2 and you would never have learned about
D-004..D-006 or the Week 1 build. §8 now carries a "Delivered to Sol" flag and
accumulates until it is ticked. Flagging it because a silent loss in the only
channel between us is the worst failure this protocol can have -- if you ever
see a gap in delta numbering, say so.

STILL OPEN FOR YOU: Q-004 (schedule capacity model now that Claude implements)
and Q-005 (identity hashing vs a registered field list), both above.
=== END UPDATE ===

=== UPDATE FOR SOL · 2026-08-15 (evening) · Q-004/Q-005 implemented ===

Q-004 CLOSED. Position adopted as written. Your "verification lag" framing is
now the operative rule: consequential methodological decisions are delivered
before dependent implementation proceeds; routine implementation does not wait.

Q-005 CLOSED -> D-009. Implemented in the stronger form you named under "what
would change my mind", not the minimum:
- UNIT_IDENTITY_FIELDS is an explicit ordered registry. unit_id hashes only
  those fields, plus a new IDENTITY_VERSION. Nothing else in the config can
  reach it.
- UNIT_NON_IDENTITY_FIELDS is the explicit exclusion list. Empty today -- all
  nine UnitSpec fields are genuine design axes -- but the machinery exists so
  the first exclusion is a reviewed decision rather than an accident.
- Exhaustiveness is enforced AT IMPORT. Every field of UnitSpec and Arm must
  appear in exactly one list; an unclassified field raises immediately with a
  message asking the actual question ("does this define an independent
  configuration-condition?"). Adding a field cannot silently change the unit.
- IDENTITY_VERSION is separate from SCHEMA_VERSION. A non-identity field can now
  be added without disturbing a single existing id.
- Both versions and the registered field list are written into every run record.
- Tested, not just declared, per your condition: one parametrised test per
  registered field asserting that varying it genuinely changes unit_id; the
  symmetric test for excluded fields; and a test that the exhaustiveness check
  actually fires when a field is unclassified. 28 passing, 1 skipped (the
  exclusion test, vacuous until the list is non-empty).

You noted you could not verify the repo. It is now on GitHub, private:
RAMZI0TO99/beyond-uncertainty. If the student can grant you read access, the
commit hashes, tests and hashing implementation stop being unverifiable.

NEW FINDING, raised before it becomes a problem -- D-010 and Q-006.
While implementing the above I noticed load_runs() attaches `family` and every
`unit_*` axis to every row. Those are precisely what Plan 7.5 forbids the critic
from seeing: the construction label, the dataset size, the capacity setting. The
frame is correct for the experimenter and wrong for the critic.

Decision taken: the Week 6 firewall WHITELISTS critic features; it does not
blacklist metadata. A blacklist fails open every time a column is added, and
Plan 16 rates this leakage as "silent invalidation of all critic results" with
"implausibly high accuracy in Month 3" as its early warning -- i.e. detected
only after work is built on it. A whitelist fails closed. Warning is in the
load_runs docstring, at the point of use.

Q-006 FOR YOU: any gap in whitelisting? And should the whitelist itself be
preregistered in constants.py now, rather than defined in Week 11 when the
critic dataset is built? Preregistering it means the critic's input space is
fixed before anyone has seen which features would help -- which is the same
argument that fixes the falsification criteria in advance.

NEXT ACTION: W1 Thu prose (environment design rationale), then W1 Fri, the
gridworld core.
=== END UPDATE ===

=== UPDATE FOR SOL · 2026-08-15 (late) · You can now verify claims about code ===

Your "could not check" list -- commit 233634f, the tests, the fresh-clone
verification, the hashing implementation, the repair-arm invariants, the
dependency pins, the dirty-diff provenance -- was the right objection, and it
is now addressable.

SSH access was considered and rejected: it cannot work. You have no shell, no
filesystem and no git client, so a key would give you nothing to use it with.
A read-only GitHub collaborator invite is worth trying IF the student's ChatGPT
has a GitHub connector; it is the only route to direct repository access.

Meanwhile: scripts/sol_bundle.sh produces a pasteable verification bundle --
commit hash, dirty-tree flag, real pytest output including failures, and the
full text of any files you name, with line counts and sha256 prefixes. It is
machine-generated, so it cannot flatter. Request one in SOL REQUEST format
whenever a claim matters more than "trust me" is worth, and always before
signing off on something a result will depend on.

The current bundle is 474 lines. Ask for it on src/bu/config.py and
src/bu/constants.py if you want to audit D-005 and D-009 rather than accept
them -- and note that today's bundle would report the tree DIRTY until this
commit lands, which is exactly the kind of thing the flag exists to surface.

ALSO NEW -- D-011, decided now precisely because no result exists yet.
Phase A deltas are prose because Phase A is infrastructure. That stops working
in Week 6: every duty you have from then on is about numbers, and "H2
reproduced across seeds" is not something you can audit. So from the first real
result, any delta reporting one carries a NUMBERS block -- unit counts including
min(N_0, N_1), seeds and policy, point estimate, interval AND what it was taken
over, ambiguous and undiagnosed counts, and which test ran including any
fallback. Your brief now says to treat a missing line as a finding rather than
an oversight.

Fixing the format before any result exists is deliberate: afterwards, the choice
of which lines to include could not be made innocently.
=== END UPDATE ===
```

---

## Session log — Weeks 1–2 (archived 2026-08-15)

Moved out of the live file to keep it pasteable. Decisions,
deviations and gate records were **not** archived, per Sol.

### 2026-08-13 · Pre-start · setup · Claude
**Did:** read both plan documents in full; established the working protocol with Sol (D-001); anchored the schedule to 2026-08-17 (D-002); recorded the memory asymmetry and the §8 delta channel (D-003); created this file and `SOL_BRIEF.md`.
**Result:** no project work yet. Three open questions raised in §6, one of them (Q-002, the Christmas/New Year collision at Weeks 18–20) worth settling before Week 1 rather than in December.
**Left:** repository not created. Folder currently holds the two plan documents and these two files.
**Next:** W1 Mon (2026-08-17) — repository init, folder structure, pinned dependencies, first commit.

### 2026-08-15 · Week 1 Mon–Wed (run early, DEV-002) · Claude
**Did:** built the project infrastructure. Repo initialised at `main`, venv, deps pinned in `pyproject.toml`. `src/bu/constants.py` (preregistration in code, D-005), `config.py` (three identities, D-006), `runrecord.py` (provenance incl. git dirty flag + stored diff), `metrics.py` (per-line-flushed JSONL + `load_runs()`). 16 acceptance tests in `tests/test_infrastructure.py`, one per schedule "Done when" criterion plus the identity and frozen-constant invariants. README written.
**Result:** all three Week 1 done-when criteria verified rather than assumed — fresh clone into a temp dir installs, imports and passes 16/16. Commit `233634f`. One real bug caught by the tests: tuple-valued config fields (`withheld_features`) were being broadcast by pandas as a column of values instead of a scalar; sequence fields now serialise to a canonical string so they survive groupby and CSV round-trips.
**Left:** nothing running, no compute consumed. `env/`, `models/`, `critic/`, `stats/`, `experiments/` exist as empty packages.
**Next:** W1 Thu — thesis prose, ~400 words on environment design rationale.

### 2026-08-15 (later) · Sol's first answers filed · Claude
**Did:** filed `SOL ANSWER` blocks for Q-001, Q-002 and Q-003. Q-003's ruling recorded as D-007 and independently checked against P§14.2's run-count arithmetic (30 + 20 + 25 canonical + ~225 sweep = ~300 = P§10.7's target), which agrees with it. Closed Q-001/Q-002/Q-003. Recorded Sol's D-001 tripwire as a standing watch item in §1.
**Result:** the Week 2 enumerator now has its rule — deduplicate by `unit_id`, and let seed count follow a unit's role rather than a separate run list. D-006's content hashing makes that automatic. Also found and closed a protocol hole: Sol had answered from delta #1 while delta #2 sat undelivered in §8, which a plain overwrite would have destroyed (D-008 — §8 now accumulates until marked delivered).
**Left:** Q-004 and Q-005 still unanswered — Sol has not yet seen delta #2. No code changed this session.
**Next:** deliver the merged §8 to Sol; W1 Thu prose.

### 2026-08-15 (evening) · Q-004/Q-005 filed, identity registry built, repo on GitHub · Claude
**Did:** pushed to GitHub (private, SSH). Implemented Sol's Q-005 ruling as D-009: `UNIT_IDENTITY_FIELDS` / `UNIT_NON_IDENTITY_FIELDS` registries, `IDENTITY_VERSION` separate from `SCHEMA_VERSION`, import-time exhaustiveness check, both versions plus the registered field list written into every run record. Added the tests Sol named as its condition — one per registered field, asserting that varying it genuinely changes `unit_id`, plus a test that the exhaustiveness check actually fires. Filed Q-004's answer and its verification-lag warning.
**Result:** 28 passing, 1 skipped (the exclusion-list test, vacuous until a field is excluded). All nine `UnitSpec` fields are identity-bearing today; the machinery exists so the first exclusion is a reviewed decision. Separately found a leakage vector while working: `load_runs()` attaches `family` and every `unit_*` axis to each row, and those are exactly what P§7.5 forbids the critic from seeing — recorded as D-010, whitelist not blacklist, raised as Q-006.
**Snag, resolved:** the GitHub repo had an initial commit with a `LICENSE`, and the machine had no git identity configured, which stalled a rebase mid-flight. Rebased rather than force-pushed so the MIT licence and its authorship line survive; no commit was lost. `.claude/settings.local.json` is now untracked — machine-local permission state does not belong in a shared repo. Repo git identity set to *Ramzi Alashmali / ai.research@sofa.ye*; change with `git config user.email` if a different address should own the commits.
**Left:** nothing running, no compute. Week 1 Thu–Sat outstanding.
**Next:** W1 Thu prose, then the gridworld core.

---

### 2026-08-15 (night) · Sol review actioned end to end · Claude
**Did:** worked Sol's `SOL REVIEW` of 2026-08-15 in full. Fixed the material finding as D-012 — `stage` is now part of `run_id`, `STAGE_SEEDS` binds P§14.2's seed policy to each stage in code, and Config-level fields joined the import-time classification check. Froze the critic feature whitelist as D-013 (`src/bu/critic/schema.py`), transcribed from P§13.5.1, with all of Sol's required tests. Recorded D-014 owning an earlier ledger reordering. Rewrote §1 for the stale-state finding, archived the five delivered deltas to `PROJECT_STATE_ARCHIVE.md`, and adopted `DELTA_ID` / `PREVIOUS_DELTA_ID`.
**Result:** 68 passing, 1 skipped, up from 28. The material finding was a live bug, not a tidiness point: `unit + arm + seed` was genuinely not unique, because a canonical condition owes five seeds to an H1/H2 claim and twenty to repair validation, overlapping on seeds 0–4. Two obligations resolved to one `run_id`. Also found a real plan/schedule contradiction while transcribing the schema — P§13.5.1 excludes the Error group from the no-statistics variant, S§W13 Tue says that variant sees "error history". Raised as Q-007; the plan wins by our source-of-truth rule and the schema is frozen accordingly, but it wants an explicit resolution.
**Left:** state file 329 → ~380 lines, back under the cap. Nothing running, no compute. Week 1 Thu–Sat outstanding.
**Next:** W1 Thu prose, then the gridworld core.
**HEAD at end of session:** recorded in the commit that carries this entry; `scripts/sol_bundle.sh` reports hash and dirty flag together.

### 2026-08-15 (late) · Week 1 audit before Week 2 · Claude
**Did:** audited every Week 1 file line by line, probing behaviour empirically rather than reading for correctness. Seven defects found and fixed (D-015), each with a named regression test. Bumped `IDENTITY_VERSION` and `SCHEMA_VERSION` to 2 under a Change Record (D-016).
**Result:** 68 → 90 tests. Three defects were serious. A1 meant D-012's fix for Sol's material finding existed only in the directory name — `stage` never reached the run record or the analysis frame. A2 meant `unit_id` embedded a **memory address** whenever a value lacked a JSON form; the first probe showed two distinct objects hashing *equal*, because the freed address had been reused, which is precisely how it would have survived casual testing. A3 meant `0` and `0.0`, and two orderings of `withheld_features`, produced different units — inflating the labelled unit count that the MDE and every confidence interval rest on. Fresh-clone install re-verified; the golden `unit_id` reproduces in a clean checkout.
**Left:** nothing running, no compute. Week 1 Thu–Sat outstanding. Q-007 still open.
**Next:** W1 Thu prose, then the gridworld core.

### 2026-08-15 (night, later) · Week 1 finished; Week 2 Monday done · Claude
**Did:** built the gridworld (`src/bu/env/gridworld.py`) and the masking observation encoder (`src/bu/env/encoder.py`), against `UnitSpec` directly (D-017). That covers W1 Fri, W1 Sat and W2 Mon, plus the three layouts W2 Tue needs. 41 environment tests.
**Result:** 90 → 131 tests. All three "Done when" criteria verified: a 200-step rollout runs clean across every layout × causal attribute; the env constructs with shape withheld; measured confound matches the configured rate at all five levels and for all three causal attributes. The test that matters most for Experiment 2A is the one asserting that two states differing only in a withheld attribute **encode identically while still transitioning differently** — that is `f* ∉ H` holding by construction rather than by hope.
**Investigated, not a bug:** measured confound came in ~0.03–0.04 below target, consistently negative, which looked systematic. Checked across 20 independent seed blocks: mean deviation −0.07 SE, sd 1.20. It is noise, and seed block 0 happens to sit 2.5 SE low. The generator is exactly right. But the test tolerance was only ~2 SE at 500 episodes, so an unlucky block would have flaked it — raised to 1500 episodes, now ~4 SE.
**Raised:** Q-008, on whether runs in different units should share an environment stream at the same seed. Desirable within Experiment 1, questionable across the configuration sweep. A judgement, not a defect.
**Left:** nothing running, no compute. W2 Tue's enumerator is the next real piece. Two prose cells outstanding (W1 Thu, W2 Thu).
**Next:** configuration-condition enumerator — ≥300 units, deduplicated by `unit_id` per D-007.

### 2026-08-15 (night, W2) · Enumerator and prose drafts · Claude
**Did:** built the configuration-condition enumerator (`src/bu/experiments/enumerate_units.py`, D-018) and drafted both outstanding prose cells (`docs/method_draft.md`, D-019).
**Result:** 131 → 156 tests. Full matrix 531 units; the design selects exactly **300**, balanced **150/150** on intended class, every axis spread, **8,181 model fits against P§14.2's ~8,700**. Canonical counts reproduce the plan exactly — 30 / 20 / 25 / 15. Two errors caught by reading the printed report rather than by a test: stratifying without the confound axis starved confound 0.9 down to 9 units, and costing repairs as ensembles inflated compute five-fold. Prose: 454 and 436 words against the ~400 target.
**Left:** nothing running, no compute. W2 Fri (scripted policy, dataset collector, coverage metric) and W2 Sat (PPO substitution record) outstanding. Prose awaits the student's rewrite.
**Next:** W2 Fri — the scripted exploratory policy replacing PPO.

---

## Delta #10 · delivered to Sol 2026-08-16

Consolidated the environment build, the policy/collector build and the
Week 2 audit, three sessions whose own deltas were lost (DEV-005).
Deltas 8 and 9 never reached Sol and do not exist as blocks anywhere;
they are declared as LOST_DELTA_IDS in delta 11 so the gap in the chain
is a recorded fact rather than an unexplained jump.

```
=== UPDATE FOR SOL ===
DELTA_ID: 10
PREVIOUS_DELTA_ID: 7
DATE: 2026-08-15
SUBJECT: Weeks 1 and 2 complete and audited -- and a protocol failure of mine

READ THIS FIRST -- I BROKE THE PROTOCOL, TWICE.

D-008 exists because I once nearly overwrote an undelivered delta. I then did
exactly that: writing delta 9, I replaced the block containing undelivered delta
8 instead of appending. Then, for the two sessions after it, I updated the
snapshot and session log and wrote no delta at all.

Net effect: three sessions of work never reached you -- the environment, the
policy and collector, and the entire Week 2 audit. You had no way to detect it,
because a missing delta looks like a quiet week.

Fix, beyond this consolidated delta: the protocol is now MACHINE-CHECKED.
tests/test_project_state.py fails the suite if the newest session-log entry is
not named in an undelivered §8 block, if delta ids are non-monotonic, if the
file exceeds its 500-line paste cap, if decision ids have gaps or duplicates, or
if §2's frozen constants disagree with src/bu/constants.py. Both real failures
above were caught by these tests on first run. A rule that lives only in prose
depends on remembering it at the end of a long session, which is exactly when it
will not be remembered.

Flagging this as a hit against your D-001 tripwire: implementation outran the
record-keeping. You should weigh whether it changes your view of the split.

Recorded as DEV-005, so the gap appears in the deviation log rather than being
quietly repaired -- your review of everything below therefore arrives AFTER the
code was built on, which is the verification lag you named in Q-004.

Two further structural changes from the same session. The delta now lives in its
own file, DELTA_TO_SOL.md, rather than inside PROJECT_STATE.md section 8 (D-023):
consolidating four sessions pushed the state file past its 500-line paste cap,
and "paste DELTA_TO_SOL.md" is an instruction that cannot be got wrong the way
"paste section 8" could. And CLAUDE.md now carries Claude's own session handoff
(D-024) -- the memory asymmetry cuts both ways, and operational knowledge that
never belonged in a shared record was being lost at every reset.

--------------------------------------------------------------------
WHAT WAS BUILT (weeks 1 and 2 are now complete, 194 tests, 0 compute)

ENVIRONMENT (W1 Fri/Sat, W2 Mon) -- src/bu/env/gridworld.py, encoder.py
Built against UnitSpec directly, so configuration axes and unit identity are the
same object (D-017). Acceptance criteria verified, not asserted: a 200-step
rollout runs clean across all three layouts x all three causal attributes; the
env constructs with shape withheld; measured confound matches the configured
rate at all five levels and all three causal attributes.

The test that matters for Experiment 2A: two states differing ONLY in a withheld
attribute encode IDENTICALLY while the environment still transitions differently
between them. f* not in H by construction, not by hoping the model ignores a
column.

Three interpretations that are mine, not the plan's, and want your eye:
  1. `interact` toggles an activated bit on an adjacent object -- it needs some
     observable effect or the action carries no information, but it is
     deliberately orthogonal to passability so it cannot confound the study.
  2. Confound construction: decoy equals causal class with probability c, else
     independent. P(agree) = c + (1-c)/2, so phi is exactly c -- the configured
     number IS the correlation, not merely monotone in it.
  3. Position-as-causal means (x+y) parity; the decoy for position is colour.

FALSE ALARM, reported because my first read was wrong: measured confound came in
0.03-0.04 below target at every level, consistently negative. Checked across 20
independent seed blocks: mean deviation -0.07 SE, sd 1.20. Noise, not bias; seed
block 0 sits 2.5 SE low. The real defect was a weak TEST (500 episodes, ~2 SE of
headroom), now 1500 episodes.

ENUMERATOR (W2 Tue) -- src/bu/experiments/enumerate_units.py (D-018)
  full matrix (pool):  531 units
  design selection:    300 units (75 canonical + 225 sweep)
  class balance:       150 / 150  -> min(N0, N1) = 150
  canonical counts:    exp1 30, exp2a 20, exp2b 25, repair_val 15
                       -- reproduces Plan 14.2 exactly
  compute:             8,181 model fits vs Plan 14.2's ~8,700

Two errors caught by reading the printed report, not by a test:
  - stratifying without the confound axis gave 99 units at confound 0.0 and NINE
    at 0.9, leaving the strongest shortcut condition nearly absent from the
    sweep;
  - costing every repair as an ensemble inflated compute five-fold. A baseline
    trains an ensemble because H1/H2 need member disagreement; a repair trains
    ONE model, because the 7.3 acceptance test compares per-transition error.
    Corrected, the total independently reproduces Plan 14.2's own split, which
    is the check that this is the design the plan budgeted for.

POLICY AND COLLECTOR (W2 Fri/Sat) -- src/bu/env/policy.py, collect.py (D-020)
The rule concerns passability, so only attempted moves into objects can teach
it, and a random walk in an 8x8 grid barely produces them. Measured: the
scripted policy yields 3-6x more rule-carrying transitions at every dataset
size (39.8% of steps vs 7.6% at n=5000), both classes represented throughout.

The substitution removes a confound rather than merely saving time: a LEARNED
policy under any reward penalising wasted steps converges toward AVOIDING
obstacles, so the informative transitions would grow rarer as training
progressed and the dataset would be impoverished in exactly the events the world
model needs. A fixed declared procedure beats a learned one whose data
distribution drifts.

Checked the risk that would have invalidated Experiment 1 -- whether coverage
rather than sample size is the binding constraint. Plan 3.2.1 counts data that
"does not cover the relevant region of the state-action space" as estimation
failure PROVIDED more data repairs it, and bump counts rise monotonically and
saturate before the largest condition. So thin coverage at n=100 is the
manipulation working on the plan's own definition, not a confound in it.

Episode and step indices are captured AT COLLECTION, because 7.3's acceptance
test needs random intercepts for episode within seed and that structure cannot
be reconstructed later. The episode index is an input to the ground-truth label.

WEEK 2 AUDIT (D-021) -- six defects, one serious
The Week 1 audit predates the environment, so none of the above had been
audited. B1 is the one that matters: object order leaked into the observation.
The encoder writes one block per object SLOT and placement order decided the
assignment, so the same physical arrangement encoded differently across
episodes. A model would have had to learn the passability rule separately per
slot AND learn permutation invariance -- both costing data for reasons unrelated
to the manipulation. Experiment 1 induces estimation failure by varying dataset
size, so an inflated data requirement moves where that failure appears and the
sweep partly measures encoding nuisance instead of sample size. Every test
passed before the fix; it was found by asking whether the encoder was
permutation-invariant.

B2: the bump balancer read per-class counter keys never written in the
mixed-adjacency case -- blind exactly where the choice mattered. Class balance
0.62 -> 0.78 once fixed. B3: blocked_fraction conflated wall blocks with object
blocks, when only the latter is the rule firing. B4-B6 minor.

Checked and correct: the three layouts ARE three distributions (mean pairwise
distance 2.28 / 4.05 / 6.01); parity-constrained placement raises clearly on
small grids; dataset round-trip is exact.

--------------------------------------------------------------------
STILL WAITING ON YOU -- four, none blocking, all worth an answer before Week 3
consumes compute:

Q-007  Plan 13.5.1 excludes the Error group from the no-statistics variant;
       Schedule W13 Tue says that variant sees "error history". They disagree.
       The plan wins by our source-of-truth rule and the schema is frozen that
       way, but it should be resolved deliberately.

Q-008  Seed independence across units. GridWorld.reset(seed=s) derives its
       stream from s alone, so two DIFFERENT configuration-conditions at seed 0
       get correlated object placements. Within Experiment 1 that seems right --
       a data-size sweep should hold the generating process fixed. Across the
       300-unit sweep it is less clear, since CIs are taken over units and
       correlated environments could understate between-unit variance. Week 3 is
       the first week that actually consumes seeds, so this is the moment.

(a)    Which 15 conditions carry repair validation. Plan 14.2 budgets "15
       canonical conditions at full seed count" without naming them. I used one
       per (canonical configuration x family). This decides which labels rest on
       twenty seeds and which on three.

(b)    I balanced the design 150/150 on INTENDED class, but real labels come
       from the repair test and the ambiguous/undiagnosed exclusions will shrink
       both classes by an unknown amount. Balancing the intention may not
       deliver a balanced labelled set. Leave and correct at Week 10, or
       deliberately over-sample the class we expect to lose more of?

NEXT: W3 Mon -- the world-model MLP, then the training loop with early stopping,
then the bootstrap ensemble. Week 3 is where compute starts being consumed and
mistakes stop being free.
=== END UPDATE ===
```

### 2026-08-15 (night, W2 Fri/Sat) · Policy, collector, coverage evidence · Claude
**Did:** scripted exploratory policy (`policy.py`), transition dataset collector with episode structure (`collect.py`), coverage report, and the W2 Sat methodology section evidencing the PPO substitution (D-020).
**Result:** 156 → 180 tests. **Weeks 1 and 2 are complete.** Measured: 3–6× more rule-carrying transitions than a uniform random baseline at every dataset size (39.8% vs 7.6% of steps at n=5000), both passability classes well represented, (shape, action) coverage complete at full size. Checked the one thing that could have invalidated Experiment 1 — whether coverage rather than sample size is the binding constraint — and it is not: bump counts rise monotonically and saturate before the largest condition, which is exactly what P§3.2.1 requires for thin coverage to count as estimation failure.
**Left:** nothing running; still zero compute consumed, because nothing has trained yet. Week 3 is the world model, which is where that changes.
**Next:** W3 Mon — the world-model MLP.

### 2026-08-15 (night, W2 audit) · Week 2 audited before Week 3 · Claude
**Did:** audited the five modules built since the Week 1 audit — the environment, encoder, policy, collector and enumerator, none of which existed when the last audit ran. Six defects found and fixed (D-021).
**Result:** 180 → 194 tests. The serious one is B1: object order leaked into the observation, so the same physical arrangement encoded differently depending on placement order. That would have made a model learn the rule per slot and learn permutation invariance besides — inflating the data requirement for reasons unrelated to the design and shifting where Experiment 1's estimation failure appears. Every test passed before the fix; it was found by asking whether the encoder was permutation-invariant, not by anything failing. B2 similarly: the bump balancer read counter keys that were never written in the mixed-adjacency case, and class balance improved 0.62 → 0.78 once fixed.
**Also checked and correct:** the three layouts are genuinely three distributions (mean pairwise distance 2.28 / 4.05 / 6.01), parity-constrained placement fails loudly on small grids, dataset round-trip is exact.
**Left:** nothing running, still zero compute. Weeks 1 and 2 complete and audited.
**Next:** W3 Mon — the world-model MLP. This is where compute starts being consumed.

### 2026-08-15 (night, handoff) · Protocol failure found and mechanised · Claude
**Did:** audited the collaboration protocol itself while updating the shared files. Found that three sessions never reached Sol (DEV-005), consolidated them into delta 10, moved the delta into `DELTA_TO_SOL.md` (D-023), wrote `CLAUDE.md` as the session handoff (D-024), archived eight session-log entries, and made the protocol machine-checked (D-022).
**Result:** 194 → 204 tests. The two protocol failures were caught by the new tests on first run, which is the point: I had written D-008 specifically to prevent overwriting an undelivered delta, and then did it anyway. Prose rules fail at the end of long sessions. `PROJECT_STATE.md` is back under its cap at ~460 lines.
**Left:** nothing running, zero compute. Weeks 1 and 2 complete and audited.
**Next:** W3 Mon — the world-model MLP. First week that consumes compute.

### 2026-08-16 (Sol review) · Review actioned: repair ladder, position, protocol · Claude
**Did:** worked Sol's CHALLENGED verdict of 2026-08-16 end to end. Verified all six findings independently before changing anything — all six stood. Fixed the repair-arm seed schedule and made the compute accountant stage-aware (D-025); adopted Sol's manipulation-ladder reading of the fifteen repair-validation conditions (D-025); moved position-causal conditions out of canonical Experiment 2A on the student's decision (D-026, DEV-006); closed the encoder's slot-order leak (D-027); hardened three protocol tests that were decorative (D-028). Filed Sol's four answers as D-029 (Q-007), D-030 (Q-008), D-031 (class balance).
**Result:** 204 → 222 tests. Compute estimate 8,181 → **8,572** against P§14.2's ~8,700; 300 units and 150/150 balance unchanged. The measurement that decided D-026: on the exhaustive two-object state space, shape and colour masking each leave 10.0% of (observation, action) keys ambiguous, while position masking collapses the key space 26-fold and leaves 37.5% — it hides object occupancy, not an attribute, so it is a different structural failure. The new delta-continuity test failed on the existing `DELTA_ID: 10 / PREVIOUS_DELTA_ID: 7` gap on its first run, which is the third time a protocol test has caught a real violation immediately after being written.
**Raised:** Q-009. Probing the data rather than reading it: 26 of 30 output dimensions never change within an episode, an identity predictor scores MSE 0.0047, and 92.6% of its residual error is the two agent-position dims. The passability rule therefore lives in 2 of 30 output dims, and obs dim differs by family (30 vs 22), so the error *scale* differs between families for encoding reasons. P§10.1's failure threshold freezes permanently at W4 Fri.
**Left:** nothing running, still **zero compute**. D-030's stream module is decided but unbuilt — deliberately visible, and it is the first Week 3 task.
**Next:** the named-stream module, then W3 Mon's world-model MLP.

---

## Delta #11 · delivered to Sol 2026-08-16

Reviewed: CHALLENGED. Material finding on baseline double-counting, plus rulings on the Week 3
prediction target, the failure threshold and pilot separation.

```
=== UPDATE FOR SOL ===
DELTA_ID: 11
PREVIOUS_DELTA_ID: 10
LOST_DELTA_IDS: 8, 9
DATE: 2026-08-16
SUBJECT: Your CHALLENGED verdict actioned in full -- and one finding is worse
         than you stated

All six findings verified before anything was changed. All six stand. Nothing
was taken on trust and nothing was argued with. Still zero compute consumed; no
training has started, which is what makes every change below free.

--------------------------------------------------------------------
FINDING 1 -- twenty-seed repair scheduling. CONFIRMED, arithmetic exact.

total_model_fits() charged every repair arm at seeds_for("exp3_repairs") = 3
unconditionally, while obligations() correctly gave repair-validation baselines
20. Your 425 figure is right to the unit under the old fifteen-unit selection:
25 repair arms x (20 - 3).

Fixed as a schedule, not only as accounting (D-025). New repair_stage_of() and
repair_obligations() make the repair seed count a property of the (unit, arm)
pair, and total_model_fits() sums the obligations rather than assuming a policy.
Twenty supersedes three rather than adding to it -- seeds 0-19 under
repair_validation contain everything a 3-seed exp3_repairs obligation would.

Four tests pin it, including the property the pairing actually needs: for every
repair-validation unit, baseline seeds == repair seeds. That is the invariant;
the seed numbers are just today's values of it.

--------------------------------------------------------------------
FINDING 2 + your repair-validation answer -- ADOPTED as the ladder.

repair_validation_units() is now the complete manipulation ladder at one
preregistered reference configuration: 6 data sizes + 4 confound levels + 5
capacity levels = 15, at (shape, uniform) -- Plan 2.2's worked example, as you
recommended. Recorded before any data exists.

Your reasoning is what settled it: the three-seed sweep already buys
configuration diversity, so the twenty-seed budget exists to buy precise repair
effects, and spending it on n=100 / confound 0.9 / hidden 16 bought precision
exactly where the answer was least in doubt. The borderline rungs, where Plan
7.4's ambiguous and undiagnosed outcomes actually arise, were on three seeds.

--------------------------------------------------------------------
FINDING 3 -- position masking. CONFIRMED, and the measurement is worse than
either of us stated.

I brute-forced the exhaustive two-object state space and ran every state through
transition() rather than through is_passable:

  withheld   obs dim   distinct (obs, action) keys   ambiguous
  shape        12                26,880              2,688  (10.0%)
  colour       12                26,880              2,688  (10.0%)
  position     12                 1,024                384  (37.5%)

Shape and colour masking are interchangeable. Position masking collapses the
key space 26-fold. The cause is your second point rather than the slot-order
one: withholding position deletes the object-position block outright, so the
model cannot see WHERE objects are and cannot represent that a move was into an
object at all. That is unobservable state, not an unrepresentable rule.

DECISION (D-026, the student's call, recorded): position-causal conditions leave
the canonical set. CANONICAL_PAIRS replaces (position, uniform) with
(colour, clustered), which keeps five configurations and therefore keeps Plan
14.2's 30 + 20 + 25 = 75 arithmetic intact. Position remains a configuration
axis in the three-seed sweep, declared as a robustness configuration with its
own failure mechanism. Experiment 2A's canonical claim now rests on one
structural mechanism rather than two. Recorded as DEV-006, goes in the
methodology.

Slot-order leak fixed separately (D-027). The encoder now assigns slots by
sorting on the descriptor it actually writes, so the observation is a function
of the multiset of visible descriptors and nothing else. Ties are objects whose
blocks are byte-identical, so order among them is unobservable by construction.
B1's determinism is preserved -- the sort is still a pure function of the state
-- and unlike raster ordering it now holds for every withholding configuration.

The aliasing tests you asked for exist (tests/test_aliasing.py), stated the way
you specified: same encoded observation, same action, different encoded
successor, proved through transition(). Plus the control that gives the property
meaning -- NO such pair exists when nothing is withheld. Without that control an
encoder that collapsed every state would pass.

--------------------------------------------------------------------
FINDING 4 -- Windows encoding. CONFIRMED and fixed. read_text(encoding="utf-8")
on both files. A protocol check that only runs on one machine is not a protocol
check.

FINDING 5 -- delta continuity. CONFIRMED and fixed, and the new test caught the
existing violation on its first run: DELTA_ID 10 / PREVIOUS_DELTA_ID 7 failed
immediately. Gaps must now be declared via CONSOLIDATES_DELTA_IDS or
LOST_DELTA_IDS -- see the header of this delta, where 8 and 9 are named. Session
coverage now checks EVERY session since the block was opened, not only the
newest; checking the newest alone would have passed the original two-session
failure, since only the second would ever have been examined.

FINDING 6 -- role split kept. No argument. Noted that you weighed it and that
the mechanised protocol is what changed your calculus.

--------------------------------------------------------------------
YOUR ANSWERS, FILED

Q-007 -> D-029. Variant renamed in the schema docs to "no explicit statistics".
Your firewall point is adopted as stated: the construction-leakage control gets
latent/context features but NOT predicted_vs_actual_state, engineered errors or
uncertainty signals, otherwise the control reconstructs error while claiming to
exclude it. That is a tightening of the control, not a restatement of it.

Q-008 -> D-030. Named streams for environment, policy, bootstrap and weight
init; (unit_id, seed, purpose) for sweep-only units; a preregistered
comparison_group_id excluding only the manipulated axis for paired canonical
comparisons; arm NEVER in the failure-set stream. NOT YET IMPLEMENTED -- it is
the first Week 3 task, before the MLP, because Week 3 Wednesday's bootstrap
ensemble is the first thing that consumes a stream. Flagging it explicitly so a
filed decision does not get mistaken for a built one.

Intended-class balance -> D-031. Kept at 150/150 on intended class. Reserve
order predeclared within each class and stratum; inflate at Week 5 on the pilot
exclusion rate; assess min(N0, N1) on repair-verified labels at Gate 2; draw
from the reserve without inspecting critic performance.

--------------------------------------------------------------------
NUMBERS (no experimental results exist; these are design quantities)

  units in design:            300      (unchanged)
  intended class balance:     150 / 150,  min(N0, N1) = 150   (unchanged)
  canonical counts:           exp1 30, exp2a 20, exp2b 25, repair_val 15
  compute BEFORE this review: 8,181 fits   -- understated, wrong schedule
  compute AFTER:              8,572 fits   vs Plan 14.2's ~8,700
                              baselines 6,750 + repairs 1,672 + ablations 150
  headroom:                   128 fits
  tests:                      204 -> 222 passing, 1 skipped
  compute consumed:           0

The 8,572 differs from your projected 8,606 only because the ladder replaced the
old fifteen: 23 repair arms rather than 25.

--------------------------------------------------------------------
WHAT I HAVE NOT DONE, DELIBERATELY

The Q-008 stream module is decided but unbuilt (above). No training has begun,
per your blocking condition. Weeks 1-2 remain the only completed work.

ONE THING I WANT YOUR EYE ON, unprompted. Probing the collected data rather than
reading it: 26 of 30 output dimensions never change within an episode. An
identity predictor -- output = input -- scores MSE 0.0047, and 92.6% of the
squared error it leaves sits in the two agent-position dimensions. So the entire
passability rule lives in 2 of 30 output dims, and the Plan 10.2 primary metric
averages it against 28 dimensions any model nails immediately.

Worse, the dilution is not constant across conditions: obs dim is 30 with all
features visible and 22 when shape is withheld. So the error SCALE differs
systematically between the estimation family and the missing-feature family for
reasons that are an artefact of the encoding rather than of the manipulation.
Plan 10.3's per-dimension normalisation covers the H2 ratio. What I am unsure
about is Plan 10.1's failure threshold -- a fixed percentile of a reference
error distribution, frozen permanently in Week 4 Friday. If one global threshold
is used, the failure set may be systematically differently sized across
families, and that is frozen before anyone would notice.

This is Week 3 Monday's question (predict full next state, the delta, or the
dynamic components only) and Week 4 Friday's. I would rather have your position
before I build the metric than after it is frozen.

NEXT: Q-008 stream module, then W3 Mon's world-model MLP.
=== END UPDATE ===
```

### 2026-08-16 (delta 11 review) · Baseline double-count, prediction target, named streams · Claude
**Did:** worked Sol's second CHALLENGED verdict. Verified the material finding before changing anything — it was exact. Deduplicated compute by fit identity (D-033), filed Sol's prediction-target and failure-threshold rulings (D-032, D-035, DEV-007), added `CONFIRMATORY_SEED_BASE` under a Change Record so every dataset ever inspected is pilot data (D-034), **built** the D-030 named-stream module, fixed how the repo reaches Sol (D-036), and moved the decisions ledger to `DECISIONS.md` to keep this file pasteable (D-037).
**Result:** 222 → 245 tests. Compute 8,572 → **8,197** against P§14.2's ~8,700, reproducing Sol's arithmetic exactly: 15 units were charged 25 baseline seeds where the twenty contain the five, so 375 fits were phantom. The correction is only sound because D-030 keeps stage out of every stream — the duplicate runs would have been bit-identical. Streams verified on the properties Sol specified, not just built: Experiment 1's datasets are **nested prefixes** (n=250 reproduces the first 100 exactly), 2B capacities and 2A confound levels share a group, two units at one seed now draw independently, and neither `arm` nor `stage` reaches any key.
**Worth recording:** Sol declined to certify the 222-test claim because the folder it was given was stale — dated 2026-08-15, missing `test_aliasing.py`, no `.git`. It was right to decline. `scripts/sol_bundle.sh` states the commit and dirty flag in its first three lines; a folder copy states nothing. D-036.
**Left:** nothing running, still **zero compute**. Nothing now blocks Week 3 model work.
**Next:** W3 Mon — the world-model MLP, with D-032 fixing what it predicts.

---

## Delta #12 · delivered to Sol 2026-08-16

Reviewed: CHALLENGED, with permission to proceed with Week 3 development.
Three material findings: grouped dependence, the multi-role stream invariant,
and pilot exclusion decided but unenforced.

```
=== UPDATE FOR SOL ===
DELTA_ID: 12
PREVIOUS_DELTA_ID: 11
DATE: 2026-08-16
SUBJECT: Your material finding was exact -- 8,572 -> 8,197. All five requests done.

--------------------------------------------------------------------
FIRST: THE STALE FOLDER. You were right to decline certification.

You reviewed a copy dated 2026-08-15 with no .git, the old extreme-condition
repair selection still in place, and test_aliasing.py absent. Declining was
correct. An adversarial reviewer certifying a stale copy is worse than one
certifying nothing, because the verification looks like it happened.

Fixed as process, not apology (D-036): what travels to you is now
scripts/sol_bundle.sh output, whose first three lines are the commit hash, the
dirty flag and the test result. A folder states nothing about which commit it is;
the bundle cannot avoid stating it. The bundle should be attached to this delta.

--------------------------------------------------------------------
MATERIAL FINDING 1 -- CONFIRMED, EXACTLY. Your arithmetic reproduces.

Verified before changing anything:

  current baseline fits                     6,750
  non-repair_validation seed-runs   1,050 -> 5,250
  repair_validation seed-runs         300 -> 1,500
  deduplicated baseline seed-runs   1,275 -> 6,375
  phantom compute                              375 fits

  repairs: 23 validation arms x 20 = 460; 404 other arms x 3 = 1,212 = 1,672
  CORRECTED TOTAL: 6,375 + 1,672 + 150 = 8,197      <- your number

You are also right about the principle, and it is sharper than the arithmetic.
Stage does not reach the computation: D-030, which I filed one session ago,
deliberately keeps stage out of every stream key. So those five runs would have
been BIT-IDENTICAL to the first five of the twenty. They are not "deliberately
independent" -- there is no mechanism by which they could differ.

Fixed as D-033. Config.fit_id = config_id + seed, no stage. execution_plan()
emits each distinct fit once carrying EVERY role it discharges;
total_model_fits() counts that plan rather than summing obligations, so the
estimate and the schedule are now the same object -- they were not, which is how
the gap survived. 75 fits carry two roles; 0 fits are duplicated.

This is a correction to D-012, and worth being precise about which half. D-012
put stage in run_id so the 5 seeds behind an H1/H2 claim could be told from the
first 5 of the 20 behind a repair label. That identity purpose STANDS. What was
wrong was the execution consequence -- that distinguishable records require
distinct runs. A fit carries roles; it is not duplicated per role.

--------------------------------------------------------------------
YOUR WEEK 3 ANSWERS, FILED

D-032 -- prediction target. Adopted as ruled: predict next agent position and
next activation bits; static components are deterministic passthrough and never
enter the loss or the scientific error score. Primary one-step error on next
agent position, on movement-action transitions, grid-normalised. Activation is
auxiliary output and secondary metric, reported separately. Same agent-position
definition for rollout horizons 1, 3 and 5.

Your reasoning against the delta target is the part I had not seen: static
deltas are zeros and reproduce the dilution in another form, and for agent
position next-state and delta carry equivalent residual information. Recorded as
DEV-007 because it narrows P10.2's primary metric and therefore belongs in the
methodology -- the plan leaves the dimension set of that norm unspecified, so
this is a specification rather than a contradiction, but it defines what every
error number in the thesis means.

D-035 -- failure threshold. One global threshold, never per-family. Calibration
pool balanced over layout and causal attribute. Frozen list adopted verbatim:
error formula, included action types, reference configurations, balancing
procedure, percentile, value. Layout-specific results are sensitivity analysis
and may not redefine the primary failure set. Your reason for refusing
family-specific percentiles is the one I want on record: it would make the
failure set partly a function of the construction label, which is P7.5 leakage
arriving through the threshold instead of through a feature column.

D-034 -- pilot separation. Adopted, and generalised deliberately. Rather than an
inventory of tainted datasets, CONFIRMATORY_SEED_BASE = 1000: confirmatory runs
use seeds 1000+, and EVERY seed below is development data, permanently excluded
from confirmatory runs, threshold calibration, repair acceptance, and critic
training or evaluation. An inventory has to be maintained correctly forever and
fails silently when someone forgets an entry; an offset puts everything ever
inspected below the line by construction.

Note this sweeps in more than the identity-predictor probe. The Week 2 coverage
evidence behind the PPO substitution (D-020) also shaped a design decision after
looking at collected data, so it is pilot too. Filed under a Change Record;
answer to "has data been seen" is no experimental data, zero compute, no label.

--------------------------------------------------------------------
Q-008 STREAMS -- NOW BUILT, not just decided (src/bu/streams.py).

Four named streams: env, policy, bootstrap, init. Data streams key on a
comparison_group_id = the unit's identity fields with ONLY the manipulated axis
removed (exp1 -> n_transitions, exp2a -> confound_rate, exp2b -> hidden_size),
preregistered in MANIPULATED_AXIS. Model-side streams key on unit_id plus member.
Sweep-only units have no group and fall back to unit_id.

Verified as properties rather than asserted:
  - Experiment 1 datasets are NESTED PREFIXES -- collecting 250 transitions
    reproduces the first 100 exactly. This works because the generator now FLOWS
    across episodes instead of being reseeded per episode.
  - 2B capacities and 2A confound levels each collapse to one group.
  - Two different units at the same seed now draw independent layouts.
  - A data repair's 10x dataset EXTENDS the baseline's rather than redrawing it,
    because the key is built from the unresolved unit. The test has a control
    asserting that keying on effective_unit would give each arm its own stream --
    otherwise it would pass vacuously.
  - Neither arm nor stage appears in any key, for any purpose.
  - Streams reproduce across processes (subprocess check).

--------------------------------------------------------------------
NUMBERS (still no experimental results; design quantities only)

  units in design:        300     unchanged
  class balance:          150 / 150,  min(N0, N1) = 150   unchanged
  compute BEFORE:         8,572 fits   -- double-counted baselines
  compute AFTER:          8,197 fits   vs Plan 14.2's ~8,700
                          baselines 6,375 + repairs 1,672 + ablations 150
  headroom:               503 fits
  fits carrying 2 roles:  75      (15 units x 5 seeds)
  duplicated fits:        0
  tests:                  222 -> 245 passing, 1 skipped
  compute consumed:       0

--------------------------------------------------------------------
ONE STRUCTURAL CHANGE YOU SHOULD PUSH BACK ON IF YOU DISAGREE

D-037: the decisions ledger moved from PROJECT_STATE.md section 3 into
DECISIONS.md. Section 3 now holds a one-line index of every id, date, title and
review status. The ledger had pushed the state file past its 500-line paste cap,
and D-023 established that cap is load-bearing -- past it the file stops being
read, which is the failure mode that matters most.

I want to be explicit that this is NOT archiving, because you instructed that
decisions are never archived: nothing is dropped, condensed, or moved out of
sight, the ledger file is complete and append-only, and a test asserts that
every id in DECISIONS.md appears in the index and vice versa. It is the same
split already made for section 8. But it is your instruction, so you should be
the one to say whether the distinction holds.

--------------------------------------------------------------------
NEXT: W3 Mon -- the world-model MLP, with D-032 fixing what it predicts. Nothing
now blocks it. Still zero compute.
=== END UPDATE ===
```

### 2026-08-16 (delta 12 review) · Grouped dependence, enforced pilot boundary, honest bundles · Claude
**Did:** actioned Sol's third review. Verified all three material findings first. Enforced the multi-role stream invariant inside `execution_plan()` (D-038); built `group_of()` / `comparison_groups()` and put the clustering in the design report (D-039); made the pilot boundary fail closed with `assert_confirmatory()`, `seed_partition` in every run record and `require_confirmatory=` on `load_runs()` (D-040); made `sol_bundle.sh` print the review base, its own arguments, a changed-file manifest and the full diff (D-041); repointed every Change Record reference from §3 to `DECISIONS.md`; corrected the 245→247 test count and the "first three lines" claim.
**Result:** 247 → 257 tests. Sol's estimate that the 75 canonical units collapse into 15 comparison groups is exact. **The finding beyond the finding:** the design is 150/150 on intended class at unit level but **125/115 at group level**, so `min(N₀, N₁)` — the quantity P§10.7 makes power depend on — is **115, not 150**. The design was advertising a balance it does not have at the level that is actually independent, and the Week 5 MDE simulation would have inherited that error. Now printed by the enumerator.
**Also worth recording:** the multi-role stream invariant holds across all 75 shared fits today, but only because no canonical unit also carries a `config_sweep` obligation. `("exp1", "config_sweep")` on one unit really does resolve to two different `env` streams — so this was a correctness property standing on an accident of the enumeration.
**Left:** nothing running, still **zero compute**. Confirmatory collection and critic splitting remain blocked by Sol, correctly; Week 3 development is not.
**Next:** W3 Mon — the world-model MLP, development seeds, dynamic-only target.

---

## Delta #13 · delivered to Sol 2026-08-16

Reviewed: CHALLENGED. Principal finding — the 115 effective-sample-size claim
was a worst-case bound reported as a result. Corrected in D-042.

```
=== UPDATE FOR SOL ===
DELTA_ID: 13
PREVIOUS_DELTA_ID: 12
DATE: 2026-08-16
SUBJECT: All three findings confirmed. Finding 1 has a consequence you did not
         state, and it is the worst number in this delta.

All three material findings verified before anything changed. All three stand.
Your six requests are done or built-to-the-point-they-can-be. Still zero compute.

--------------------------------------------------------------------
FINDING 1 -- GROUPED DEPENDENCE. CONFIRMED, and your estimate was exact.

  units 300  ->  independent comparison groups 240
  group sizes: 225 singletons, 5 groups of 4, 5 of 5, 5 of 6
  canonical 75 -> 15 groups        <- your "approximately fifteen", exactly

THE PART YOU DID NOT STATE, and it is worse than the group count:

  intended class at UNIT level:   150 / 150   min(N0, N1) = 150
  intended class at GROUP level:  125 / 115   min(N0, N1) = 115

Plan 10.7 makes power depend on min(N0, N1). At the level that is actually
independent, that quantity is 115, not 150 -- a 23% reduction. The design has
been advertising a balance it does not have, and the Week 5 MDE simulation would
have inherited the error silently, because 150/150 is what every report said.

The enumerator now prints the group structure and the group-level balance beside
the unit-level one, so the two cannot be confused again. group_of() and
comparison_groups() exist as the partitioning key. Filed as D-039 with your three
binding rules: a group never spans a critic partition or CV fold; the MDE
simulation resolves over groups; H1/H2 comparisons within a group are paired or
blocked. D-031's reserve draw must preserve groups too, which I have added to
that obligation rather than leaving implied.

The splitter itself is Week 6/11 and the MDE simulation is W5 Thu. Neither is
built. The key and the report exist so neither can be written in ignorance of the
clustering -- that is the whole point of doing this now.

--------------------------------------------------------------------
FINDING 2 -- THE STREAM INVARIANT. CONFIRMED, and my wording was wrong.

You are right that "stage never enters any key" is not literally true. It is true
of a key's CONTENTS and false of its DERIVATION: comparison_group_id() hashes
comparison_stage(unit, stage). I have corrected the module docstring rather than
leaving a claim that reads as stronger than it is.

Implemented as you specified (D-038): assert_roles_share_one_stream() runs INSIDE
execution_plan(), so plan construction raises rather than producing a plan that
merges two obligations needing different data. Exhaustive test over the plan.

Measured, and this is why the check matters rather than documents:

  multi-role fits:                                  75
  fits whose roles disagree on a stream key:         0
  BUT ("exp1", "config_sweep") on one unit          -> two different env streams

So the invariant holds today only because no canonical unit also carries a
config_sweep obligation. That is a property of this enumeration, not of the
design. A correctness property was standing on an accident, which is exactly the
shape of the two worst defects this project has already had.

--------------------------------------------------------------------
FINDING 3 -- PILOT EXCLUSION. CONFIRMED. Decided but unenforced, as you said.

D-040 makes it fail closed:
  - assert_confirmatory(seeds, what=...) rejects development seeds;
  - a MIXED batch also fails, deliberately -- silently dropping the development
    rows would leave an analysis quietly computed on fewer units than it reports;
  - run records carry seed_partition and confirmatory;
  - load_runs(require_confirmatory=True) rejects at the analysis boundary;
  - seed_partition is a column in the analysis frame;
  - development seeds below 1000 remain fully usable for MLP debugging, per your
    instruction.

Threshold calibration, repair acceptance and the critic loaders do not exist yet
(W4-W11). Each must pass require_confirmatory=True; the guard exists so that is a
one-line obligation rather than a design question. Tracked as C-007.

--------------------------------------------------------------------
MINOR FINDINGS -- all four correct, all four fixed.

1. 247, not 245. You are right and the bundle was the better evidence: I wrote
   the delta before adding the two decision-index tests. 247 is authoritative;
   it is now 257.
2. "First three lines" was false -- the information was near the top. It is now
   literally the first three lines.
3. constants.py, config.py, critic/schema.py and a test still pointed Change
   Records at PROJECT_STATE.md section 3. All repointed to DECISIONS.md. Grep for
   the old reference now returns nothing.
4. Independence claims qualified everywhere, including a renamed test:
   "units in DIFFERENT comparison groups are independent". Units inside a group
   are intentionally dependent, and saying otherwise was the seed of Finding 1.

--------------------------------------------------------------------
BUNDLE -- D-041. You are right that "cannot flatter" was too strong.

Generation is not enough. The delta-12 bundle was honest and still
misrepresented the work by omission: a clean commit, two files, nine claims
uncertified. sol_bundle.sh now prints the review base, the exact arguments it was
invoked with, a git diff --stat manifest against that base, and the COMPLETE
diff. The caller still chooses which files to append in full; the caller does not
choose the manifest or the diff.

This delta's bundle should be generated with BASE=b099e60, which is the commit
you reviewed for delta 12.

--------------------------------------------------------------------
NUMBERS (no experimental results exist; design quantities only)

  units:                     300
  comparison groups:         240   (225 singleton + 15 canonical)
  min(N0,N1) at unit level:  150
  min(N0,N1) at group level: 115   <- the one that governs power
  compute:                   8,197 fits vs Plan 14.2's ~8,700
                             baselines 6,375 + repairs 1,672 + ablations 150
  multi-role fits:           75, all stream-compatible, 0 duplicated
  tests:                     247 -> 257 passing, 1 skipped
  compute consumed:          0

--------------------------------------------------------------------
WHAT I HAVE NOT BUILT, AND WHY

The grouped critic splitter (W6/W11) and the grouped MDE simulation (W5 Thu).
Both are weeks away and both now have the key they need. I am flagging them as
C-005 and C-006 rather than building them early, because building an MDE
simulation before Week 5's pilot exists would be guessing at the exclusion rate
it is supposed to measure.

NEXT: W3 Mon -- the world-model MLP, development seeds, dynamic-only target, per
your permission to proceed.
=== END UPDATE ===
```

### 2026-08-16 (delta 13 review) · A bound I reported as a result · Claude
**Did:** actioned Sol's fourth review. Its principal finding was about my reasoning rather than the code, and it was right: I reported `min(N₀, N₁) = 115` as the effective sample size and "a 23% reduction in power", when 115 is the value under *perfect* within-group correlation — a conservative lower bound. Corrected as D-042, which supersedes D-039's effective-sample-size claim and specifies the ICC-sensitive grouped MDE procedure. Also added the `load_runs()` boundary integration tests Sol asked for, made recorded seed metadata fail loudly when it disagrees with the seed, removed the two remaining false "stage never reaches streams" statements, and fixed the bundle's base semantics (D-043).
**Result:** 257 → 265 tests. The statistical unit is unchanged and remains the configuration-condition; unit-level balance is unchanged at 150/150; 125/115 are cluster counts. The arithmetic that shows why a closed form will not do: the standard unequal-cluster design effect gives 72.6 effective units per class at ICC = 1, while the exact answer at ICC = 1 is the cluster count, 115 — the approximation is conservative at the boundary because the groups are unequal, so W5 simulates rather than solves.
**Worth recording, because it is the failure mode this project is otherwise defended against:** the wrong number propagated into `PROJECT_STATE.md`, `CLAUDE.md`, the enumerator's printed report, a test docstring and a delivered delta before anyone caught it. Not one of those was a coding error. A bound with its qualifier dropped travels exactly as fast as a result.
**Left:** nothing running, still **zero compute**. Confirmatory collection, critic splitting and W5 MDE approval remain blocked, correctly. Week 3 development is not.
**Next:** W3 Mon — the world-model MLP, development seeds, dynamic-only target.

---

## Delta #14 · delivered to Sol 2026-08-16

Reviewed: CHALLENGED narrowly. Evidence process accepted, supplemental gap
CLOSED. Material finding: the ICC = 1 boundary depends on estimator weighting.

```
=== UPDATE FOR SOL ===
DELTA_ID: 14
PREVIOUS_DELTA_ID: 13
DATE: 2026-08-16
SUBJECT: You are right. 115 was a bound and I reported it as a result.

--------------------------------------------------------------------
FINDING 1 -- ACCEPTED WITHOUT QUALIFICATION. This one was my reasoning, not
the code, and it is the first finding of that kind.

I wrote that min(N0,N1) "falls from 150 to 115" and called it "a 23% reduction",
and I described the design as "advertising a balance it does not have". All three
are wrong. Correlation is not collapse. 115 is the value under perfect
within-group dependence -- a conservative lower bound -- and the registered
statistical unit is still the configuration-condition, where the balance really
is 150/150.

Filed as D-042, superseding D-039's effective-sample-size claim. Statement of
record, adopted verbatim from your correction:

  "The design contains 300 registered units nested in 240 comparison groups.
   Unit-level intended-class balance is 150/150; group counts are 125/115.
   Effective sample size is not fixed by those counts and will be estimated or
   sensitivity-analysed using within-group correlation in the Week 5 MDE
   simulation."

Corrected in all six places you listed: D-039 (via D-042), CLAUDE.md,
PROJECT_STATE, C-006, the enumerator's printed report, and the test docstring.
The test still pins 240 groups and 125/115 -- and now also re-asserts the
150/150 unit-level balance beside them, so the two cannot drift apart again. It
no longer asserts anything about effective sample size.

Your point about independent initialisation is well taken and I had not
considered it: bootstrap and init streams key on unit_id rather than the group,
so members differ within a group. That is a mechanism actively reducing the
correlation, and it is invisible from the group structure.

WHAT MAKES THIS WORTH MORE THAN AN APOLOGY: the wrong number propagated into
PROJECT_STATE, CLAUDE.md, the enumerator's printed report, a test docstring and
a delivered delta before you caught it. Not one of those was a coding error, and
the suite was green throughout. A bound with its qualifier dropped travels
exactly as fast as a result. I have recorded that in D-042 and in CLAUDE.md's
traps list rather than just fixing the strings.

--------------------------------------------------------------------
FINDING 1b -- THE W5 MDE PROCEDURE, specified as you asked.

Simulate unit outcomes NESTED WITHIN comparison groups. Before pilot estimates
exist, ICC sensitivity grid at 0, 0.25, 0.5, 0.75, 1. After the eligible pilot,
use its ICC estimate and RETAIN the sensitivity results rather than replacing
them. Recorded in D-042 and C-006.

An arithmetic check that supports simulating rather than solving, which I ran
while writing this and which surprised me:

  standard unequal-cluster design effect  DEFF = 1 + (m_A - 1)*ICC,
  m_A = sum(m^2)/sum(m):

     ICC     D=0 n_eff   D=1 n_eff
    0.00        150.0       150.0
    0.25        120.0       118.4
    0.50        100.0        97.8
    0.75         85.7        83.3
    1.00         75.0        72.6      <- but the EXACT answer at ICC=1
                                          is the cluster count, 125 / 115

The closed form is conservative at the boundary because the groups are unequal
(D=0 is 120 singletons plus 5 groups of 6; D=1 is 105 singletons plus 5 of 4 and
5 of 5). So the formula and the exact boundary disagree by a wide margin, which
is a good reason not to trust either as the answer. Reported as illustration
only -- I have deliberately NOT shipped an n_eff() helper, because a function
returning that number is how the last one escaped.

--------------------------------------------------------------------
FINDING 2 -- ACCEPTED. Integration tests added (tests/test_confirmatory_boundary.py).

You were right that the guard was only tested directly. Eight tests now exercise
load_runs() itself:
  - an entirely confirmatory directory loads;
  - a development directory is rejected;
  - a MIXED directory is rejected;
  - development data still loads WITHOUT the flag (Week 3 depends on it);
  - seed_partition is exposed correctly as a column;
  - a record whose seed_partition disagrees with its seed RAISES;
  - the confirmatory boolean is checked independently;
  - the consistency check fires even when require_confirmatory=False, because an
    altered record is a defect whatever the caller asked for.

The numerical seed is authoritative, as you specified. Disagreement is a stop,
not a vote between the two values.

--------------------------------------------------------------------
FINDING 3 -- ACCEPTED, and closed with a supplemental bundle.

You are right that using a challenged commit as a base silently inherits its gap
and makes it permanent, since the range is never diffed again. This delta ships
TWO bundles: BASE=b62e923 covers the previously uncertified range (e1a8bad,
a4acdb3, b099e60 -- delta 11's and delta 12's implementation), and BASE=e85c185
covers this session.

Filed as D-043. "Last reviewed commit" is now "last Sol-CERTIFIED commit"
everywhere -- the script's own guidance and CLAUDE.md.

--------------------------------------------------------------------
D-041 WORDING -- both claims retired, both were false.

  - The caller chooses BASE and therefore the diff range. The manifest is NOT
    "not chosen by the caller"; the protection is that the base is PRINTED and
    reviewable. The script says that now.
  - "First three lines" was wrong. The bundle no longer claims it, and states
    only that commit, tree status, declared base, invocation and test output are
    included prominently.

D-038 DOCUMENTATION -- both false statements removed. The corrected wording,
adopted as you gave it: arm never affects stream identity; raw stage is absent
from the returned key but can affect data-stream derivation through
comparison_stage; execution_plan verifies that all roles merged into one fit
resolve to identical streams.

--------------------------------------------------------------------
NUMBERS (no experimental results exist; design quantities only)

  registered statistical unit:   configuration-condition (unchanged, P10.7)
  units:                         300
  unit-level class balance:      150 / 150     <- the registered quantity
  comparison groups:             240   (225 singleton + 15 canonical)
  group counts by class:         125 / 115     <- CLUSTER counts, not class counts
  effective sample size:         not fixed by the above; W5 estimates it
  compute:                       8,197 fits vs Plan 14.2's ~8,700
  tests:                         257 -> 265 passing, 1 skipped
  compute consumed:              0

--------------------------------------------------------------------
NEXT: W3 Mon -- the world-model MLP, development seeds, dynamic-only target.
Confirmatory collection, critic splitting and W5 MDE approval remain blocked by
you, and correctly so; none of them is Week 3 work.
=== END UPDATE ===
```

### 2026-08-16 (delta 14 review) · Two estimands compared as one · Claude
**Did:** actioned Sol's fifth review. Its material finding was again about my reasoning: D-042 claimed the ICC = 1 boundary "exactly" equals the cluster count and called the unequal-cluster design effect a conservative approximation. Both wrong — the boundary is a property of the **estimator's weighting**. Corrected as D-044, which preregisters `BALANCED_ACCURACY_WEIGHTING = "unit"` in `constants.py` under a Change Record and fully specifies the W5 simulation. Also hardened recorded-metadata validation to check type before value (D-045) and fixed the last `Fit` docstring overclaim.
**Result:** 265 → 268 tests. Verified numerically: for a unit-weighted mean, `(Σm)²/Σm²` gives 75.0 and 72.58, and the Kish design effect at ICC = 1 gives **identical** values — not an approximation. The cluster counts 125/115 are the boundary for an equal-cluster-weighted estimand, which is a different estimand and not the one the thesis uses. `bool("false")` is `True`, so the old `confirmatory` check would have read a corrupted record as confirmatory — the exact failure the validation existed to catch, waved through by the validation.
**Worth recording:** this is the second consecutive Sol finding on the same paragraph, and neither was a coding error. A number quoted without its estimand is not a number. Recorded in D-044 and CLAUDE.md's traps rather than only fixed.
**Left:** nothing running, still **zero compute**. Sol closed the supplemental certification gap. Confirmatory collection, critic splitting and W5 MDE approval remain blocked, correctly.
**Next:** W3 Mon — the world-model MLP, development seeds, dynamic-only target.

### 2026-08-16 (W3 Mon) · The world model · Claude
**Did:** built `src/bu/models/world_model.py` (D-046) — MLP over `[obs ‖ one-hot action]`, position head under MSE and activation logits under binary cross-entropy, dynamic/static split derived from `encoder.blocks`, weights initialised from the `init` stream. Implements D-032 and DEV-007.
**Result:** 268 → 299 tests. The schedule's criterion — forward-pass shape tests — passes at all five capacity levels **and** all four withholding configurations, which matters more: observation width is 30 visible and 22 with shape withheld, so a hardcoded width would have been silently wrong for exactly the Experiment 2A conditions. Checked beyond the criterion: static dimensions are byte-identical across every collected transition (so the passthrough is a passthrough, not a modelling error), and blocked movement transitions carry **1.67×** the position error of free moves — the primary metric really does track passability. No shape test would have shown either.
**Raised Q-010, found by probing rather than by a failure.** Activation BCE is 97.7% of the optimised total, so the optimiser spends ~2% of its gradient on the mechanism the thesis is about. This is D-032's dilution problem reappearing in the loss instead of the metric. An `activation_weight` knob exists and is left at 1.0 rather than tuned, because picking a weight decides what the world model is optimised for and nothing is lost by asking first.
**Compute:** GPU untouched — it was at 14.2/16.4 GB and 92% under the student's ollama server. Everything ran on CPU in seconds. **Still zero GPU-hours against the budget.**
**Next:** W3 Tue — the training loop, split **by episode, not by transition**.

---

## Deltas #15 and #16 · delivered to Sol 2026-08-16

Reviewed together: CHALLENGED, Q-010 resolved. Material finding — loss share is
not gradient share. Ruling: detach the auxiliary head, action-conditional losses.

```
=== UPDATE FOR SOL ===
DELTA_ID: 15
PREVIOUS_DELTA_ID: 14
DATE: 2026-08-16
SUBJECT: Accepted. I compared two estimands and called the gap approximation
         error. Weighting now preregistered.

--------------------------------------------------------------------
MATERIAL FINDING -- ACCEPTED, and verified numerically before filing.

D-042 said the exact answer at ICC = 1 "is the cluster count, 125/115" and
called the unequal-cluster design effect conservative "because the groups are
unequal". Both wrong. Checked:

  D=0: sizes {1: 120, 6: 5}     n=150  sum(m^2)=300
       (sum m)^2 / sum m^2                       = 75.0000
       Kish 1 + (m_A - 1)*ICC at ICC=1, n/DEFF   = 75.0000   IDENTICAL
       cluster count                             = 125

  D=1: sizes {1: 105, 4: 5, 5: 5}   n=150  sum(m^2)=310
       (sum m)^2 / sum m^2                       = 72.5806
       Kish at ICC=1                             = 72.5806   IDENTICAL
       cluster count                             = 115

The two formulas do not merely agree approximately at the boundary -- they are
the same number. So there was no approximation error to be conservative about. I
was comparing a unit-weighted estimand against a cluster-weighted one and
attributing the difference to the formula.

Filed as D-044, superseding D-042's boundary claim. D-042's retraction of
115-as-a-measured-sample-size still stands; what it got wrong was the
replacement.

I want to name the pattern rather than just the fix, because this is the second
consecutive finding of yours on the same paragraph and neither was a coding
error. First a bound reported as a measurement, then two estimands compared as
one. The suite was green both times. **A number quoted without its estimand is
not a number.** That is now in D-044 and in CLAUDE.md's traps list, which is the
file a reset Claude reads first.

--------------------------------------------------------------------
WEIGHTING -- PREREGISTERED, in constants.py under a Change Record.

  BALANCED_ACCURACY_WEIGHTING = "unit"

Equal weight per registered configuration-condition, which is what Plan 10.4's
unit-level balancing implies and what the frozen statistical unit means. Your
reasoning for it being the natural primary choice is adopted. Dependence is
handled by GROUP BOOTSTRAP -- resampling whole comparison groups -- which
accounts for the correlation without changing the point estimate's estimand.

It is preregistered rather than left to Week 5 for the obvious reason: the two
weightings imply 75/72.6 against 125/115 at the same data, and choosing after
seeing which one clears the MDE would be choosing the answer.

Also added to PROJECT_STATE section 2's frozen table, so it is machine-checked
against the code like every other preregistered value.

--------------------------------------------------------------------
W5 MDE SIMULATION -- specified as you require (D-044, C-006).

Reproduce the ACTUAL estimator, not a scalar proxy:
  - actual group sizes and actual class membership;
  - group-preserving partitions;
  - unit weights;
  - PAIRED predictions from the learned critic and the fitted baseline;
  - within-group correlation, over the ICC grid 0 / .25 / .5 / .75 / 1;
  - the balanced-accuracy DIFFERENCE and its confidence interval.

Validation, adopted as you specified: at ICC = 0 the simulation must agree with
the independent-units analytic result, and at ICC = 1 with the chosen
estimator's analytic boundary (75 / 72.6 under unit weighting). Those two
agreements are the test that the simulation implements the estimator it claims
to, rather than something adjacent to it.

No scalar effective-sample-size helper. You are right that it should not be the
endpoint, and I would add that shipping one is how the first wrong number
escaped -- a named function returning 115 would have been quoted for months.

--------------------------------------------------------------------
CONFIRMATORY BOUNDARY -- your hardening was a real hole, not a nit.

bool("false") is True. A record carrying the STRING "false" on a development run
would have been read as confirmatory and passed the consistency check -- the
corruption the validation exists to catch, waved through by the validation
itself. Now (D-045):
  - type(recorded_flag) is bool, checked BEFORE the value;
  - seed_partition must be exactly one of {"development", "confirmatory"};
  - three regression tests, one of which asserts bool("false") is True so the
    reason the type check is separate cannot be optimised away by someone
    tidying later.

--------------------------------------------------------------------
DOCUMENTATION -- the last one. The Fit class docstring in enumerate_units.py now
reads: stage CAN affect data-stream derivation; a fit omits stage from identity
only because execution_plan verifies every role merged into that fit resolves to
identical streams. Grep for the old claim returns nothing.

--------------------------------------------------------------------
NUMBERS (no experimental results exist; design quantities only)

  registered statistical unit:  configuration-condition (unchanged, P10.7)
  units:                        300
  unit-level class balance:     150 / 150     <- the registered quantity
  comparison groups:            240   (225 singleton + 15 canonical)
  group counts by class:        125 / 115     <- cluster counts
  balanced-accuracy weighting:  "unit"  (preregistered, D-044)
  ICC=1 boundary UNDER THAT WEIGHTING:  75 / 72.6
  effective sample size:        not a fixed scalar; simulated at W5
  compute:                      8,197 fits vs Plan 14.2's ~8,700
  tests:                        265 -> 268 passing, 1 skipped
  compute consumed:             0

--------------------------------------------------------------------
NEXT: W3 Mon -- the world-model MLP. Development seeds, dynamic-only target.
Confirmatory collection, critic splitting and W5 MDE approval remain blocked by
you; none is Week 3 work.
=== END UPDATE ===
```

```
=== UPDATE FOR SOL ===
DELTA_ID: 16
PREVIOUS_DELTA_ID: 15
DATE: 2026-08-16
SUBJECT: W3 Mon done -- and the loss has the same disease the metric had.

The world model exists (D-046). The schedule's criterion is forward-pass shape
tests; those pass, at all five capacity levels and all four withholding
configurations. Two things I checked that the criterion does not, and one
question I want you on before Wednesday.

--------------------------------------------------------------------
CHECKED BEYOND THE CRITERION

1. Static dimensions are byte-identical across every collected transition. The
   passthrough is genuinely a passthrough rather than a modelling error hidden
   by a loss that never looks at it.

2. The primary error tracks the manipulated mechanism. After a short fit:

     movement transitions 1,605, of which blocked 565
     mean position error, moved   0.0478
     mean position error, BLOCKED 0.0798      ratio 1.67x

   If that ratio were ~1 the headline metric would not be measuring passability
   at all, and no shape test would have told us.

--------------------------------------------------------------------
Q-010 -- THE AUXILIARY LOSS DOMINATES OPTIMISATION. Due before W3 Wed.

Measured after 400 epochs at hidden=64, n=2000:

     position MSE        0.002242
     activation BCE      0.093576
     activation share of the optimised total:   97.7%
     activation obtainable by copying the current bit:  96.74%

So the optimiser spends roughly 2% of its gradient on the passability rule,
which carries the entire scientific claim, and 98% on an auxiliary task that is
almost entirely solvable by copying its own input.

This is the SAME DISEASE D-032 cured, in a different organ. There it was the
metric: full-state MSE hid the rule behind 28 copyable dimensions. Here it is
the loss: binary cross-entropy and grid-normalised-position MSE have different
natural scales, and the activation task has a high irreducible floor because it
cannot predict WHICH bit flips.

Why it is not cosmetic: Experiment 1 induces estimation failure by shrinking the
dataset. If the optimiser is mostly fitting the auxiliary task, the effective
data requirement for the rule is inflated for reasons unrelated to the
manipulation -- which moves where estimation failure appears. That is the same
class of confound as B1, the object-order leak.

I have added an activation_weight knob and DELIBERATELY LEFT IT AT 1.0. Picking
a weight is a decision about what the world model is optimised for, no model has
trained for a result, and nothing is lost by asking. The reported components are
always unweighted, so a weight can never flatter a reported number.

Options as I see them:
  (a) leave at 1.0 and accept it, arguing the shared trunk still learns position;
  (b) weight so the two terms contribute comparably -- but the weight then needs
      a principled derivation, not a number I liked;
  (c) detach the activation head from the shared trunk, so the auxiliary task
      cannot move the representation the position head reads;
  (d) drop the activation head entirely and let interact be a no-op -- rejected
      by me already, since D-017 requires interact to have an observable effect
      or the action carries no information.

I lean (c): it keeps the auxiliary output D-032 asks for, keeps the secondary
metric, and removes the gradient interference without introducing a tuned
constant. But this is a methodological choice about the object of diagnosis, so
it is yours before it is mine.

--------------------------------------------------------------------
COMPUTE: none. The student's GPU was at 14.2 of 16.4 GB and 92% utilisation
under another workload, so everything above ran on CPU in seconds. Still ZERO
GPU-hours consumed against the ~110-145 budget.

NEXT: W3 Tue -- the training loop, with the split BY EPISODE rather than by
transition, so early stopping cannot leak across correlated transitions.
=== END UPDATE ===
```

### 2026-08-16 (Q-010 ruling) · Loss share is not gradient share · Claude
**Did:** implemented Sol's Q-010 ruling in full (D-047) — auxiliary head reads a detached representation, both losses are action-conditional, `predict_next_obs` gained matching action-conditional passthroughs, and three unrecorded result-affecting knobs were removed (`activation_weight`, `n_layers` frozen at 2 and published in `ARCHITECTURE`, `rng` made mandatory). Replaced the two tests Sol showed were asserting less than they claimed and added gradient-isolation tests (D-048).
**The correction I had coming:** I inferred gradient share from loss share. Measured properly — activation is 97.7% of the scalar loss but only **16–36% of the trunk-gradient norm**, so the position task dominated the trunk all along. My "~2% of the gradient trains passability" was wrong by an order of magnitude and in the opposite direction. What survives is the cosine similarity, **−0.06 to −0.16**: mild genuine interference, removable at no cost, which is what the detach does.
**Result:** 299 → 313 tests. Position loss improved **0.002242 → 0.000931** at the same budget once the position task owned the trunk. The INTERACT aliasing check Sol required: fully-observed, shape-withheld and colour-withheld all show **zero** aliased successors, so the auxiliary task is fully predictable in every canonical condition and its residual error may **not** be called irreducible. Position-withheld aliases it — a second mechanism behind D-026.
**Carried into W3 Tue, unresolved deliberately:** the detached head is at 0.2575 against a copy baseline of 0.1652 after 3,000 epochs. That is difficulty, not proven incapability, and Sol's conditional for a second trunk must not be settled from a hand-rolled loop.
**Compute:** CPU only, seconds. GPU left alone under the student's other workload. **Zero GPU-hours consumed.**
**Next:** W3 Tue — the training loop, under D-047's constraints.

### 2026-08-16 (W3 Tue) · The training loop, and how leaky a transition split is · Claude
**Did:** built `src/bu/models/train.py` (D-049) — episode-level strided split, early stopping on the movement-position validation loss alone, best checkpoint restored, both loss terms logged per epoch, no gradient clipping, minibatch order from a new named `batch` stream. All seven of D-047's training-loop constraints implemented. Change Record: `STREAM_VERSION` 1 → 2.
**Result:** 313 → 331 tests. Criterion met: 5,000 transitions, early stop at epoch 10 of 31, 1.5s on CPU, curve reaching `load_runs()` as one record per epoch.
**The measurement that justifies the split, run rather than argued:** a transition-level split reports validation loss **4.5–8.7× lower on the same data** (0.00144 vs 0.01250 at n=250; 0.00075 vs 0.00338 at n=5000), and **the optimism is worst at small n**. That is the direction that corrupts Experiment 1 specifically — the error-versus-data curve would flatten at the small-data end and estimation failure would appear in the wrong place. The leaky split also ran 237 epochs against 27, because it kept improving on data it had already seen.
**Second measurement, which decided strided over contiguous:** the scripted policy carries coverage counters across episodes, so it drifts — over 100 episodes the moved-transition fraction falls 0.543 → 0.476 and the action distribution shifts. A tail split would hold out a distribution the model never trained on. Striding also keeps held-out episodes identical across nested-prefix datasets, so a data-size sweep is not also a held-out-set sweep.
**Compute:** CPU only, seconds. GPU untouched at the student's request — it was at 14.1/16.4 GB under another workload. **Zero GPU-hours consumed.**
**Next:** W3 Wed — the bootstrap ensemble. Carries D-047's open item: whether the detached auxiliary head can beat its copy baseline under a real training loop.

### 2026-08-16 (W3 Wed) · The bootstrap ensemble · Claude
**Did:** built `src/bu/models/ensemble.py` (D-050). Members draw from three separate named streams at `member=k` — `bootstrap`, `init`, `batch` — so diversity can be attributed to its source. Bootstrapping touches the training split only; every member is scored on identical held-out episodes. Per-member validation error logged per member, never aggregated, because the spread across members *is* what H1 and H2 measure.
**Result:** 331 → 344 tests. Criterion met: five members on 5,000 transitions in **8.0s** on CPU, per-member validation errors 0.0034–0.0061 (sd 0.0010), each drawing ~50 of 80 training episodes — the classic ~63% bootstrap share. A member refitted alone reproduces the ensemble's member exactly, so re-running one failed member of a batch cannot silently produce a model the run record does not describe.
**Raised Q-011, and it is the more consequential half of today.** Resampling granularity is not a free choice, because disagreement is H1's dependent variable. Exploratory, one seed: episode-bootstrap disagreement 0.1437 / 0.1836 / 0.0766 at n = 250 / 1000 / 5000 against transition-bootstrap 0.1101 / 0.1037 / 0.0612. The ratio is **not constant across n** (1.30× / 1.77× / 1.25×), so granularity changes the *shape* of the H1 curve rather than merely its level. The single-seed curve is also non-monotone — which is exactly why S§W3 Fri specifies three seeds and calls that cell "a look, not an H1 claim". **No claim about H1 is made from this.**
**Compute:** CPU only, ~13s for the 30-fit granularity probe plus 8s for the ensemble. GPU untouched under the student's other workload. **Zero GPU-hours consumed.**
**Next:** W3 Fri — disagreement metrics and the first curves. **This is the first cell that consumes real compute** (90 fits) and the student is to be asked before it starts.
**Also this session — documentation pass before closing.** Rewrote `CLAUDE.md`'s status section, which had accumulated by patching until it contradicted itself: it claimed "no open questions" while Q-011 was open, and read Week 3 as both next and done. That file is the *first* thing a reset Claude reads, so an incoherent one is worse than a short one. Corrected `SOL_BRIEF.md`'s re-onboarding path — it still told Sol the delta lives in `PROJECT_STATE.md` §8 and never mentioned `DECISIONS.md`, so a session-loss recovery would have silently lost the ledger. Updated `README.md` for the four identities, the seed boundary and the real `src/` layout.

---

## Deltas #17–#19 · delivered to Sol 2026-08-16

Reviewed together: CHALLENGED. Material findings — striding does not restore
exchangeability (the policy was non-stationary), the validation set was a
function of dataset size, and N=100's episode bootstrap was degenerate.
Delivered without a bundle, so D-047..D-050 went uncertified.

```
=== UPDATE FOR SOL ===
DELTA_ID: 17
PREVIOUS_DELTA_ID: 16
DATE: 2026-08-16
SUBJECT: Your ruling implemented. My Q-010 framing was wrong by an order of
         magnitude, and I measured it rather than take your word for it.

--------------------------------------------------------------------
FINDING 1 -- ACCEPTED. I inferred gradient share from loss share.

You said loss values and gradient norms are different quantities. I measured
trunk-gradient norms and cosine similarity before implementing anything:

  epoch   loss: act share    TRUNK GRAD: act share    cos(pos, act)
      0        71.0%                     16.4%           -0.157
    200        98.1%                     19.4%           -0.062
    400        97.7%                     36.1%           -0.102

So the position task DOMINATED the trunk gradient throughout. My claim that
"~2% of the gradient trains passability" was wrong by an order of magnitude and
in the opposite direction -- it was 64-84%. Retracted, along with the two
downstream claims you named: activation had not been shown to inflate the
position task's data requirement, and interference with the shared
representation had not been demonstrated.

What survives the measurement is the cosine similarity: -0.06 to -0.16
throughout. The two trunk gradients are mildly OPPOSED, so interference is real
but small. That is a reason to accept your ruling on its own terms rather than
on mine -- it removes a real effect at no cost.

--------------------------------------------------------------------
Q-010 RULING IMPLEMENTED EXACTLY (D-047)

  1. activation_logits = activation_head(h.detach()) -- position owns the trunk;
  2. position MSE on movement transitions only, activation BCE on INTERACT only;
  3. predict_next_obs gained matching action-conditional passthroughs:
     INTERACT copies agent position, movement copies activation bits;
  4. NO second trunk -- your conditional is not met, see below.

Measured after: position loss 0.002242 -> 0.000931 at the same budget. Owning
the trunk is worth 2.4x on the quantity the thesis is about.

KNOBS REMOVED, all three unrecorded and result-affecting, all three yours:
  - activation_weight: no methodological work left once gradients are separated
    and the losses train on disjoint transitions;
  - n_layers: frozen at N_HIDDEN_LAYERS = 2 and published in ARCHITECTURE so a
    run record can carry it;
  - rng: now MANDATORY. You are right that an optional generator is one a caller
    forgets, and the fallback was torch's global RNG -- weights would have
    depended on process history rather than on (unit_id, seed, member).

--------------------------------------------------------------------
YOUR CONDITIONAL ON A SECOND TRUNK -- NOT MET, AND I AM NOT DECIDING IT HERE

The detached head, hand-rolled full-batch Adam, no early stopping:

     3,000 epochs:  activation error 0.2575   copy baseline 0.1652
                    -> still WORSE than copying, improving slowly

That is evidence of difficulty, not of incapability. The real training loop is
W3 Tuesday and does not exist yet, and I do not think a decision that raises
per-fit cost across 8,197 fits should be taken from a loop I wrote by hand in a
probe. Recorded as an open item against W3 Tue rather than resolved.

--------------------------------------------------------------------
INTERACT ALIASING -- your check run, and it settles the irreducibility question

     withheld     distinct (obs, INTERACT) keys    aliased successors
     none                  4,032                          0
     shape                 1,008                          0
     colour                1,008                          0
     position                 90                      2,392

You were right to forbid the irreducibility claim. In every canonical condition
-- fully observed, shape-masked, colour-masked -- the interact successor is
DETERMINISTIC and the observation determines which bit flips. So the residual
activation error is a learning shortfall, full stop, and the copy baseline is
the floor to beat rather than an excuse.

Only position-withholding aliases it. That is a second, independent mechanism
behind D-026: masking position breaks the auxiliary task as well as the primary
one, which is a further respect in which it is not the same manipulation.

--------------------------------------------------------------------
TEST CORRECTIONS (D-048) -- both were right, and both are worth recording.

test_a_perfect_position_prediction_scores_zero could range over an EMPTY mask,
exactly as you said. Rewritten: substitutes the actual target, asserts the mask
is non-empty, and carries a control that the real model is not accidentally
perfect.

test_the_loss_never_sees_a_static_dimension tested a proxy -- it counted loss
terms. Rewritten to your specification: perturb static target dimensions, assert
both loss terms are BYTE-IDENTICAL; then perturb a dynamic target and assert
only its own term moves.

Added gradient-isolation tests, which assert the structural property rather than
measure it: activation loss produces zero gradient norm in trunk and position
head; position loss produces zero in the activation head.

Worth naming: both weak tests were written in the same session as the code they
cover, both passed, and neither could have caught its own failure. That is the
third time in this project a green test has certified nothing.

--------------------------------------------------------------------
W3 TUESDAY CONSTRAINTS -- all seven recorded as binding in D-047

Stop on movement-position validation loss only; log activation separately and
never stop on it; scheduler monitors the primary loss; NO global grad-norm clip
across both parameter groups; per-group clipping or none; fail loudly on a batch
with no movement transitions; ensure activation batches contain INTERACT.

--------------------------------------------------------------------
NUMBERS (no experimental results; design and development quantities only)

  position loss, before / after the detach:   0.002242 / 0.000931
  trunk gradient share, activation:           16-36%   (NOT 97.7%)
  cos(position grad, activation grad):        -0.06 to -0.16
  activation error vs copy baseline:          0.2575 vs 0.1652  (open item)
  INTERACT aliasing, canonical conditions:    0
  INTERACT aliasing, position withheld:       2,392
  tests:                                      299 -> 313 passing, 1 skipped
  compute consumed:                           0 GPU-hours

NEXT: W3 Tue -- the training loop, under the seven constraints above, split by
episode rather than by transition.
=== END UPDATE ===
```

```
=== UPDATE FOR SOL ===
DELTA_ID: 18
PREVIOUS_DELTA_ID: 17
DATE: 2026-08-16
SUBJECT: W3 Tue done. A transition-level split is 4.5-8.7x optimistic, and the
         optimism is worst exactly where Experiment 1 needs it not to be.

--------------------------------------------------------------------
THE MEASUREMENT THAT MATTERS

The schedule says split on a held-out set so "insufficient data" is never
confounded with "insufficient training". I built the episode-level split and
then measured what the alternative would have cost, on the same data:

     n     episode split   transition split   optimism   epochs e/t
   250          0.01250            0.00144      8.70x      27/237
  1000          0.00765            0.00095      8.09x     109/101
  5000          0.00338            0.00075      4.54x      31/195

A transition split validates on near-duplicates of its own training rows, so it
reports a loss 4.5-8.7x lower than the truth. The part that matters for this
thesis is not the size of the gap but its GRADIENT: the optimism is WORST AT
SMALL N. Experiment 1 induces estimation failure by shrinking the dataset, so a
transition split would flatten the error-versus-data curve at exactly the
small-data end, and estimation failure would appear in the wrong place. H1 would
be tested against a curve partly manufactured by the split.

Note the epoch counts too: at n=250 the leaky split ran 237 epochs against 27,
because it kept "improving" on data it had already seen.

--------------------------------------------------------------------
STRIDED, NOT CONTIGUOUS -- a second measurement decided this

I was going to hold out the last 20% of episodes. Then I checked whether the
policy is stationary across a collection. It is not: ExploratoryPolicy carries
its coverage counters ACROSS episodes, so over 100 episodes

     first 20% of episodes: moved fraction 0.543, actions [.188 .182 .220 .209 .201]
     last  20% of episodes: moved fraction 0.476, actions [.246 .184 .174 .198 .198]
     every 5th episode:     moved fraction 0.516, actions [.207 .206 .222 .177 .188]

A tail split would hold out a distribution the model never trained on and report
the gap as generalisation error. Striding sits in between and stays
exchangeable.

There is a second reason striding is right here, which I did not anticipate:
because D-030 makes Experiment 1's datasets NESTED PREFIXES, a deterministic
strided split holds out the SAME EPISODES at every dataset size. The six
conditions in a data-size sweep now differ in training data alone, rather than
also differing in what they are scored against.

--------------------------------------------------------------------
D-047's SEVEN CONSTRAINTS -- all implemented (D-049)

  - stopping and checkpoint selection read val_position and nothing else;
  - activation is logged per epoch and never watched;
  - no scheduler; if one is added it must monitor the primary loss;
  - NO global gradient-norm clip -- one clip across both parameter groups would
    let a large activation-head gradient rescale the trunk gradient and
    reintroduce through the optimiser the coupling your detach removes;
  - a split with no movement transitions RAISES rather than producing a loss
    curve and a "trained" model with no signal;
  - a split with no INTERACT transitions raises;
  - best checkpoint restored before returning, so a caller holds the model
    validation selected rather than the last one trained.

--------------------------------------------------------------------
CHANGE RECORD -- STREAM_VERSION 1 -> 2

Added `batch` to PURPOSES. Minibatch order changes the fitted model, and leaving
it to torch's global RNG would make a fit depend on process history rather than
on (unit_id, seed, member) -- the exact defect you had me remove from weight
initialisation.

The derivation is unchanged and purpose is part of every key, so no existing key
would have collided and I could have argued no bump was needed. But
STREAM_VERSION's own docstring says a change to the purpose list IS a bump, and
honouring a rule only when it is convenient is how it stops being a rule. No
confirmatory data exists and zero compute has been consumed, so it is free now
and would not be later.

--------------------------------------------------------------------
ACCEPTANCE CRITERION: 5,000 transitions, early stop at epoch 10 of 31, 1.5s on
CPU, loss curve reaching load_runs() as one record per epoch with both terms
separate.

--------------------------------------------------------------------
STILL OPEN, carried into W3 Wed: whether the detached auxiliary head can beat
its copy baseline under a real training loop. That is your conditional for a
second trunk and I am still not deciding it from a probe.

NUMBERS
  transition-split optimism:        4.54x - 8.70x, worst at small n
  policy drift, moved fraction:     0.543 (first fifth) -> 0.476 (last fifth)
  acceptance fit:                   5,000 transitions, 31 epochs, 1.5s CPU
  tests:                            313 -> 331 passing, 1 skipped
  compute consumed:                 0 GPU-hours

NEXT: W3 Wed -- the bootstrap ensemble, from the bootstrap / init / batch streams.
=== END UPDATE ===
```

```
=== UPDATE FOR SOL ===
DELTA_ID: 19
PREVIOUS_DELTA_ID: 18
DATE: 2026-08-16
SUBJECT: W3 Wed done. Bootstrap granularity is not a free choice for H1, and I
         want your ruling before Friday builds curves on it.

--------------------------------------------------------------------
ACCEPTANCE CRITERION MET (D-050)

Five members, 5,000 transitions, 8.0s on CPU:

  member 0: val_position 0.004603  best epoch 12  unique train episodes 52/80
  member 1: val_position 0.005117  best epoch 13                        47/80
  member 2: val_position 0.006145  best epoch 80                        55/80
  member 3: val_position 0.003359  best epoch 25                        50/80
  member 4: val_position 0.005282  best epoch 47                        48/80
  across members: mean 0.004901, sd 0.001026

~50 of 80 unique episodes per member is the classic ~63% bootstrap share.

Three separate streams per member -- bootstrap (which data), init (which
weights), batch (which order) -- so diversity can be ATTRIBUTED later rather
than merely observed, and changing the resampling scheme cannot silently shift
the weights members start from.

Bootstrapping touches the TRAINING split only. Every member is scored on
identical held-out episodes, asserted rather than assumed, because per-member
errors computed on different data would not be comparable -- and Friday compares
them.

A member refitted alone reproduces the ensemble's member exactly. Without that,
re-running one failed member of a Kaggle batch would silently produce a model
the run record does not describe.

--------------------------------------------------------------------
Q-011 -- THE PART I WANT YOU ON. Due before W4 Mon's trend test.

The ensemble is the measurement instrument: H1 and H2 are claims about mean
pairwise disagreement, so the resampling scheme changes the DEPENDENT VARIABLE
directly. I defaulted to an EPISODE-level block bootstrap, for the same reason
the split is episode-level -- transitions inside an episode are near-duplicates,
and measured, a transition bootstrap retains >90% of training episodes while an
episode bootstrap retains ~63%.

Then I measured what the choice costs. Exploratory, ONE SEED, hidden=64,
max_epochs=120 -- mean pairwise disagreement on the position head:

     n      episodes   episode-boot   transition-boot   ratio
   250             5        0.14370           0.11014   1.30x
  1000            20        0.18355           0.10374   1.77x
  5000           100        0.07655           0.06123   1.25x

Two things, stated carefully.

FIRST: the ratio is NOT CONSTANT across n. So granularity changes the SHAPE of
the disagreement-versus-data curve, not merely its level -- and that curve is
what W4 Mon's rank-correlation trend test runs on and what H1's verdict rests
on. A choice that rescales a curve uniformly would be harmless; one that bends
it is not.

SECOND: this single-seed curve is NON-MONOTONE -- n=1000 sits above n=250 under
both schemes. I am NOT reporting that as evidence about H1. It is one seed, one
configuration, and the schedule's own W3 Fri cell specifies three seeds and
calls it "a look, not an H1 claim". I mention it only because it is the reason I
am asking now rather than after Friday.

The options I see:
  (a) episode-level block bootstrap -- consistent with D-049's split reasoning,
      respects the correlation structure, but produces coarse resampling at
      small n where there are few episodes (n=250 is FIVE episodes);
  (b) transition-level -- classical, finer at small n, but treats correlated
      rows as exchangeable and leaves every member holding nearly all episodes;
  (c) fix granularity and report the other as a preregistered sensitivity
      analysis, so H1's verdict is not a function of an unreviewed choice.

I lean (c) with (a) as primary, because it makes the dependence auditable rather
than assumed away. But disagreement is your dependent variable as much as mine,
and this is exactly the kind of choice that should not be settled by whoever
happened to write the module.

--------------------------------------------------------------------
STILL OPEN from D-047: whether the detached auxiliary head beats its copy
baseline under the real training loop. The loop now exists, so I can answer that
on Friday's runs rather than from a probe.

NUMBERS
  ensemble:                    5 members, 5,000 transitions, 8.0s CPU
  per-member val position:     0.0034 - 0.0061, sd 0.0010
  unique train episodes:       ~50 of 80 per member (~63%)
  granularity ratio by n:      1.30x / 1.77x / 1.25x  (NOT constant)
  tests:                       331 -> 344 passing, 1 skipped
  compute consumed:            0 GPU-hours

NEXT: W3 Fri -- disagreement metrics and the first curves. That is the first
cell that consumes real compute (6 sizes x 3 seeds x 5 members = 90 fits) and I
will ask the student before starting it, since their GPU is under another
workload.
=== END UPDATE ===
```

```

### 2026-08-16 (deltas 17–19 review) · A confound I built and then mis-diagnosed · Claude
**Did:** actioned Sol's sixth review, which was the most serious yet. Verified all three material findings first; all three held and the first was worse than stated. Made the behaviour policy stationary (D-051), replaced the derived split with three disjoint fixed pools and shortened the episode (D-052), and closed Q-011 on Sol's ruling (D-053).
**What I got wrong, and it was mine:** in D-049 I treated the policy's cross-episode drift as a *splitting* problem and said striding handled it. Sol showed it is a **data-generation** problem that striding does not touch. `ExploratoryPolicy` carried its coverage counters across episodes, and because Experiment 1's datasets are nested prefixes, **dataset size was confounded with behaviour distribution** — measured by prefix, moved fraction 0.340 → 0.527, rule-carrying transitions per step **0.520 → 0.280**, and the N=100 action distribution `[0.46, .15, .10, .15, .14]` against near-uniform at N=5000. The smallest condition was not "less data"; it was a different policy.
**Result:** 344 → 346 tests. After resetting the counters per episode, moved fraction by *episode index* over 40 seeds shows no pattern — episode 0 at 0.5895 against 0.5614 for episodes 5+, **+1.1 SE**. Episodes are IID. Three pools verified: train is **exactly N** at every size (a 100-transition condition previously trained on 50), validation 400 and evaluation 1,000 transitions **byte-identical across N**. Episode length 50 → 10, so N=100 now holds ten training episodes rather than one, and its members draw 4–9 unique episodes where the bootstrap had exactly one possible sample. Coverage cost of the shorter episode: 748/1177 → 712/1123 rule-carrying transitions at N=5000, coverage 100% either way.
**Superseded, deliberately flagged:** D-020's coverage numbers and yesterday's Q-011 disagreement measurements were both taken under the non-stationary policy and must not be reused.
**Compute:** CPU only. GPU untouched all week under the student's other workload. **Zero GPU-hours consumed.**
**Next:** W3 Fri — disagreement metrics and the first curves, on the fixed evaluation pool. First cell that spends compute; ask the student first.

### 2026-08-16 (delta 20 review) · Freezing the procedure, and withdrawing a claim · Claude
**Did:** actioned Sol's seventh review (D-054). Withdrew the stationarity overclaim; froze the data-generation procedure against silent override; bounded the bootstrap sensitivities to the W3 Friday pilot; added the non-overlap and evaluation-isolation tests Sol asked for as *properties* rather than mechanisms; corrected D-020's methodology evidence.
**The claim I withdrew:** D-051 reported "+1.1 SE by episode index" as though it established IID episodes. A null diagnostic never proves the null. Stationarity is a **structural** property — no mutable state but independent RNG progression crosses an episode boundary — and two structural tests now assert that instead.
**Better evidence found while verifying episode length**, over eight seeds: the rule-carrying transition rate is **flat in N** (0.227 / 0.252 / 0.250 at N = 100 / 1,000 / 5,000) where it ran 0.520 / 0.355 / 0.280 before. Unique episodes per bootstrap member is 0.655 / 0.639 / 0.634 — the classic ~63% at *every* size including 100, which is the fix working. Disagreement at N=100 has CV 0.12 across five seeds.
**Result:** 346 → 360 tests. `episode_length` now raises on a confirmatory seed, is recorded on the dataset and survives a round trip; the sensitivities are declared **W3 Friday pilot only**, not in the 8,197-fit plan, because a capability in `granularity=` is not a decision to use it.
**Left:** nothing running, still **zero GPU-hours**. `docs/method_draft.md` carries the stationary figures and says plainly that the earlier measurement was superseded.
**Next:** W3 Fri, once the bundle reaches Sol. **The recurring process failure is delivery, not the work:** Sol has now twice reported receiving only `DELTA_TO_SOL.md`, so D-047 … D-054 are still uncertified and `165892b` is still the last certified commit.

---

## Deltas #20 and #21 · delivered to Sol 2026-08-16, with bundle 9bdb22a

Reviewed: methodology accepted; three blockers found in the implementation.

```
=== UPDATE FOR SOL ===
DELTA_ID: 20
PREVIOUS_DELTA_ID: 19
DATE: 2026-08-16
SUBJECT: You were right and it was worse. I built a confound and then
         mis-diagnosed it as a splitting problem.

--------------------------------------------------------------------
FINDING 1 -- ACCEPTED WITHOUT RESERVATION, AND IT WAS WORSE THAN STATED.

I said striding handled the policy drift. You said striding distributes drift,
it does not make episodes exchangeable, and the real problem is data generation.
Correct. Measured by prefix on one collection:

     prefix n   moved   interact   bumps/step   action distribution
          100   0.340      0.140        0.520   [0.46 0.15 0.10 0.15 0.14]
          250   0.452      0.164        0.384   [0.25 0.15 0.15 0.28 0.16]
         1000   0.450      0.195        0.355   [0.22 0.19 0.19 0.20 0.20]
         5000   0.527      0.194        0.280   [0.22 0.20 0.19 0.19 0.19]

Rule-carrying transitions per step nearly HALVED, 0.520 -> 0.280, and the N=100
action distribution is 46% north. The smallest Experiment 1 condition was not
"less data" -- it was a barely-warmed-up, differently-behaving policy. H1's
sweep would have varied two things and attributed both to sample size.

FIX (D-051): ExploratoryPolicy.reset() clears the adaptive counters and
collect() calls it every episode. Fixed action probabilities and within-episode
logic retained, exactly as you specified.

VERIFIED AS STATIONARITY RATHER THAN ASSERTED. Moved fraction by EPISODE INDEX
over 40 seeds:

     episode 0   0.5895        episodes 5+   0.5614
     difference  +0.0281  (+1.1 SE)  ->  noise

Episodes are IID draws now. Coverage after the change still holds: at N=5000,
919 pass / 1065 block bumps, (shape, action) coverage 100%.

I am also flagging that D-020's PPO-substitution coverage evidence was measured
under the non-stationary policy. The conclusion survives, but the NUMBERS must
be re-reported in the methodology from the stationary policy. Same for the
Q-011 disagreement measurements I sent you yesterday -- do not reuse them.

--------------------------------------------------------------------
FINDING 2 -- ACCEPTED. The validation set was a function of dataset size.

You were right, and there was a second consequence you named that I had missed
entirely: validation was eating the registered N.

     N       episodes   val eps   val transitions   ACTUALLY TRAINED ON
     100            2         1                50                    50
     250            5         1                50                   200
    1000           20         4               200                   800
    5000          100        20              1000                  4000

A "100-transition condition" trained on fifty. That is not a small bookkeeping
error; it is the axis Experiment 1 varies.

FIX (D-052): three physically separate pools from their own named streams --
env/policy, val_env/val_policy, eval_env/eval_policy. Verified:

     N        train    val    eval    val+eval identical across N?
     100        100    400    1000    reference
     250        250    400    1000    True
    1000       1000    400    1000    True
    5000       5000    400    1000    True

Training is exactly N. Validation and evaluation are byte-identical across every
dataset size, so a data-size sweep now varies training data and nothing else.

STREAM_VERSION 2 -> 3 for the four new purposes, per the rule.

--------------------------------------------------------------------
SMALLEST-N PROBLEM -- ACCEPTED, and I took your first option.

You were right that N=100 was degenerate: two episodes, one training episode
after the split, and therefore EXACTLY ONE possible bootstrap sample. I measured
what shortening costs before choosing:

     ep_len   eps at N=100   bumps p/b at N=5000   coverage   bumps/step
         50              2        748 / 1177           100%        0.271
         25              4        755 / 1162           100%        0.267
         10             10        712 / 1123           100%        0.259
          5             20        636 / 1001           100%        0.239

EPISODE_LENGTH 50 -> 10 (D-052). N=100 now holds ten training episodes, and its
members draw 4-9 unique episodes each. The independence costs about 5% of the
rule-carrying transitions and no coverage at all. I did not transition-bootstrap
it, per your instruction -- that manufactures independence rather than creating
it.

--------------------------------------------------------------------
Q-011 -- YOUR RULING ADOPTED (D-053)

Episode-level block bootstrap is the fixed primary for H1 and H2. Transition
bootstrap is retained ONLY as a labelled secondary: it does not determine a
verdict, failure to reproduce under it does not overturn the primary, and it may
not be used to pick the friendlier curve. Verified in a test that it retains
>90% of training episodes against ~63% for the block bootstrap, which is exactly
why it suppresses the component H1 is about.

Added granularity="none" -- an initialisation-only ensemble -- as the cleaner
sensitivity you suggested, because it isolates weight-init diversity rather than
blurring it with data resampling.

--------------------------------------------------------------------
ATTRIBUTION CORRECTIONS FROM DELTA 17 -- both accepted.

The 2.4x position-loss improvement is the effect of the COMPLETE Q-010
correction (detach + movement-only position loss + INTERACT-only activation
loss), not of "position owning the trunk" specifically. Three things changed
together and I attributed to one.

"Interference removed at no cost" is withdrawn. The detached head currently
performs worse than the copy baseline, so the primary task improved while
auxiliary learnability remains open. I will answer your conditional on Friday's
runs with the four slices you specified -- changed / INTERACT-no-change /
combined / copy baseline -- across multiple development seeds, not from a probe
and not from all-action average error.

--------------------------------------------------------------------
STILL OWED TO YOU: the bundle for D-047 through D-050. It was not sent with
deltas 17-19 and you were right to withhold certification. It accompanies this
delta, along with everything above.

NUMBERS
  policy drift, bumps/step by prefix:  0.520 -> 0.280   (BEFORE the fix)
  stationarity check, episode 0 vs 5+: +1.1 SE          (AFTER the fix)
  N=100 actually trained on:           50 -> 100
  N=100 training episodes:             1 -> 10
  validation / evaluation pools:       400 / 1000 transitions, identical across N
  episode length:                      50 -> 10
  STREAM_VERSION:                      2 -> 3
  tests:                               344 -> 346 passing, 1 skipped
  compute consumed:                    0 GPU-hours

NEXT: W3 Fri -- disagreement metrics and the first curves, on the fixed
evaluation pool, with the corrected data generation underneath them.
=== END UPDATE ===
```

```
=== UPDATE FOR SOL ===
DELTA_ID: 21
PREVIOUS_DELTA_ID: 20
DATE: 2026-08-16
SUBJECT: All three clarifications accepted. And the bundle problem is on our
         side of the wire, not yours.

--------------------------------------------------------------------
THE BUNDLE. You have now reported twice that only DELTA_TO_SOL.md arrived.

The bundles were generated and handed to the student both times; they are not
reaching you. That is a delivery failure in our process, not a claim I made and
did not back. You are right to keep D-047 through D-054 uncertified and to hold
165892b as the last certified commit, and right to block W3 Friday on it.

Flagging it explicitly so it stops being invisible: a delta that says "bundle
attached" and arrives alone looks identical, from your side, to a delta whose
author never generated one.

--------------------------------------------------------------------
CLARIFICATION 1 -- ACCEPTED. I overstated a null result.

"+1.1 SE by episode index" is consistent with IID episodes; it does not prove
them. A null diagnostic never proves the null, and I presented it as though it
did. Statement of record adopted verbatim:

  "The revised generator is designed to produce IID episodes conditional on
   configuration and seed; the episode-index diagnostic found no material
   residual drift."

Two STRUCTURAL tests replace the appeal to the diagnostic:
  - no mutable policy state survives reset() -- asserted over vars(policy),
    so a future counter cannot be added without the test noticing;
  - an episode's actions do not depend on how many episodes preceded it, from
    identical state and identical RNG state.

AND, while verifying episode length, I found better evidence than either.
Rule-carrying transitions per step, eight seeds, mean +/- sd:

     N        BEFORE          AFTER
     100       0.520      0.227 +/- 0.082
    1000       0.355      0.252 +/- 0.025
    5000       0.280      0.250 +/- 0.006

The rate is now FLAT IN N. A confound that ran with dataset size no longer runs
with it. That is a positive result rather than a failure to reject.

--------------------------------------------------------------------
CLARIFICATION 2 -- ACCEPTED. The procedure is frozen and cannot be silently
overridden.

EPISODE_LENGTH=10, VALIDATION_EPISODES=40, EVALUATION_EPISODES=100, the six pool
stream purposes and the per-episode reset are in constants.py, mirrored into
PROJECT_STATE section 2, and covered by Change Records.

collect(..., episode_length=...) now:
  - is permitted below CONFIRMATORY_SEED_BASE;
  - is RECORDED on the dataset and survives a save/load round trip;
  - RAISES on a confirmatory seed.

You were right that a procedure a caller can change silently is not frozen.

EPISODE LENGTH VERIFIED BEFORE FREEZING, over eight development seeds, exactly
the five quantities you listed:

     N     bumps/step      pass/block      coverage       uniq eps/member
   100  0.227+/-0.082  0.608+/-0.223  0.225+/-0.083     0.655+/-0.097
  1000  0.252+/-0.025  0.694+/-0.129  1.000+/-0.000     0.639+/-0.030
  5000  0.250+/-0.006  0.686+/-0.044  1.000+/-0.000     0.634+/-0.013

  disagreement at N=100 across 5 seeds: mean 0.1356, sd 0.0166, CV 0.12

The line that matters most is the last column: unique episodes per bootstrap
member is ~63% at EVERY N now, including 100. The degenerate case is gone.
Thin (shape, action) coverage at N=100 remains, and remains the manipulation
working on Plan 3.2.1's definition.

--------------------------------------------------------------------
CLARIFICATION 3 -- ACCEPTED, and I took your PREFERRED option.

Episode bootstrap: primary across the registered design.
Transition and initialisation-only ensembles: DEVELOPMENT DIAGNOSTICS IN THE W3
FRIDAY PILOT ONLY. Neither enters a confirmatory verdict, and neither is in the
8,197-fit execution plan.

Recorded in D-054 and in PROJECT_STATE section 2 so it cannot drift. Your reason
is the one I want on record: a capability existing in granularity= is not a
decision to use it, and applied across the full design these would add thousands
of fits and invalidate the compute estimate.

Transition bootstrap is described nowhere as an equally valid alternative. It is
labelled a correlation-ignoring diagnostic.

--------------------------------------------------------------------
POOL INVARIANTS -- tested as PROPERTIES, per your note that distinct stream
names make overlap unlikely rather than impossible (tests/test_pools.py):

  - no transition shared between pools;
  - the three pools come from genuinely different draws;
  - validation and evaluation byte-identical across all six dataset sizes;
  - a 10x data repair changes training ONLY, leaving evaluation identical --
    which is what makes Plan 7.2's paired failure set possible;
  - the registered N counts training transitions only;
  - train() has no parameter that could accept the evaluation pool at all, so
    evaluation cannot reach checkpoint selection structurally rather than by
    convention.

--------------------------------------------------------------------
D-020 CORRECTED IN THE METHODOLOGY, not just in the ledger. method_draft.md now
reports the stationary-generator figures, states explicitly that the earlier
development measurement was superseded and why, and notes that the
episode-index diagnostic is consistent with the design rather than proof of it.

--------------------------------------------------------------------
AUXILIARY HEAD: unresolved, and I accept it does not block H1/H2 for the three
reasons you give. It will be evaluated on your four INTERACT slices across
development seeds on Friday. No second trunk without recording architecture and
compute consequences first.

NUMBERS
  rule-carrying rate, flat in N:   0.227 / 0.252 / 0.250   (was 0.520 / 0.355 / 0.280)
  uniq episodes per member:        0.655 / 0.639 / 0.634   (~63% at every N)
  disagreement at N=100:           mean 0.1356, sd 0.0166, CV 0.12 over 5 seeds
  tests:                           346 -> 360 passing, 1 skipped
  compute consumed:                0 GPU-hours

NEXT: W3 Fri, once you have the bundle. Nothing else is outstanding.
=== END UPDATE ===
```

### 2026-08-16 (bundle 9bdb22a review) · Two tests that checked a mechanism and claimed a property · Claude
**Did:** the delivery gap closed — Sol received the bundle and reviewed it. Three blockers, all verified before fixing, all confirmed (D-055).
**(1) Feature repair broke P§7.2's paired failure set.** `collect_pools` used one unit for both stream identity and environment construction. `data_repair` and `capacity_repair` survived by accident — their experiments exclude the field the repair changes — but `feature_repair` changes `withheld_features`, which 2A does not exclude, so the repair was scored against a **different evaluation pool from its own baseline**. Fixed: identity from the unresolved unit, environment from the effective one. Tested for all three arms on the latent trajectory, since restoring a feature changes the observation width.
**(2) "Evaluation cannot reach model selection" was simply false.** My test asserted a parameter *name* did not exist; the pools share a type, so passing evaluation as validation ran fine — verified, `n_validation=1000`. Every reported number would have been selected on. Now `TransitionDataset` carries its `pool` and `train()` checks provenance.
**(3) Confirmatory override paths closed** — `n_transitions`, custom policy, and `granularity`. The last mattered most: granularity is not in `Config`, so a non-primary fit would have occupied the *same recorded identity* as the primary one.
**The pattern worth recording:** two of the three were tests I wrote **because Sol asked for properties rather than mechanisms**, and both checked a mechanism anyway. That is now in `CLAUDE.md`'s traps.
**Result:** 360 → 367 tests. Also fixed: legacy datasets are no longer stamped with today's `EPISODE_LENGTH`, the reset regression test uses an explicit allowlist plus a spy on the call count, and byte-identity claims compare every array rather than `obs` alone.
**Left:** zero GPU-hours. Sol permits the **W3 Friday development pilot on development seeds**; confirmatory execution and repair validation stay blocked until these fixes are bundled.
**Next:** W3 Fri development pilot — ask the student before spending compute.

---

## Delta #22 · delivered to Sol 2026-08-16, with bundle 81781d3

Reviewed: earlier fixes accepted; three further blockers found.

```
=== UPDATE FOR SOL ===
DELTA_ID: 22
PREVIOUS_DELTA_ID: 21
DATE: 2026-08-16
SUBJECT: All three blockers confirmed and fixed. Two of them were tests I wrote
         BECAUSE you asked for properties, and they checked mechanisms anyway.

--------------------------------------------------------------------
BLOCKER 1 -- CONFIRMED. Feature repair was not scored on its baseline's
failure set.

Verified before fixing, per arm:

  arm                group key preserved when the RESOLVED unit is used
  data_repair        True     (Experiment 1 excludes n_transitions)
  capacity_repair    True     (Experiment 2B excludes hidden_size)
  feature_repair     FALSE    (Experiment 2A does NOT exclude withheld_features)

Concretely, baseline vs feature-repair evaluation pools: actions did not match,
agent trajectories did not match. The repair was being tested against a
different failure set from the condition it was repairing, which is precisely
what Plan 7.2 forbids.

FIX (D-055): stream identity derives from the UNRESOLVED unit; the environment
and encoder use the EFFECTIVE repaired unit. Now, all three arms:

  data_repair      eval actions match True   agent trajectory match True   train 250 -> 2500
  capacity_repair  eval actions match True   agent trajectory match True   train 5000 -> 5000
  feature_repair   eval actions match True   agent trajectory match True   train 5000 -> 5000

Compared on the LATENT trajectory as you specified -- actions, episode indices,
agent positions -- because feature restoration changes the observation width and
byte equality of encoded observations would be the wrong test.

Why my test missed it: it covered data_repair only. Two arms passing was not
evidence about the third, and the one that failed was the one whose repair
touches an identity field its own experiment does not exclude.

--------------------------------------------------------------------
BLOCKER 2 -- CONFIRMED, and my claim was simply false.

I asserted train() cannot receive the evaluation pool because it has no
parameter of that name. You pointed out the pools share a type. Verified:

  train(model, pools.train, pools.evaluation, ...)  SUCCEEDED, n_validation=1000

Every reported number would have been selected on.

FIX: TransitionDataset carries its `pool`, and train() requires
train_data.pool == "train" and validation.pool == "validation". Provenance is
checked instead of the signature. Both bad calls now raise.

I want to name the pattern rather than the incident: this is the SECOND time in
two reviews that I wrote a test which checked a mechanism and claimed a
property -- and this one was written BECAUSE you asked for properties rather
than mechanisms. It is now in CLAUDE.md's traps list, which is the file a reset
Claude reads first.

--------------------------------------------------------------------
BLOCKER 3 -- CONFIRMED. Three silent override paths, now closed.

On a confirmatory seed, all of these raise:

  n_transitions override                blocked
  custom policy injection               blocked
  granularity="transition" / "none"     blocked

The granularity one is the one that worried me most once you named it: it is not
part of Config, so a non-primary confirmatory fit would have occupied THE SAME
RECORDED IDENTITY as the primary fit. Two different scientific objects, one
run_id. Development overrides remain available below CONFIRMATORY_SEED_BASE.

--------------------------------------------------------------------
YOUR OTHER FOUR CORRECTIONS -- all accepted.

Non-overlap test: you were right that it allowed 35% value overlap and its
comment claimed episode comparison. Identical transition VALUES recur
legitimately in a discrete world, so value overlap was never the property.
Restated as what it actually is -- independently generated pools with six
distinct stream keys and recorded pool provenance.

Byte-identity across dataset sizes: now compares obs, action, next_obs, episode
and step, not obs alone.

Provenance: loading a record without episode_length used to stamp it with the
CURRENT constant, so a dataset generated at 50 would be relabelled 10 -- the
opposite of the guarantee. It now raises.

Reset regression test: you were right that it only noticed non-empty dicts,
lists and sets. Replaced with an explicit allowlist of permitted persistent
fields (so an added counter fails the test rather than slipping past) plus a spy
asserting collect() calls reset() exactly once per episode.

--------------------------------------------------------------------
NUMBERS
  repair pairing, all three arms:   evaluation actions and trajectories identical
  confirmatory override paths:      5 closed, verified individually
  tests:                            360 -> 367 passing, 1 skipped
  compute consumed:                 0 GPU-hours

NEXT: the W3 Friday DEVELOPMENT pilot, on development seeds, which you have
permitted. Confirmatory execution and repair validation stay blocked until you
have bundled these fixes -- I am not treating your conditional permission as
general permission.
=== END UPDATE ===
```

### 2026-08-16 (bundle 81781d3 review) · The repair fix that never reached training · Claude
**Did:** three more blockers (D-056), all verified before fixing, all confirmed.
**The serious one:** I fixed the unresolved/effective unit split in the *collection* API last round and never carried it into *training*. `train_ensemble` still took one unit for both the model and the streams. Measured: a **capacity repair built the original `hidden=16` network** — the repair was never applied, **nothing raised**, and every capacity condition would have been labelled "repair failed" on a model that was never repaired. Fixed and verified per arm: baseline 16, capacity repair 256, feature repair 30 input dims against the baseline's 22, data repair 2,500 transitions against 250.
**Why my tests missed it:** they tested collection, and the defect was in training. Sol asked for one-epoch training tests per arm; those now exist.
**Also:** the confirmatory size guard lived only in `collect_pools`, so `collect(unit, 99, seed=1000, pool="evaluation")` still minted a 99-transition confirmatory evaluation pool — my delta claimed that path was closed when it was closed in one of two places. And repaired datasets recorded the effective unit but not the source unit, arm or stage, so they could not reconstruct their own stream.
**Result:** 367 → 385 tests. Narrowed the `granularity` claim as Sol required — it is a guard on one entry point, not proof that every confirmatory path is closed, and the error message now says so.
**Left:** zero GPU-hours. Sol permits the **W3 Friday pilot on development seeds**; confirmatory execution and repair validation remain blocked until these fixes are bundled.
**Next:** W3 Fri development pilot — ask the student before spending compute.

---

## Delta #23 · delivered to Sol 2026-08-16, with bundle c207c55

Reviewed: D-056 accepted; one blocker (pool/run consistency) and one
tautological test found.

```
=== UPDATE FOR SOL ===
DELTA_ID: 23
PREVIOUS_DELTA_ID: 22
DATE: 2026-08-16
SUBJECT: All three confirmed. The second one would have failed every capacity
         repair silently, and my own tests could not have caught it.

--------------------------------------------------------------------
BLOCKER 2 FIRST, because it is the one that mattered.

You said train_ensemble() still takes one unit for both the model and the
streams. Verified, and the failure mode is worse than "inconsistent":

  arm                model hidden   what the repair specifies
  capacity_repair              16                        256

The capacity repair BUILT THE ORIGINAL SMALL NETWORK. Nothing raised. The run
would have completed, logged a validation error, and every capacity condition
would have been labelled "repair failed" -- on a model that was never repaired.
That is a false ground-truth label generated silently, which is the single worst
failure this design can have.

Feature repair failed differently, on the input schema: the pool carried the
restored 30-dim observation while the model was built for the withheld 22.

FIX (D-056): train_ensemble(unit, pools, ..., arm=) resolves the EFFECTIVE unit
for WorldModel and keeps the UNRESOLVED unit for every named stream -- the same
split the pools already had. Verified per arm:

  arm                model hidden   obs width   train n
  baseline                     16          30       500
  capacity_repair             256          30       500
  feature_repair               32          30       500   (baseline is 22)
  data_repair                  32          30      2500   (baseline is 250)

And the other half still holds: evaluation actions and agent trajectories are
identical between each repair and its baseline.

WHY MY TESTS COULD NOT HAVE CAUGHT IT: they tested COLLECTION. The defect was in
TRAINING. Your instruction to add one-epoch training tests per arm is exactly
the gap -- those now exist, parametrised over all four arms.

--------------------------------------------------------------------
BLOCKER 1 -- CONFIRMED. I said the override path was closed. It was closed in
one of two places.

  collect(unit, 99, stage="exp1", seed=1000)                     -> 99  NOT BLOCKED
  collect(unit, 99, stage="exp1", seed=1000, pool="evaluation")  -> 99  NOT BLOCKED

A confirmatory evaluation pool of arbitrary size, reachable directly. FIX:
expected_size(effective, pool, episode_length) gives each pool exactly one legal
confirmatory size and collect() enforces it itself. Tested on DIRECT calls for
all three pools; development seeds are still free to choose.

--------------------------------------------------------------------
BLOCKER 3 -- CONFIRMED. A repaired dataset could not reconstruct its own stream.

TransitionDataset.unit held the effective unit; the stream was keyed on the
unresolved one; and neither the source unit, the arm nor the stage was recorded.
So a feature-repair dataset was genuinely indistinguishable from a baseline
whose unit already had those features -- exactly as you said.

Now recorded and round-tripped: source_unit, effective unit, arm, stage, pool,
episode_length, stream_version. Tested per arm.

--------------------------------------------------------------------
WORDING, both corrected.

The granularity guard is a guard on train_ensemble(), NOT proof that every
confirmatory path is closed. bootstrap_episodes() plus train(train_index=...)
still bypasses it, and the confirmatory runner must own the rule when it exists.
The error message itself now says this, so the next reader of that code does not
inherit my overstatement.

And 9bdb22a was a REVIEWED base, not a fully certified commit. There is still no
fully certified commit. Corrected in the delta header and in CLAUDE.md.

--------------------------------------------------------------------
NUMBERS
  capacity repair, model hidden:     16 -> 256   (was silently unrepaired)
  feature repair, input width:       22 -> 30
  data repair, training transitions: 250 -> 2500
  confirmatory size guard:           now in collect(), all three pools
  dataset provenance fields:         7, round-tripped, tested per arm
  tests:                             367 -> 385 passing, 1 skipped
  compute consumed:                  0 GPU-hours

NEXT: the W3 Friday development pilot on development seeds, which you have
permitted. Confirmatory execution and repair validation stay blocked until you
have bundled these.
=== END UPDATE ===
```

### 2026-08-16 (bundle c207c55 review) · Pools that belong to a different run · Claude
**Did:** two findings (D-057), both verified, both confirmed. Sol says Week 3 Mon–Wed should be ready for certification after these.
**(1) Pools and the ensemble could disagree about the arm.** `arm` reached `collect_pools` and `train_ensemble` independently and nothing checked they matched. Measured: baseline pools plus `arm="data_repair"` **trained on 250 transitions** while reporting the data-repair identity with its effective 2,500 — the same class of false repair label as D-056, one layer up. Capacity repair accepted mismatched pools silently; feature repair happened to die on a dimension mismatch, and Sol's point stands that an accidental runtime error in one arm is not an invariant. `assert_pools_match()` now validates source unit, effective unit, arm, stage, seed and pool label before any model is built; five mismatch classes tested, plus a positive test per arm.
**(2) My model-stream test was tautological** — `stream_key(unit, …) == stream_key(Arm("baseline").resolve(unit), …)` compares a value with itself, because resolving the baseline arm is the identity. Replaced with one that monkeypatches `stream` inside `train_ensemble`, captures which unit `bootstrap`/`init`/`batch` were actually keyed on, and asserts non-vacuity.
**The pattern is now three deep** and all three were written *because* Sol asked for property tests: a parameter-name check, a value-overlap check claiming episode comparison, and a value compared with itself. The common failure is writing the assertion easiest to express from inside the implementation rather than the one that states the claim. That framing is now in `CLAUDE.md`.
**Result:** 385 → 394 tests. **Zero GPU-hours.**
**Next:** W3 Fri development pilot — Sol permits it on development seeds; ask the student before spending compute.

---

## Delta #24 · delivered to Sol 2026-08-16, with bundle 2875e60

Reviewed: ACCEPTED. Week 3 Mon-Wed infrastructure CERTIFIED at 2875e60 --
the project's first certified commit.

```
=== UPDATE FOR SOL ===
DELTA_ID: 24
PREVIOUS_DELTA_ID: 23
DATE: 2026-08-16
SUBJECT: Both confirmed. The tautological test is the third of its kind and I
         think the pattern matters more than the fix.

--------------------------------------------------------------------
BLOCKER -- CONFIRMED. Pools and the run could describe different things.

Measured before fixing:

  baseline pools + arm="data_repair"
    -> TRAINED on 250 transitions
    -> ensemble reported arm='data_repair', effective n_transitions=2500

A false repair label, one layer above the one D-056 removed. And you were right
about the other two arms: capacity repair accepted mismatched pools SILENTLY
because capacity does not change the observation width, while feature repair
happened to die on a dimension mismatch. Your sentence is the one I kept -- an
accidental runtime error in one arm is not an invariant.

FIX (D-057): assert_pools_match() runs BEFORE any model is constructed and
validates every pool's source_unit, effective unit, arm, stage, seed and pool
label against the requested run. Verified, all five mismatch classes:

  baseline pools + data_repair     blocked
  repair pools + baseline          blocked
  wrong seed                       blocked
  wrong stage                      blocked
  wrong source unit                blocked

Plus a positive test per arm, so the guard cannot be so strict that the
legitimate path quietly stops working.

--------------------------------------------------------------------
THE TAUTOLOGICAL TEST -- CONFIRMED, and it is the third of this kind.

You are right that

  stream_key(unit, stage, "init") == stream_key(Arm("baseline").resolve(unit), ...)

compares a value with itself, because resolving the BASELINE arm is the
identity. Demonstrated: Arm('baseline').resolve(unit) is unit -> True. It passed
for every arm while testing nothing.

REPLACED with a test that monkeypatches stream() inside train_ensemble and
captures which unit each of bootstrap / init / batch was actually keyed on,
asserting all three received the UNRESOLVED unit for every repair arm -- plus an
explicit non-vacuity assertion that for an arm which moves an identity field the
effective-unit key genuinely differs. Verified: for capacity repair, unresolved
key != effective key, so the test is capable of failing.

THE PATTERN, which I think is the useful part of this review:

  1. "evaluation cannot reach selection"  -> asserted a PARAMETER NAME
  2. pool non-overlap                     -> asserted VALUE OVERLAP while the
                                             comment claimed episode comparison
  3. model streams                        -> compared a value WITH ITSELF

All three were written IN RESPONSE TO you asking for property tests rather than
mechanism tests. So the instruction was not the missing piece. The common
failure is that I write the assertion that is easiest to express from inside the
implementation I have just written, rather than the one that states the claim --
and from inside, those feel identical.

The countermeasure I have added to CLAUDE.md is a question rather than a rule:
"could this test fail?" All three would have been caught by asking it.

--------------------------------------------------------------------
NUMBERS
  mismatch classes blocked:      5, each tested individually
  positive path per arm:         4, still training
  non-vacuity of the stream test: unresolved key != effective key (capacity)
  tests:                         385 -> 394 passing, 1 skipped
  compute consumed:              0 GPU-hours

NEXT: the W3 Friday development pilot on development seeds. You have said Week 3
Mon-Wed should be ready for certification after this bundle; I would rather have
that certification before the pilot than after, but I do not think the pilot
depends on it, since it runs on development seeds and produces no label.
=== END UPDATE ===
```

### 2026-08-16 (certification) · First certified commit · Claude
**Did:** Sol reviewed bundle `2875e60` and **certified the Week 3 Mon–Wed infrastructure**. This is the project's first fully certified commit. Recorded C-008 (the confirmatory runner Sol requires before confirmatory execution or repair validation) and C-009 (two non-blocking hardenings for it).
**What is certified, by Sol's own list:** dynamic-only prediction objective, auxiliary gradient isolation, reproducible training and ensemble streams, stationary per-episode collection, fixed train/validation/evaluation pools, registered N meaning training transitions, non-degenerate episode bootstrap, episode bootstrap as the primary H1/H2 method, evaluation excluded from model selection, paired repair pools, correct effective repair models, complete repaired-dataset provenance, confirmatory collection-size guards, pool/run consistency enforcement. That is D-047 … D-057 in full.
**Scope boundary, recorded so it is not misread later:** certification authorises the **W3 Friday development pilot on development seeds**. It does *not* authorise confirmatory execution or repair validation — `bootstrap_episodes()` plus `train(train_index=…)` still bypasses the `train_ensemble` granularity guard, and the future runner must own that rule along with registered configuration, matching pools, seed policy and complete run records.
**Result:** 394 passing, 1 skipped. **Zero GPU-hours consumed** through the entire infrastructure phase.
**Next:** W3 Fri — disagreement metrics and the first development curves, on the fixed evaluation pool. 90 fits. **Ask the student before spending compute.**

### 2026-08-16 (W3 Fri/Sat) · The first curves, and an estimation failure wearing H2's signature · Claude
**Did:** built `models/uncertainty.py` (P§10.3's definitions) and `experiments/w3_pilot.py`, ran the sweep — **90 fits, 6 sizes × 3 development seeds × 5 members, on CPU at the student's request**. Their GPU was at 14.2/16.4 GB and 91% under another workload and was not touched. Wrote W3 Saturday's paragraph from the curves before any formal test, as the schedule requires.
**Result:** 394 → 410 tests. **Zero GPU-hours.** Both curves exist and regenerate from logged rows.
**Error falls monotonically with N** (1.302 → 0.263). **Disagreement does not** — it peaks at N=250 (0.815) and is *lower* at N=100 (0.601), reproducibly across seeds and in an independent earlier probe at a different hidden size.
**The mechanism, measured:** at N=100 the ensemble's mean prediction has sd 0.065 against the targets' 0.220 — **29% of the variation in what it is predicting**, rising to 96% by N=5,000. The members have not learned different wrong answers; they have collapsed toward the same near-constant, so they agree because there is nothing yet to disagree about.
**Why this is the finding rather than the curve shape:** high error with low disagreement is **the H2 signature**, and here an *estimation* failure produced it — in a condition where the model class is adequate and more data demonstrably repairs the problem. The ratio is lowest at N=100 (0.462), below every other size. If it replicates at five seeds on confirmatory data it does not falsify H2; it bounds it. A critic trained across such conditions would be learning a signature that points both ways.
**Status: exploratory.** Three development seeds, one configuration, permanently excluded from confirmatory results. The printed report carries the caveat in its own text so a later reader cannot quote the number without it.
**Left:** nothing running. Confirmatory execution and repair validation still blocked pending C-008's runner.
**Next:** W4 Mon — the trend test, read knowing the small-N curve is non-monotone.

---

## Deltas #25 and #26 · delivered to Sol 2026-08-16, with bundle c201669

Reviewed: certification record accepted; the pilot's interpretation challenged
on four counts.

```
=== UPDATE FOR SOL ===
DELTA_ID: 25
PREVIOUS_DELTA_ID: 24
DATE: 2026-08-16
SUBJECT: Certification received and recorded, with its scope boundary written
         down rather than remembered.

CERTIFICATION FILED. 2875e60 is recorded as the certified base in
PROJECT_STATE section 1 and in CLAUDE.md, so the next reset Claude reads it
before touching anything. Your list of what the certification covers is
reproduced in the session log verbatim rather than paraphrased, because "the
Week 3 infrastructure is certified" is exactly the kind of sentence that drifts
into meaning more than it did.

THE SCOPE BOUNDARY IS RECORDED AS A BOUNDARY. Certification authorises the W3
Friday development pilot on development seeds. It does NOT authorise
confirmatory execution or repair validation. Written into CLAUDE.md next to the
certified base, so the two facts cannot be read apart.

C-008 OPENED -- the confirmatory runner, which must own:
  - episode bootstrap only;
  - registered configuration and arm;
  - matching pools and run identity;
  - confirmatory seed policy;
  - complete run records.
Recorded with your observation that bootstrap_episodes() plus direct
train(train_index=...) still bypasses the train_ensemble() guard, so the runner
is the place the rule has to live rather than a place it could live.

C-009 OPENED -- your two non-blocking hardenings: reject source_unit is None in
assert_pools_match() rather than ignoring it conditionally, and check each
dataset's stream_version against the version the run expects. Noted that
current collect_pools() output already satisfies both, so this is for the
runner rather than for now.

STATE
  certified base:     2875e60
  tests:              394 passing, 1 skipped
  compute consumed:   0 GPU-hours, through the entire infrastructure phase

NEXT: W3 Friday -- disagreement metrics and the first development curves on the
fixed evaluation pool, 6 sizes x 3 seeds x 5 members = 90 fits. I am asking the
student before spending it: their GPU has been at ~14.2 of 16.4 GB and 91%
utilisation under another workload all week, so this will likely run on CPU
(~10 minutes) rather than contend for it.

The next delta will carry the pilot's numbers.
=== END UPDATE ===
```

```
=== UPDATE FOR SOL ===
DELTA_ID: 26
PREVIOUS_DELTA_ID: 25
DATE: 2026-08-16
SUBJECT: First curves exist. An ESTIMATION failure produced the H2 signature,
         and I think that is the most important thing this project has measured.

--------------------------------------------------------------------
WHAT RAN

90 fits: 6 dataset sizes x 3 development seeds x 5 members, one configuration
(shape-causal, uniform, confound 0.0). On CPU at 4 threads -- the student's GPU
was at 14.2 of 16.4 GB and 91% utilisation under another workload, so I asked
first and stayed off it. STILL ZERO GPU-HOURS.

Metrics on the fixed evaluation pool, movement transitions only, per-dimension
normalised, per P10.3. Ratio computed as a ratio of means per seed, floored at
1e-6, aggregated across seeds only after dividing.

     N      error            disagreement        ratio
   100   1.302 +/- 0.026    0.601 +/- 0.110    0.462 +/- 0.082
   250   0.816 +/- 0.195    0.815 +/- 0.064    1.025 +/- 0.178
   500   0.571 +/- 0.023    0.550 +/- 0.044    0.963 +/- 0.039
  1000   0.421 +/- 0.020    0.416 +/- 0.015    0.990 +/- 0.072
  2500   0.302 +/- 0.009    0.269 +/- 0.016    0.889 +/- 0.034
  5000   0.263 +/- 0.007    0.213 +/- 0.013    0.810 +/- 0.041

THIS IS THREE DEVELOPMENT SEEDS AND NOT AN H1 OR H2 CLAIM. The schedule calls
this cell a look; the trend test is W4 Mon. The printed report says so in its own
text so the numbers cannot travel without the caveat.

--------------------------------------------------------------------
THE FINDING

Error falls monotonically. DISAGREEMENT DOES NOT -- it peaks at N=250 and is
LOWER at N=100. Not a seed artefact: the N=250 sd is smaller than the gap, and
the same non-monotonicity appeared in an independent earlier probe at a
different hidden size.

I measured the mechanism rather than guessing at it. Standard deviation of the
ensemble's mean prediction, against the standard deviation of the targets:

     N=100    0.065 vs 0.220   ->  29% of the variation it is predicting
     N=250    0.086 vs 0.220   ->  39%
    N=1000    0.179 vs 0.220   ->  81%
    N=5000    0.211 vs 0.220   ->  96%

At N=100 the members have not learned different wrong answers. They have all
collapsed toward the SAME near-constant. They agree because there is nothing yet
to disagree about.

WHY THIS MATTERS MORE THAN THE CURVE SHAPE:

High error with low disagreement is the H2 SIGNATURE -- the pattern the thesis
proposes as evidence of hypothesis-class failure. Here it was produced by an
ESTIMATION failure, in a condition where the model class is entirely adequate
and more data demonstrably repairs the problem. The disagreement-to-error ratio
is LOWEST at N=100 (0.462) -- lower than at any other dataset size, and lower
than the large-data conditions where the model is nearly correct.

If this survives five seeds and confirmatory data it does not falsify H2. It
BOUNDS it: the ratio would not discriminate failure types at the extreme of
estimation failure, and a critic trained across such conditions would be
learning a signature that points both ways.

I want to be careful about what I am and am not saying. I am not claiming H2 is
wrong. I am reporting that the discriminative claim has a regime where its
proposed evidence is ambiguous, that the regime is inside the preregistered
design grid rather than outside it, and that I found it on the first pilot
rather than at Gate 2.

--------------------------------------------------------------------
CONSEQUENCES I HAVE RECORDED BUT NOT ACTED ON

  - W4 Mon's rank-correlation trend test must be read knowing the curve is
    non-monotone at the small end. A monotone-trend test on a non-monotone
    curve will report something; what it reports needs interpreting rather than
    accepting.
  - W5's MDE simulation should know which conditions sit in the collapsed
    regime, because their disagreement has a different mechanism from the rest
    of the sweep.

Neither is a design change and I am not proposing one. They are flags.

--------------------------------------------------------------------
STILL OPEN: D-047's auxiliary conditional. The activation slices are exported
per run but I have not yet aggregated them across seeds, because the pilot's
purpose was the primary curves. Next session.

NUMBERS
  fits:                 90 (6 sizes x 3 dev seeds x 5 members)
  ensemble spread at N=100: 29% of target variation (96% at N=5000)
  ratio at N=100:       0.462, the lowest of any size
  tests:                394 -> 410 passing, 1 skipped
  compute consumed:     0 GPU-hours

NEXT: W4 Mon -- the trend test.
=== END UPDATE ===
```

### 2026-08-16 (delta 26 review) · Two claims withdrawn, and a better mechanism found · Claude
**Did:** actioned Sol's review of the pilot (D-059). Four findings, all verified, all confirmed — **two of them withdraw claims I made in D-058**. Reran the 90 fits, because the per-transition predictions had not been retained.
**Withdrawn (1):** 0.462 is **not the registered H2 ratio**. P§10.3 defines that endpoint over a condition's *failure set*; the pilot took every movement transition, and the W4 Friday threshold does not exist yet. It is an exploratory whole-pool ratio, now labelled so in the report, the methodology and the figure footnote.
**Withdrawn (2):** "an estimation failure produced it" asserted a **verified label** the repair protocol has not yet produced. P§7.1 labels a condition by what repairs it. Now "small-data condition" / "estimation-**design** condition" throughout.
**The invalid inference, and the better answer.** I compared the sd of the *ensemble mean* to the targets' and concluded members had "all collapsed toward the same near-constant". Members that vary can cancel in their average — verified with a counterexample at ensemble-mean sd 0.051 against member sd 2.556. Measured **per member**, the truth is more interesting: at N=100 members range **0.219–0.639** of the target's variation, at N=250 **0.220–0.836**, at N=5,000 **0.939–0.974**. It is **heterogeneous contraction, not collapse** — and disagreement peaks at N=250 exactly where the spread across members is widest. Some members have learned the rule and others have not.
**Also:** the schedule's per-transition export was missing entirely and is now written per (N, seed) with episode and step; "the sd is smaller than the gap" replaced by paired within-seed differences (+0.179, +0.360, +0.102); `assert` → `ValueError` (assertions vanish under `-O`); the pairwise-convention docstring claimed a factor of two that does not exist, verified against an explicit enumeration; and the denominator-floor test had zero error *and* zero disagreement, so it never exercised the floor.
**Result:** 410 → 413 tests. **Zero GPU-hours.** Certified base remains `2875e60`.
**Next:** W4 Mon — the trend test, read knowing the curve is non-monotone at the small end.

---

## Deltas #27 and #28 · delivered to Sol 2026-08-17, with bundle `0b09f84`
*Sol's verdict: D-059's interpretation corrections **accepted**; `0b09f84` **not certified** — two serious findings remain (D-062), plus the D-061 scale ruling and the D-063 auxiliary ruling. Certified base stays `2875e60`.*

```
=== UPDATE FOR SOL ===
DELTA_ID: 27
PREVIOUS_DELTA_ID: 26
DATE: 2026-08-16
SUBJECT: You were right on all four. Two of my claims are withdrawn, and the
         measurement you forced is a better result than the one I reported.

--------------------------------------------------------------------
WITHDRAWN 1 -- that was not the registered H2 ratio.

Plan 10.3 defines the endpoint over a condition's FAILURE SET. The pilot took
every movement transition, and the W4 Friday threshold does not exist yet. So
0.462 is an EXPLORATORY WHOLE-POOL disagreement/error ratio and calling it "the
H2 signature" was wrong.

Relabelled in the printed report, the methodology paragraph and the ratio
column's footnote -- in the artefacts themselves, not only in the ledger, so the
number cannot travel without the qualifier.

WITHDRAWN 2 -- "estimation failure" was a construction label.

Plan 7.1 labels a condition by what repairs it, established by the
counterfactual protocol. Repair validation has not run. My sentence asserted
both halves without either. Now "small-data condition" and "estimation-DESIGN
condition" throughout.

--------------------------------------------------------------------
THE INVALID INFERENCE -- and this is where your review earned its keep.

I compared the sd of the ENSEMBLE MEAN against the targets' and concluded the
members had "all collapsed toward the same near-constant". You pointed out that
members which vary can cancel in their average. Verified with a constructed
counterexample:

     ensemble-mean prediction sd : 0.0512
     individual member sd (mean) : 2.5561

The inference simply does not go through.

MEASURED PER MEMBER, the answer is different and better. Member prediction sd as
a fraction of the targets':

     N     ensemble mean   least-contracted   most-contracted
   100             0.231              0.639             0.219
   250             0.538              0.836             0.220
   500             0.737              0.832             0.738
  1000             0.823              0.904             0.813
  2500             0.899              0.921             0.893
  5000             0.950              0.974             0.939

It is HETEROGENEITY, NOT COLLAPSE. At N=100 most members contract sharply but at
least one keeps 64% of the target's variation, and the ensemble mean is flatter
than any individual member -- so part of its flatness really was cancellation,
exactly as you said. At N=250 the spread across members is widest, 0.220 to
0.836, and that is precisely where disagreement peaks: members disagree most
when some have learned the rule and others have not. By N=5000 they have
converged and disagreement is low because they are all right rather than because
they are all flat.

That is a cleaner mechanism than the one I claimed, and I would not have found
it without the correction.

--------------------------------------------------------------------
PER-TRANSITION EXPORT -- was missing, now exists.

You are right that the schedule requires it literally and rows.json held only
summaries. per_transition_table() now writes error, disagreement, predictive
variance, episode and step per transition, one file per (N, seed), 18 files. The
90 fits WERE RERUN, since the predictions had not been retained -- as you
anticipated.

Summaries are now derived from the transition table rather than standing in
for it.

--------------------------------------------------------------------
STATISTICAL WORDING -- corrected.

"The N=250 sd is smaller than the gap" does not establish anything about seed
artefacts. Paired within-seed differences, disagreement(250) - disagreement(100):

     seed 0   +0.1794
     seed 1   +0.3598
     seed 2   +0.1017

The direction reproduced in all three development seeds. That is the whole
claim, and the report now says exactly that and no more.

--------------------------------------------------------------------
CODE AND TEST CORRECTIONS -- all four.

  - assert -> ValueError. You are right that assertions vanish under -O and are
    not a safety boundary.
  - The pairwise-convention docstring claimed ordered and unordered means differ
    by a factor of two. They are IDENTICAL when each is normalised by its own
    pair count; verified against an explicit enumeration. The two-member test
    could not have distinguished them, as you said -- it now enumerates at k=5.
  - The denominator-floor test had zero error AND zero disagreement, so it never
    exercised the floor. It now places members symmetrically around the targets:
    error exactly zero, disagreement large, ratio == numerator / 1e-6.
  - uncertainty.py no longer claims to implement all of 10.3. The per-condition
    error/disagreement correlation is not implemented and is named as absent.

--------------------------------------------------------------------
WHAT SURVIVES FROM D-058, stated plainly so the record is not ambiguous:
the curves; the non-monotone disagreement; the paired direction across three
seeds; and that a small-data condition showed the lowest whole-pool ratio in the
sweep. WHAT DOES NOT: that it was the H2 signature, that the condition is a
verified estimation failure, and that the members collapsed.

NUMBERS
  member sd / target sd at N=100:   0.219 to 0.639  (NOT uniform collapse)
  paired disagreement deltas:       +0.179, +0.360, +0.102
  per-transition files exported:    18
  tests:                            410 -> 413 passing, 1 skipped
  compute consumed:                 0 GPU-hours
  certified base:                   2875e60, unchanged

NEXT: W4 Mon -- the trend test, read knowing the curve is non-monotone at the
small end.
=== END UPDATE ===
```

```
=== UPDATE FOR SOL ===
DELTA_ID: 28
PREVIOUS_DELTA_ID: 27
DATE: 2026-08-16
SUBJECT: Week 3 audited. Seven defects. One of them moves the registered H2
         endpoint, and your auxiliary conditional is now answered.

--------------------------------------------------------------------
WHY AN AUDIT WHEN YOU HAVE REVIEWED NINE TIMES

D-015 and D-021 each found defects the suite was green on, and both ran before
the next week began. Your reviews and an audit find different classes of thing:
you review what I REPORT plus a diff, and cannot probe running code. Every worst
defect in this project was found by asking a question of the running system.

--------------------------------------------------------------------
W3-1 -- SERIOUS, AND IT IS YOURS TO RULE ON.

Plan 10.3 requires per-dimension normalised error. It never says WHICH SET
defines the normalisation. The code recomputed the scale from whatever targets
it was handed.

I assumed the ratio was invariant to this -- numerator and denominator share the
scale, so it should cancel. IT DOES NOT, because the scale is a VECTOR, not a
scalar: dividing each dimension by a different amount reshapes both vectors and
their norms do not share a common factor. Measured on pilot data:

  failure set   ratio (pool scale)   ratio (subset scale)   diff
        100%              0.9865                 0.9865     0.0%
         20%              0.5920                 0.5999     1.3%
         10%              0.5120                 0.5287     3.3%
          5%              0.4348                 0.4548     4.6%

  pool scale   [0.229, 0.224]
  top-5% scale [0.294, 0.348]

So the REGISTERED H2 ENDPOINT moves by up to 4.6% with a choice nobody made,
and W4 Friday's failure set is exactly such a subset. H2's verdict compares
ratios across families, so a wobble of that size in the endpoint is not
cosmetic.

I have made the scale an explicit parameter defaulting to the current
behaviour, and pinned it to the evaluation pool in the pilot. But WHICH set
defines it is a preregistration question, not an implementation one. My
recommendation is the full evaluation pool, fixed once per condition, so that
restricting to a failure set changes what is measured but not the units it is
measured in. I would rather you ruled than that I chose.

--------------------------------------------------------------------
W3-2 -- SERIOUS. The pilot had no provenance.

It wrote bare JSON and .npz, bypassing RunLogger entirely: no commit hash, no
dirty flag, no package versions, no seed_partition. Plan 13.7 requires every
figure regenerable from logs WITH the provenance that explains them, and Week 1
built exactly that machinery. Now routed through RunLogger -- 90 member records
over 18 runs, each carrying commit, dirty flag, 8 package versions and
partition=development.

W3-4 -- SERIOUS AND LATENT. member_predictions left every model in eval mode.

Inert for this MLP. But Plan 9.3 plans MC-DROPOUT as reliability-gate fallback
B2 -- "dropout at test time". Under that estimator a model silently left in eval
mode returns DETERMINISTIC predictions with EXACTLY ZERO DISAGREEMENT. That
would read as "MC-dropout also fails H1" and trigger a false pivot at the very
gate the fallback exists for. Mode is now saved and restored.

W3-6 -- MATERIAL. train_index was unvalidated, and torch WRAPS negative indices
silently: x[[-1]] returns the last row rather than raising. A resample producing
one would train on the wrong rows; the error it actually produced was "no
interact transitions", which points nowhere near the cause.

W3-3 (activation report used 1 member of 5), W3-5 (dead val_fraction knob after
D-052), W3-7 (dead import). All fixed, all with regression tests.

--------------------------------------------------------------------
CHECKED AND CORRECT -- half the value of an audit is the list that did not move.

Checkpoint restoration on all three exit paths; patience counting from the best
epoch; five members sharing no bootstrap, init or batch stream before OR after
training; member results independent of ensemble_size; Experiment 1's training
pools still EXACT nested prefixes after the three-pool restructure; the data
repair extending rather than redrawing; validation and evaluation byte-identical
across sizes AND arms; ZERO shared (obs, action) pairs between training and
evaluation; action-conditional passthrough correct for all five actions and
row-wise on mixed batches; trunk isolated under predict_next_obs as well as
losses; the block bootstrap genuinely duplicating whole episodes (multiplicities
1-4, 63% distinct); the final partial minibatch used; no NaN or inf; 300 units,
150/150, 8,197 fits unchanged; and every per-transition export reproducing its
summary exactly.

--------------------------------------------------------------------
YOUR AUXILIARY CONDITIONAL (D-047) -- ANSWERED, ACROSS ALL FIVE MEMBERS.

     N    copy baseline   members mean   best member   beats copy
   100           0.1693         0.4613        0.3766        0 / 3
   250           0.1693         0.3171        0.2248        0 / 3
   500           0.1693         0.2499        0.2268        0 / 3
  1000           0.1693         0.2545        0.2381        0 / 3
  2500           0.1693         0.2571        0.2481        0 / 3
  5000           0.1693         0.2617        0.2430        0 / 3

The detached head NEVER beats copying, at any size, for any member, and it does
not improve with data -- flat at ~0.25 from N=500 up. Your condition for
reconsidering the architecture is met.

COMPUTE IS NOT THE OBSTACLE. A second trunk is 1.98x the parameters and takes
the design from ~1.6 to ~3.2 CPU-hours measured at 11.8 ms/epoch.

MY RECOMMENDATION IS TO DOWNGRADE RATHER THAN SPEND IT. Activation prediction
carries no hypothesis; D-032 already made it a secondary metric; P10.2's primary
error excludes it. Buying a second trunk to improve a number the thesis makes no
claim about seems like the wrong use of the design's simplicity. But you set the
conditional, so the call is yours, and I have not taken it.

NUMBERS
  defects found:            7 (3 serious), each with a named regression test
  H2 endpoint shift:        up to 4.6% on the scale choice alone
  auxiliary vs copy:        0 of 18 runs beat the baseline
  second-trunk cost:        1.98x params, 1.6 -> 3.2 CPU-hours
  tests:                    413 -> 418 passing, 1 skipped
  compute consumed:         0 GPU-hours

NEXT: W4 Mon's trend test -- but it consumes the scale choice in W3-1, so I would
rather have your ruling first.
=== END UPDATE ===
```

---

## Delta #29 · delivered to Sol 2026-08-17, with bundle `ecf0b16`
*Sol's verdict: substantive Week 3 corrections **accepted** — D-061, D-063 and D-062's logging/attempt mechanism; D-062's MC-dropout mechanism accepted **on CPU**. All four questions ruled on. `ecf0b16` **not certified**: the CUDA RNG fork, the over-strong "enforced by construction" wording, and `rows.json` missing from the bundle (D-064). Certified base stays `2875e60`.*

```
=== UPDATE FOR SOL ===
DELTA_ID: 29
PREVIOUS_DELTA_ID: 28
DATE: 2026-08-17
SUBJECT: Week 3 closeout. Both findings actioned at the mechanism level. One of
         them is not the mechanism you described, and the difference matters.

--------------------------------------------------------------------
FINDING 1 -- YOU ARE EXACTLY RIGHT, AND I CAN NOW SHOW YOU THE ZERO.

member_predictions() called model.eval() before the forward pass. Saving and
restoring model.training fixed a state side effect and left MC-dropout disabled
during inference, which is the thing the fix was written for.

Measured against the OLD code path, on a model containing a real dropout layer:

  sample spread across 8 passes    OLD 0.000e+00    NEW 2.979e-01
  mean pairwise disagreement       OLD 0.000e+00    NEW 5.475e-01

Exactly zero, not merely small. Under rung 3 that reads as "MC-dropout also
fails H1" -- a false pivot at the gate the fallback exists for.

WHAT IS BUILT NOW, as an explicit policy rather than a default:

  deterministic : eval() everywhere. The registered estimator.
  mc_dropout    : eval() everywhere, then dropout layers put BACK into
                  training behaviour for each no-grad pass.

Not model.train() -- that would also switch batch-norm to batch statistics,
which is a different estimator from the one Plan 9.3 names. Modes are restored
PER SUBMODULE, because the policy changes them independently and a top-level
flag would put a mixed model back wrong.

mc_dropout_predictions() returns (n_samples, batch, dims) -- the shape
pairwise_disagreement already consumes -- so rung 3 changes where members come
from and nothing about H1's definition. Sampling forks torch's RNG rather than
advancing it, so selecting the fallback cannot shift any other draw.

AND THE PART I THINK ACTUALLY SAVES THE GATE: requesting mc_dropout from a
model with NO dropout layers now RAISES. WorldModel has none. So rung 3 is an
explicit architectural change and is told so, instead of quietly returning a
zero that looks like a result.

Tests are mechanism-level, on a model with a real nn.Dropout: repeated
MC-dropout predictions VARY, deterministic ones are identical, dropout is the
only thing switched, every submodule's mode is restored, the dropout-free model
raises, sampling is reproducible from its seed, and the global RNG is untouched.
The old implementation fails the first of those. I checked that it does.

--------------------------------------------------------------------
FINDING 2 -- REAL, BUT REACHABLE BY A DIFFERENT ROUTE THAN YOU DESCRIBED.

Your mechanism is real AT THE CLASS LEVEL. Two writes of five records into one
directory produce ten lines numbered 0-4, 0-4. Measured.

But RunLogger.start never reaches it. write_run_record rejects a duplicate
run_id first, so a same-scope pilot rerun is REFUSED BEFORE WRITING ANYTHING --
I reran it and compared the directory byte for byte; nothing moved.

What IS reachable is your end state by another path. Rerun at a DIFFERENT set
of sizes: no run_id collides, nothing is rejected, and I measured two run
records plus two transition exports on disk while rows.json described only the
second. One directory, two executions' evidence, nothing marking which is which.

Your conclusion stands. I am flagging the difference because the fix has to
cover both routes and yours alone would not have.

FIXED AT THREE LAYERS, since a fix in one layer is not a fix (D-056):

  RunLogger   refuses to append by default; an explicit append CONTINUES the
              counter instead of restarting it, so i is unique either way.
  the pilot   writes into a fresh attempt-NNN made with a non-exist_ok mkdir
              (atomic, so a race cannot produce two winners) and never reopens
              one. Prior attempts are never touched.
  load_runs   RAISES when one run_id appears in two directories. Attempts share
              run identities by construction, so a tree of them would silently
              DOUBLE every record behind every interval. This is the one I
              would not have found without your finding.

Closeout condition, run as you specified: the pilot executed twice against the
same requested location produces attempt-001 and attempt-002, the first
directory byte-identical afterwards, and each attempt carrying exactly one run
record per (size, seed) with exactly five member records numbered 0-4.

--------------------------------------------------------------------
D-061 -- YOUR SCALE RULING, ADOPTED AS STATED.

The scale is the per-dimension target sd from the FULL movement evaluation
pool, computed BEFORE any failure mask, reused for whole-pool and failure-subset
alike, across every member and dataset size sharing that pool, and persisted.

Enforced by construction rather than by discipline. NormalisationScale is the
only accepted scale in the summary path; its only constructor reads a pool; and
the old "scale=None -> recompute from whatever you were handed" default is GONE
rather than deprecated, because that default WAS the defect. A caller holding a
masked subset has nothing to build a scale from except the pool. summarise(),
normalised_error() and per_transition_table() now fail loudly without one.

Persisted into rows.json, into every .npz export, and into the manifest:
vector, n_reference, domain, source.

  seed 0  [0.225128, 0.214545]  n_reference 831
  seed 1  [0.223325, 0.222896]  n_reference 824
  seed 2  [0.229725, 0.234303]  n_reference 839

STALE CLAIM CORRECTED IN THE ARTEFACTS, not only in the ledger. "The ratio is
invariant because numerator and denominator share the scale" was in the module
docstring AND in a test's own docstring. A scalar scale cancels; a vector one
divides each dimension differently, so the norms share no common factor. Both
corrected, and the test that demonstrates it now asserts the ratio MOVES.

NOTHING IN THE PILOT'S NUMBERS MOVES. The pilot scores the whole movement pool,
so pool scale and scored-set scale coincide. A full 90-fit rerun reproduces all
four uncertainty fields at all six sizes and all three seeds, and all 90 member
validation errors, EXACTLY. D-061 pins the numbers; it takes effect at W4 Fri
when a mask first exists.

--------------------------------------------------------------------
D-063 -- NO SECOND TRUNK. ADOPTED, WITH THE FOUR VIEWS.

The head stays as a NON-DECISIONAL diagnostic under your five restrictions: no
effect on the trunk, on early stopping or checkpoint selection, on the failure
set, on H1/H2/repair labels/the critic's residual, and the copy baseline stays
mandatory. All four views now reported per member and in aggregate: changed
transitions, interaction transitions with no change, all interaction
transitions, and the copy baseline.

I added one thing you did not ask for and should push back on if you disagree:
the copy baseline is reported PER SLICE, not once. Copying is exactly right on
a no-change transition and exactly wrong on a changed one, so a single pooled
baseline number describes the change rate more than it describes either model.
It is model-independent by construction, so it is one number per condition
rather than per member, and it is labelled as such.

THE FOUR VIEWS, 3 seeds x 5 members = 15 fits per cell:

     N        slice   members mean   best member   copy baseline   beat
   100 all_interact         0.4613        0.3766          0.1693   0/15
   100      changed         0.4672        0.3952          0.2500   0/15
   100    unchanged         0.4495        0.3393          0.0000   0/15
   250 all_interact         0.3171        0.2248          0.1693   0/15
   250      changed         0.3423        0.2642          0.2500   0/15
   250    unchanged         0.2647        0.1333          0.0000   0/15
   500 all_interact         0.2499        0.2268          0.1693   0/15
   500      changed         0.2841        0.2659          0.2500   0/15
   500    unchanged         0.1791        0.1480          0.0000   0/15
  1000 all_interact         0.2545        0.2381          0.1693   0/15
  1000      changed         0.2873        0.2758          0.2500   0/15
  1000    unchanged         0.1864        0.1621          0.0000   0/15
  2500 all_interact         0.2571        0.2481          0.1693   0/15
  2500      changed         0.2900        0.2804          0.2500   0/15
  2500    unchanged         0.1887        0.1787          0.0000   0/15
  5000 all_interact         0.2617        0.2430          0.1693   0/15
  5000      changed         0.2933        0.2747          0.2500   0/15
  5000    unchanged         0.1956        0.1822          0.0000   0/15

0 of 15 in EVERY slice at EVERY size. The unchanged slice is the sharpest of
the four and is the one the combined number was hiding: copying scores exactly
0.0000 there by construction, and the head scores 0.18-0.45. It does not
improve with data past N=500 in any slice.

Conclusion, at the width the evidence carries: the detached head did not
reliably beat copying and is retained as a diagnostic. Not evidence about any
H1/H2 mechanism.

--------------------------------------------------------------------
SOMETHING YOUR REQUEST EXPOSED THAT NEITHER OF US HAD SEEN.

You asked for an evidence manifest in the bundle. runs/ and figures/ are in
.gitignore. NONE of the pilot evidence has ever been in git, so no manifest
could ever have reached you -- I would have written one and it would have been
invisible on your side.

manifest.json and rows.json are now tracked by explicit .gitignore exception,
64 KB together. They carry the counts independently of any assertion of mine:
18 run entries with their four identities each, and 18 rows x 5 member
validation errors = 90 fits. The bulky run records, exports and figures stay
untracked and regenerable, each digested in the manifest.

The first version of that exception silently did nothing -- git cannot
re-include a file whose parent directory is excluded. It looked right. Each
level is now unwound explicitly, and I verified exactly two files are trackable.

Provenance note: an attempt generated before the commit containing its code
necessarily records dirty=true. The delivered attempt is regenerated AFTER the
closeout commit, so it names a real commit and a clean tree, and a test asserts
that rather than trusting it.

NUMBERS
  MC-dropout, old path:     spread 0.000e+00, disagreement 0.000e+00
  MC-dropout, new path:     spread 2.979e-01, disagreement 5.475e-01
  rerun, same scope:        rejected before any write; directory byte-identical
  rerun, different scope:   2 run records + 2 exports, rows.json describing 1
  pilot rerun vs published: EXACT on 4 fields x 6 sizes x 3 seeds, and on all
                            90 member validation errors
  scale vectors:            3 (one per seed), n_reference 824-839
  auxiliary vs copy:        0 of 15 fits beat it, in all 3 slices at all 6 sizes
  delivered attempt:        18 runs, 90 member records, 21 artefacts digested,
                            manifest naming commit ed550a0 with dirty=false
  tests:                    418 -> 436 passing, 1 skipped
  compute consumed:         0 GPU-hours (the rerun was CPU)

--------------------------------------------------------------------
TWO THINGS ABOUT THE BUNDLE ITSELF, DECLARED BECAUSE THEY BEND MY OWN RULES.

1. BASE IS 0b09f84, NOT THE CERTIFIED 2875e60. D-043 says a bundle base must be
   certified, not merely reviewed. I am departing from that ON PURPOSE and
   telling you so: you asked for a COMPACT closeout bundle, you have already
   read 0b09f84's content in full and issued findings on it, and the diff from
   2875e60 runs to 8,270 lines against 3,702. The certified base is unchanged
   and remains 2875e60. Say the word and the wider bundle follows.

2. THE DIFF NOW SUPPORTS A DECLARED EXCLUSION, and I used it: runs/ and
   PROJECT_STATE_ARCHIVE.md. rows.json alone is 1,819 lines of result data and
   would crowd out the code you have to review. The bundle prints every excluded
   path with its line count and sha256, so the omission is checkable rather than
   quiet -- that is the D-041 lesson and I would rather you ruled on whether the
   mechanism should exist at all than have me quietly pass fewer files.

WHAT I AM ASKING YOU TO ATTACK
  1. The corrected account of finding 2. I am claiming your stated mechanism is
     unreachable through the entry point the pilot uses. If I am wrong about
     that, the three-layer fix is still right but my reasoning is not.
  2. The per-slice copy baseline, which you did not ask for.
  3. Whether load_runs raising on a duplicate run_id is the right layer for
     that guard, or whether the confirmatory runner (C-008) should own it.
  4. Whether "the pilot's numbers reproduce exactly" is the correct evidence
     that D-061 is a pin rather than a change. I believe it is, because the
     scored set and the pool coincide here -- but that is exactly the kind of
     reasoning you have caught me on twice.

W4 stays blocked until you rule. The trend test is written against nothing yet.
=== END UPDATE ===
```

---

## Delta #30 · delivered to Sol 2026-08-17, with bundle `08391ae`
*Sol's verdict: evidence delivery **closed** — `rows.json` read and independently verified (18 rows, 18 unique run ids, 90 member errors, scale vectors per seed with n_reference 831/824/839, **0/90** wins over the copy baseline in all three activation slices). D-061 correction, C-010's formulation, D-063, device derivation and the mixed-accelerator refusal all **accepted**. `08391ae` **not certified**: the seeded RNG still reached generators the fork did not restore (D-065), and CLAUDE.md still carried the withdrawn wording. Certified base stays `2875e60`.*

```
=== UPDATE FOR SOL ===
DELTA_ID: 30
PREVIOUS_DELTA_ID: 29
DATE: 2026-08-17
SUBJECT: Micro-closeout. Both items corrected, no fits rerun, and rows.json is
         in the bundle this time.

--------------------------------------------------------------------
1. rows.json IS IN THE BUNDLE.

You are right, and the way this happened is worth one sentence: the exclusion
mechanism I built to keep the bundle REVIEWABLE is what removed the evidence the
bundle existed to DELIVER. You could see digests and counters and not the rows
they described. That is D-036 and D-041 arriving one level down, and my own
"a test passed on my machine" is not evidence in your hands.

The bundle now names rows.json explicitly. No fits were rerun; it is the same
attempt-001 generated at ed550a0 on a clean tree, byte-identical, and its digest
in the manifest is unchanged. You can now read all 18 summary rows, the 90
member validation errors, the per-member auxiliary slices, and the per-row
normalisation metadata directly.

--------------------------------------------------------------------
2. THE RNG ISOLATION WAS CPU-ONLY. FIXED BY DERIVING THE DEVICES.

Confirmed from torch's own documentation of fork_rng: "CPU RNG state is always
forked", device generators only for devices passed in. So devices=[] isolated
CPU and left CUDA advancing, exactly as you said.

MEASURED ON THIS MACHINE'S CUDA DEVICE, not reasoned about:

  old, fork_rng(devices=[])   torch.cuda.get_rng_state() preserved?  False
  new, derived devices        torch.cuda.get_rng_state() preserved?  True
                              and samples still vary on the device:  True

I took your first option rather than the CPU restriction. Restricting MC-dropout
to CPU would put rung 3 of the reliability ladder on a different device from
everything around it at the W4 gate, which seems a worse trade than deriving the
devices properly.

  forkable_devices(model, *tensors) reads the devices of the model's PARAMETERS
  and BUFFERS and of the input tensors. CPU-only returns (None, []) and the
  CPU path is byte-for-byte what it was. A call spanning two accelerator types
  RAISES, because one fork_rng cannot isolate both and quietly forking one of
  them is the defect I would be re-introducing.

Tests: the CUDA test runs where a device exists and asserts the CUDA generator
is preserved AND that samples still vary; the device DERIVATION is covered on
any machine using meta tensors, so a CPU-only checkout still tests the logic;
and the old test is renamed from "the global RNG" to "the CPU RNG", which is
the claim it actually made.

--------------------------------------------------------------------
3. "ENFORCED BY CONSTRUCTION" WAS TOO STRONG. WITHDRAWN.

You are right on every particular. The dataclass constructor is public,
from_evaluation_pool() takes any 2-D tensor including a masked one, and the
low-level metric path accepts raw tensors. I overstated what a type can do.

REPLACED, in the module docstring, the class docstring and the constructor's
own Args, with the narrow true claim:

  - the registered summary path REQUIRES an explicit NormalisationScale and
    will not invent one, so a subset cannot be normalised BY ACCIDENT;
  - the W3 pilot constructs it from the full movement evaluation pool;
  - the W4 runner MUST construct it BEFORE producing the failure mask and MUST
    reuse the same object for the whole-pool and masked calculations.

The third is a CALL-SITE INVARIANT, and it is filed as a required test of the
W4 runner (C-010) rather than as a property this module claims.

Since it cannot be prevented at the type, I made it AUDITABLE. n_reference
records how many transitions the vector was measured over, so a subset-derived
scale is visible in every artefact carrying it. A new test builds one from a
10-row mask against a 200-row pool and asserts it records 10 and produces a
different vector.

The test I had called "a mask cannot recompute the scale" is renamed to "the
summary path will not invent a scale". Its name claimed more than its
assertions established -- which is D-055 and D-057 happening inside a
regression test I wrote for exactly that class of defect. Third time.

--------------------------------------------------------------------
YOUR RULINGS, FILED (D-064)

  rerun account          accepted -- three-layer fix covers both routes
  per-slice baseline     accepted and preferred
  duplicate-run_id       stays in load_runs as defence in depth; the
                         confirmatory runner ALSO owes explicit selection of
                         one immutable attempt -> C-010
  exact reproduction     valid that D-061 PINS the W3 numbers, since the scored
                         set here is the complete movement pool; NOT validation
                         of the masked call site -> tested in the W4 runner
  compact base           allowed for this closeout only; certification remains
                         one chain from 2875e60. Noted, and not repeated.

NUMBERS
  CUDA rng preserved:       old False -> new True (measured on device)
  CUDA test cost:           ~68 MiB, sub-second, 32x4 input through 16 units
  subset-scale audit:       n_reference 10 vs pool 200, different vectors
  fits rerun:               ZERO. attempt-001 is unchanged at its manifest hash
  tests:                    436 -> 440 passing, 1 skipped
  compute consumed:         0 GPU-hours of budget

WHAT I AM ASKING YOU TO ATTACK
  1. Deriving devices rather than restricting to CPU. It is the larger change
     of the two options you offered, and it is mine.
  2. Whether raising on a mixed-accelerator call is right, or whether it should
     fork each type in turn. I chose to raise because I could not test the
     multi-type path on one device.
  3. Whether C-010 as filed states the W4 invariant tightly enough to be a test
     rather than an intention.
=== END UPDATE ===
```

---

## Delta #31 · delivered to Sol 2026-08-17, with bundle `9c0d89d`
*Sol's verdict: **CERTIFIED.** The device-local RNG correction accepted; the skipped two-GPU test accepted as explicitly unverified; the corrected CLAUDE.md wording accepted; leaving the append-only §7 and D-061 entries intact accepted, since D-064 records their correction; and the single `SOL_BUNDLE.txt` plus embedded delta id and digest judged sufficient. **New certified base `9c0d89d` — Week 3 closed and frozen** (D-067).*

```
=== UPDATE FOR SOL ===
DELTA_ID: 31
PREVIOUS_DELTA_ID: 30
DATE: 2026-08-17
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: You are right a third time on the same function. Device-local seeding,
         and the reason my own test could not have caught it.

--------------------------------------------------------------------
FIRST -- THE BUNDLE YOU REVIEWED WAS NOT THIS DELTA'S. MY FAULT.

You were sent sol_bundle_microcloseout.txt at 08391ae. This delta's bundle was
generated correctly at 4a6e4dd and was simply not the file that got pasted.
THREE bundles sat side by side in the repository root -- sol_bundle_closeout,
sol_bundle_microcloseout, sol_bundle_rng_patch -- produced ninety minutes apart,
all plausibly named. Picking the wrong one was the likely outcome, not bad luck,
and the student did nothing wrong.

This is D-036 and D-041 in a third costume. Generating a bundle is not
delivering one. A bundle that selects its own contents can still mislead. And
now: a bundle that cannot be told apart from a stale sibling is not delivered
either. Each time I improved the ARTEFACT and left the HANDOVER unguarded.

FIXED TWO WAYS (D-066):
  one file  SOL_BUNDLE.txt, overwritten every time. The per-session names are
            deleted -- they are regenerable from one command and are not
            evidence; the evidence is attempt-001 and git.
  one line  the bundle's header now names THIS delta -- its DELTA_ID and its
            sha256. The two are produced by different commands at different
            moments, so nothing tied them together. Now you can refuse a
            mismatched pair in one comparison, without trusting either producer.

            I tried the obvious thing first and it does not work: stamping the
            commit INTO the delta changes the delta, which changes the commit,
            so the line always names its own predecessor. I caught that by
            using it -- the stamped value was already one commit stale the
            moment it was written. The dependency has to run bundle -> delta,
            because the bundle is generated last.

I also now verify your eight required properties MECHANICALLY against the
generated file before sending, rather than by looking at it. On the first run
that check failed item two -- the tree was dirty because .gitignore was not yet
committed. That is exactly the sort of thing an eye slides past.

--------------------------------------------------------------------
THE LEAK, REPRODUCED BEFORE I TOUCHED ANYTHING.

I fixed the FORK to cover the devices in use and left the SEEDING on
torch.manual_seed, which seeds the CPU generator AND every accelerator device.
The two sets stopped matching, so the call reseeded generators nothing would
restore.

Your first case, measured on this machine -- and note the computation never
touches the GPU at all:

  CPU model, CPU inputs, forkable_devices() -> (None, [])
  torch.cuda.get_rng_state() preserved across the call?   FALSE

FIXED BY SEEDING DEVICE-LOCALLY, your preferred option:

  seed_locally(seed, device_type, devices):
      torch.default_generator.manual_seed(seed)        # CPU only, not the
                                                       # all-device convenience
      for index in devices:                            # derived devices only
          with module.device(index): module.manual_seed(seed)

Devices absent from forkable_devices() are never seeded. A "meta" device type
seeds nothing rather than looking for a module that does not exist. The set
seeded is now exactly the set the fork restores, by construction of the same
list -- and I mean that literally this time: it is one variable used twice.

--------------------------------------------------------------------
WHY MY TEST COULD NOT HAVE CAUGHT IT, WHICH IS THE PART I WANT ON RECORD.

The CUDA test checked the one device that was both seeded AND forked. That is
the single configuration in which the mismatch cancels. I wrote it against the
machine it runs on rather than against the claim it makes.

That is the D-055 / D-057 defect class -- an assertion that cannot fail in the
configuration it runs in -- arriving through HARDWARE rather than through code.
A one-GPU machine cannot distinguish "seeds what it forks" from "seeds
everything and forks one thing". It is the fourth time this class has bitten me
and the first time the cause was the machine.

--------------------------------------------------------------------
TESTS, INCLUDING ONE I CANNOT RUN.

  CPU call, every CUDA device unchanged      RUNS HERE, and FAILED before the
                                             fix -- this is your first case
  two CUDA devices, used and unused both
    unchanged                                SKIPPED. This machine has one GPU.
                                             DECLARED AS UNVERIFIED, not
                                             reported as passing
  seed_locally directly: CPU generator
    moves, no device generator does          runs on any machine, no GPU needed
  stochasticity + seed reproducibility       retained, and now asserted ON THE
                                             DEVICE too: same seed identical,
                                             different seed differs, spread
                                             still 1e-3+

The multi-GPU guarantee therefore rests on seed_locally seeding only the derived
indices, which the third test covers directly, plus the two-device test standing
ready for a machine that can run it. I would rather say that than imply
coverage I do not have.

--------------------------------------------------------------------
THE STALE CLAUDE.md SENTENCE -- CORRECTED, AND ONE I AM LEAVING ALONE.

You are right that it is the dangerous one: it instructs the NEXT Claude, who
has no memory, using the model you withdrew. Replaced with the explicit-and-
auditable claim plus the C-010 pointer, and a second instance in the same file's
module map is corrected too. I swept both the code and the docs for the phrasing
and there are now no surviving instances outside the entries that withdraw it.

One I am deliberately NOT editing, and I want you to know it is a choice: the
PROJECT_STATE.md section 7 session-log entry from the closeout still contains
"Enforced by construction". Section 7 is append-only (D-014, which exists
because I once reordered that ledger), and the entry immediately following it
withdraws the claim by name. If you would rather I break the append-only rule to
strike it, say so and I will -- but I did not want to make that call myself.

Same reasoning for D-061 in the ledger: untouched, with D-064 naming it as the
correction, which is how D-042 corrected D-039 and D-044 corrected D-042.

NUMBERS
  CPU-only call, CUDA rng preserved:   old FALSE -> new TRUE (measured)
  devices seeded on a CPU call:        0 (was: every CUDA device)
  fits rerun:                          ZERO. attempt-001 unchanged, digest
                                       cdaa497cec68 on rows.json as before
  tests:                               440 -> 442 passing, 2 skipped
  compute consumed:                    0 GPU-hours of budget

YOUR TWO PROVISIONAL RULINGS ARE TAKEN AS GIVEN, AND BOTH ARE IMPLEMENTED

  two-device test    stays SKIPPED and explicitly UNVERIFIED. Never reported as
                     passed. The implementation-level test carries the
                     guarantee: seed_locally() moves the CPU generator and NO
                     device generator, on any machine, GPU or not.
  append-only        section 7 and D-061 left intact, D-064 correcting them in
                     place in the chronology. CLAUDE.md now carries ONLY the
                     explicit-and-auditable description -- both instances, and
                     I swept code and docs for the phrasing.

WHAT I AM ASKING YOU TO ATTACK
  1. Whether a single file name plus the bundle naming its delta is enough, or
     whether the bundle should be generated BY the same command that finalises
     the delta so the two cannot diverge at all.
=== END UPDATE ===
```

---

# §7 session log — Week 3, archived on certification at `9c0d89d`

### 2026-08-16 (W3 audit) · Seven defects, one of which moves a registered endpoint · Claude
**Did:** the Week 3 audit (D-060), on the precedent of D-015 and D-021 — a behavioural probe of everything built this week, before Week 4 builds a gate verdict on it. Nine Sol reviews are not a substitute: Sol reviews what is reported plus a diff, and cannot probe running code.
**Seven defects, three serious.** **W3-1** is the one that matters: P§10.3 requires per-dimension normalised error but never says *which set* defines the normalisation, and the scale was recomputed from whatever subset it was handed. Because the scale is a **vector** it does not cancel between the ratio's numerator and denominator — so the **registered H2 endpoint moves by up to 4.6%** with a choice nobody made, and the W4 Friday failure set is exactly such a subset. **W3-2**: the pilot bypassed `RunLogger` entirely, so its outputs had no commit, no dirty flag, no package versions, no `seed_partition` — P§13.7's requirement, using machinery Week 1 built for it. **W3-4**: `member_predictions` left every model in eval mode; inert for this MLP, but P§9.3 plans **MC-dropout** as reliability-gate fallback B2, and under it a model left in eval mode returns deterministic predictions with **zero disagreement** — which reads as "MC-dropout also fails H1" and triggers a false pivot at the gate the fallback exists for.
**Also:** the activation report used one member of five; `TrainConfig.val_fraction` was dead after D-052; `train_index` was unvalidated and **torch wraps negative indices silently**, so a bad resample would train on the wrong rows and fail later for an unrelated reason.
**Checked and correct**, which is half the point of an audit: checkpoint restoration on all three exit paths, patience counting, five members sharing no stream before or after training, member results independent of `ensemble_size`, nested prefixes still exact after the restructure, validation/evaluation byte-identical across sizes **and arms**, **zero** shared (obs, action) pairs between train and evaluation, passthrough correct for all five actions and row-wise on mixed batches, trunk isolated under `predict_next_obs`, the block bootstrap genuinely duplicating episodes, the partial minibatch used, no NaN anywhere, and 300 units / 150-150 / 8,197 fits unchanged.
**D-047's conditional is answered.** Across all five members and every dataset size the detached auxiliary head **never** beats its copy baseline — 0 of 3 seeds everywhere, best member 0.225 against 0.169, no improvement with data. Compute is not the obstacle (a second trunk is 1.98×, taking the design from ~1.6 to ~3.2 CPU-hours). **Recommendation: downgrade rather than spend it** — activation carries no hypothesis and P§10.2's primary error excludes it. Recorded for Sol, not decided.
**Result:** 413 → 418 tests, every finding with a named regression test. **Zero GPU-hours.**
**Next:** W4 Mon — the trend test, once Sol has ruled on W3-1's scale choice, which W4 consumes.
---

### 2026-08-17 (W3 closeout) · Two fixes that fixed the symptom, and a ruling on the scale · Claude
**Did:** Sol's review of deltas 27–28. D-059's interpretation corrections accepted; **`0b09f84` not certified**, and Week 3 not closed on two serious findings. Both verified before anything changed, per the standing rule, and **one of the two is different from how it was stated**.
**1. The MC-dropout fix did not fix MC-dropout.** Sol is exactly right: `member_predictions` restored `model.training` but still called `eval()` before the forward pass, so dropout was off *during* inference. Reproduced against the old path on a model with a real dropout layer — sample spread and mean pairwise disagreement both **exactly 0.000e+00**, against 0.298 and 0.547 under the replacement. Replaced with an explicit prediction policy, dropout re-activated per no-grad pass, modes restored per **submodule**, and **MC-dropout on a dropout-free model now raises** — `WorldModel` has none, so rung 3 is an explicit architectural choice rather than a silent zero.
**2. The rerun hazard is real, by a different route.** The append-with-restarting-counter mechanism is real at the class level (measured: ten records numbered 0–4, 0–4) but **unreachable** through `RunLogger.start`, which `write_run_record` rejects first — a same-scope rerun was refused *before writing anything*, files byte-identical. What is reachable is the same end state via a **different-scope** rerun: no `run_id` collision, so two executions' records and exports sat in one directory while `rows.json` described only the second. Fixed at three layers: `RunLogger` refuses to append (and continues the counter when told to), the pilot writes into a fresh `attempt-NNN` it never reopens, and `load_runs()` raises when one `run_id` appears in two directories.
**D-061 adopted as ruled.** The scale is measured once from the full movement evaluation pool before any mask. Enforced by construction: `NormalisationScale` is the only accepted argument and its only constructor reads a pool, so masking has nothing to recompute from. The **stale invariance claim is corrected in the artefacts** — it was in the module docstring and in a test's own docstring, not only in the ledger. **The pilot's numbers do not move:** a full rerun reproduces all four uncertainty fields at every size and seed, and all 90 member validation errors, exactly.
**D-063 adopted:** no second trunk; the head is a non-decisional diagnostic, and all four views are now reported per member with a **per-slice** copy baseline.
**Also found:** `runs/` and `figures/` are gitignored, so the evidence manifest Sol asked for **could never have reached a bundle**. The compact artefacts are now tracked by explicit exception; `manifest.json` + `rows.json` carry 18 runs × 5 member errors = 90 fits in 64 KB.
**Result:** 418 → 436 tests. **Zero GPU-hours** — the 90-fit rerun was CPU.
**Next:** deliver the closeout bundle. W4 Mon stays blocked until it passes review.
---

---

### 2026-08-17 (W3 micro-closeout) · A claim narrowed, and an isolation that only held on CPU · Claude
**Did:** Sol's review of delta 29. The substantive Week 3 corrections are **accepted** — D-061, D-063 and D-062's logging/attempt mechanism outright, and D-062's MC-dropout mechanism on CPU. All four of my questions were ruled on: the corrected rerun account accepted; the per-slice copy baseline accepted and preferred; the duplicate-`run_id` guard confirmed as belonging in `load_runs` **as defence in depth**, with the confirmatory runner additionally owing an explicit immutable-attempt selection; and exact reproduction accepted as valid evidence that D-061 **pins** the W3 numbers — but **not** as validation of the future masked call site. Two narrow items remained, both mine, neither requiring a rerun (D-064).
**1. "Enforced by construction" was too strong, and Sol is right.** `NormalisationScale`'s dataclass constructor is public, `from_evaluation_pool()` accepts a masked tensor, and the low-level metrics still take raw tensors. The true claim is narrower: the registered summary path **will not invent** a scale, so a subset cannot be normalised by accident — the rest is a **call-site invariant** the W4 runner must carry (C-010). Since it cannot be prevented at the type it is made auditable: a masked construction records the mask's size, and a test now asserts that (10, not 200) with a different vector. The old test's *name* claimed what its assertions did not, which is the D-055/D-057 defect in my own regression test.
**2. The RNG isolation was CPU-only.** `fork_rng(devices=[])` forks CPU always but device generators only for devices it is handed, so a GPU run advanced the CUDA generator — and the fallback estimator is the thing that would run on a GPU. Verified on this machine's device rather than reasoned about: under the old call `torch.cuda.get_rng_state()` was **not** preserved; under the fix it is, and the samples still vary. Devices are now derived from the model's parameters, buffers and inputs; two accelerator types raise; the CPU path is unchanged.
**Also, and it is the sharper lesson:** the bundle's own exclusion mechanism — built to keep the bundle reviewable — **excluded the evidence the bundle existed to deliver**. Sol could see digests and counters but not the 18 rows, the 90 validation errors or the per-member auxiliary values. A test passing on my machine is not evidence in the reviewer's hands. `rows.json` ships explicitly from now on.
**Result:** 436 → 440 tests. **Zero GPU-hours** of budget; one sub-second, ~68 MiB GPU test now runs where a device exists.
**Next:** deliver the micro-closeout. Sol expects to certify Week 3 on it, with no further scientific decision.

---

### 2026-08-17 (W3 RNG correction) · The seeding was wider than the fork · Claude
**Did:** Sol's review of delta 30. **Every scientific item is now accepted** — `rows.json` read and independently verified by Sol (18 rows, 18 unique run ids, 90 member errors, one scale vector per seed, reference counts 831/824/839, **0/90 wins over the copy baseline in all three activation slices**), the D-061 correction, C-010's formulation, D-063, device derivation, and the mixed-accelerator refusal. Certification held on one narrow code item, and Sol was right again (D-065).
**The leak.** D-064 fixed the *fork* to cover the devices in use and left the *seeding* on `torch.manual_seed`, which seeds the CPU generator **and every accelerator device**. The two sets stopped matching, so the call reseeded generators nothing would restore — including on a **CPU-only** call, where the computation never touches the GPU at all. Reproduced before changing anything: `torch.cuda.get_rng_state()` was not preserved across a pure-CPU MC-dropout call. Fixed by seeding device-locally — the CPU default generator directly, then each derived device — so the set seeded is exactly the set the fork restores.
**Why my own test missed it, which is the part to keep.** The CUDA test checked the one device that was both seeded *and* forked: the single configuration where the mismatch cancels. Written against the machine it ran on rather than against the claim. That is D-055/D-057's defect class arriving through **hardware** — a one-GPU machine cannot tell "seeds what it forks" from "seeds everything, forks one thing". The two-device test is written and **skips here**; it is declared unverified rather than reported as passing.
**Also:** `CLAUDE.md` still taught the next Claude the withdrawn "a mask has nothing to recompute from" model, in the file a reset Claude reads first. Corrected, with a pointer to C-010. The §7 entry carrying the old wording is **not** edited — §7 is append-only (D-014) and the entry after it withdraws the claim by name.
**Result:** 440 → 442 tests, 2 skipped. **Zero GPU-hours** of budget.
**Next:** deliver the RNG patch. Sol certifies Week 3 on it.

---

### 2026-08-17 (W3 bundle repackage) · The right bundle existed; the wrong one was sent · Claude
**Did:** Sol reported delta 31's bundle as stale — `08391ae`, 440 tests, the old `torch.manual_seed` — and it was, because **three** bundle files sat side by side in the repository root, generated ninety minutes apart, all plausibly named. Sol reviewed a delta describing code its bundle did not contain. The correct bundle had been generated at `4a6e4dd` and was simply not the one picked. **My packaging failure, not the student's** (D-066).
**This is D-036 and D-041 in a third costume.** Generating a bundle is not delivering one; a bundle that selects its own contents can still mislead; and now — a bundle that cannot be told apart from a stale sibling is not delivered either. Each time the fix improved the *artefact* and left the *handover* unguarded.
**Fixed:** one canonical `SOL_BUNDLE.txt`, overwritten each time, with the per-session names deleted so a stale copy cannot survive beside a fresh one; and a `BUNDLE_COMMIT:` line in every delta, so the delta and the bundle — produced by different commands at different moments — can be checked against each other in one line. Sol's eight required properties are now verified **mechanically against the generated file** before sending; on the first run that check caught a dirty tree, which is exactly what an eye slides past.
**Sol's provisional rulings, both accepted:** the two-device test stays skipped and **explicitly unverified**, carried by the implementation-level test that `seed_locally()` touches only the CPU generator and the derived indices; and the append-only §7 and D-061 entries stay intact, with `CLAUDE.md` carrying only the corrected description.
**Result:** 442 tests, 2 skipped, unchanged — no code changed. **Zero GPU-hours.**
**Next:** resend delta 31 with its actual bundle.

---

## Delta #32 · delivered to Sol 2026-08-17, with bundle `7dbcd32`
*Sol's verdict: certification filing **accepted**; `7dbcd32` **certified** as the documentation/state continuation, to be used as the next review base while the frozen implementation remains `9c0d89d`. Ruling 1: **do not special-case the non-monotone small end** — reading rule frozen in full (D-068). Ruling 2: **the W4 gate uses development seeds**, the W10 verdict confirmatory, never pooled. W4 Mon authorised.*

```
=== UPDATE FOR SOL ===
DELTA_ID: 32
PREVIOUS_DELTA_ID: 31
DATE: 2026-08-17
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: Week 3 filed as frozen, with its boundaries. Housekeeping cleared.
         Nothing scientific in this one -- it exists so the freeze is recorded
         before W4 Mon touches anything.

--------------------------------------------------------------------
CERTIFICATION FILED (D-067)

9c0d89d recorded as the certified base in PROJECT_STATE section 1, in CLAUDE.md,
and as the BASE in the bundle command above. Week 3 marked CLOSED AND FROZEN.

Your accepted conclusions are filed at the width you allowed them, not wider:
the pilot is exploratory development evidence and not an H1/H2 verdict; D-061
fixes normalisation to the full movement pool before masking and the W3 numbers
are unchanged by it because the scored set equals that pool; no second
activation trunk, the head non-decisional, 0/90 against its paired copy
baseline; 18 runs and 90 member results with immutable-attempt provenance;
MC-dropout an explicit policy that fails closed on the dropout-free WorldModel.

THE BOUNDARIES ARE FILED IN THE SAME PLACE AS THE CERTIFICATION, deliberately,
so the two cannot be read apart -- the D-036 lesson applied to a permission
rather than to a bundle:

  no confirmatory execution, no repair validation      C-008, C-009
  no masked failure-set analysis until C-010 exists    REQUIRED BEFORE W4 FRI
  MC-dropout rung 3 needs an explicit architectural decision (no dropout)

--------------------------------------------------------------------
HOUSEKEEPING YOU FLAGGED

CLAUDE.md said "440 passing, 1 skipped". Now 442/2, alongside the new certified
base, the frozen Week 3 status, and the boundaries above. That file is what a
reset Claude reads first, so a stale count there is how a reset agent
mis-reports the suite in its own next delta.

Also archived Week 3's six section 7 entries into PROJECT_STATE_ARCHIVE.md now
that it is frozen -- 387 lines back down to 334 against the 500 cap, nothing
condensed, the certification entry kept in place. The archive is complete.

--------------------------------------------------------------------
WHAT W4 MONDAY WILL BE, SO YOU CAN OBJECT BEFORE IT IS BUILT

Schedule W4 Mon: implement the trend test ONCE and use the same function for the
W4 gate and the W10 H1 verdict -- rank correlation of disagreement against
dataset size across the six sizes, with a confidence interval over seeds,
returning coefficient, interval and pass/fail. Not an effect-against-variance
comparison (Plan 4.2).

Two things I intend to carry into it, and would rather you challenged now:

  1. The pilot's disagreement curve is NON-MONOTONE at the small end -- it peaks
     at N=250, reproduced in all three paired seeds. A rank correlation over six
     sizes is exactly the instrument that bends on that. I do not intend to
     handle it specially. It is a property of the data, the test is
     preregistered, and choosing a friendlier instrument after seeing the curve
     is the thing preregistration exists to prevent. But you should know that I
     know, and that a rung-0 failure at the W4 gate is a live possibility
     rather than a surprise.

  2. The trend test runs on DEVELOPMENT seeds for the W4 gate and confirmatory
     seeds for the W10 verdict, and it is the SAME function. I will make the
     partition an explicit argument rather than something a caller can drift
     on, per D-034 and D-040.

C-010 is queued ahead of W4 Fri, not W4 Mon, since Monday's test does not mask.

NUMBERS
  certified base:      2875e60 -> 9c0d89d
  decisions certified: D-061 ... D-066 in one chain
  tests:               442 passing, 2 skipped (unchanged; no code this session)
  state file:          387 -> 334 lines against the 500 cap
  compute consumed:    0 GPU-hours of ~110-145 budgeted

WHAT I AM ASKING YOU TO ATTACK
  1. Whether refusing to special-case the non-monotone small end is right, or
     whether the preregistered test needs a stated reading rule BEFORE it runs
     rather than after the coefficient exists.
  2. Whether the W4 gate should be run on development seeds at all, given every
     number it produces is excluded from confirmatory results by D-034.
=== END UPDATE ===
```

---

## Delta #33 · delivered to Sol 2026-08-17, with bundle `a84cf6c`
*Sol's verdict: **`a84cf6c` CERTIFIED** as the W4 Monday trend-test implementation; the development-pilot calculation accepted as a smoke-test result and explicitly not the gate. Ruling 1: do not move the statistical rule — separate gate **eligibility** into a wrapper (3 configurations × 5 development seeds, all-three-must-pass). Ruling 2: keep the exact six-size refusal. Ruling 3: keep fail-closed on undefined replicates but **narrow the explanation** — cancellation between opposing curves, not evidence against a trend (D-070).*

```
=== UPDATE FOR SOL ===
DELTA_ID: 33
PREVIOUS_DELTA_ID: 32
DATE: 2026-08-17
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: W4 Mon built to your frozen rule. It passes on the pilot -- and the
         interval is coarse in a way you should rule on before Tuesday.

--------------------------------------------------------------------
THE FUNCTION, BUILT TO THE RULE YOU FROZE (D-068)

src/bu/stats/trend.py. One function, both stages, 22 tests. Every clause you
specified is implemented as written:

  statistic     Spearman's rho, ascending size vs mean pairwise disagreement
  grid          ALL SIX registered sizes
  direction     negative expected
  pass rule     the ENTIRE 95% interval below zero. Touching zero fails.
                Entirely above zero is REVERSED and fails. Constant or
                undefined fails.
  no veto       out-of-order points act only through rho and its interval
  interval      exact paired seed-block bootstrap, ordered tuples enumerated:
                3^3 = 27, 5^5 = 3125. NO RNG EXISTS.
  quantiles     2.5 / 97.5, method="linear", declared in code
  point est.    rho on the across-seed mean curve
  diagnostics   per-seed curves and per-seed rho, reported, NOT a vote

Your nine required tests all exist, plus: rho checked against scipy including
ties, the partition boundary, and that the partition label cannot change the
mathematics -- same curve at development and confirmatory seeds returns an
identical rho, interval and verdict.

ONE THING I ADDED THAT YOU DID NOT ASK FOR. The size grid must be exactly the
six registered sizes. Without that check the grid is a keyword argument, and a
five-point statistic computed over a trimmed grid is INDISTINGUISHABLE from the
registered one in every artefact that carries it -- the "drop the awkward small
end" move arriving through a parameter instead of a decision. I found it because
my first version of that test passed for the wrong reason.

--------------------------------------------------------------------
APPLIED TO THE PILOT -- DEVELOPMENT SEEDS, AND NOT THE GATE.

  rho (across-seed mean curve)   -0.9429
  95% interval                   [-0.9429, -0.8286]
  verdict under the frozen rule  PASS -- the whole interval lies below zero
  seeds / resamples              3 development / 27 exact
  per-seed rho                   -0.9429, -0.8286, -0.9429

  mean curve:  N=100 0.6014 | 250 0.8150 | 500 0.5502 | 1000 0.4159 |
               2500 0.2685 | 5000 0.2127

YOUR PREDICTION HELD EXACTLY. The N=250 peak costs ONE of fifteen pairwise
inversions. rho weakens from -1.0 to -0.9429 naturally, with nothing removed and
nothing smoothed, and the interval stays wholly negative.

--------------------------------------------------------------------
THE LIMITATION, WHICH I THINK MATTERS MORE THAN THE VERDICT.

The 27 resamples take only TWO DISTINCT VALUES:

  -0.942857  x20 of 27
  -0.828571  x7 of 27

So the "95% interval" here IS THE FULL SUPPORT of the distribution -- the 2.5th
percentile is its minimum and the 97.5th is its maximum. Its narrowness is a
property of having three highly consistent seeds, not evidence of precision.
With three blocks the exact bootstrap simply cannot resolve a tail.

I am not proposing a change to the rule. I am flagging it because SCHEDULE W4
TUESDAY RUNS THE GATE AT FIVE SEEDS ACROSS THREE CONFIGURATIONS, and at five
seeds the support is 3,125 and the quantiles mean something. If any part of
Tuesday ends up running at three seeds, it inherits this coarseness, and I would
rather that be a decision than a discovery.

Question: does the pass rule need a minimum-seed condition attached to it, or is
"the whole interval below zero" acceptable even when the interval has two atoms?
The rule as frozen would pass a three-seed result whose distribution has no tail
to speak of.

--------------------------------------------------------------------
BOUNDARIES OBSERVED

  W4 gate      development seeds only. The pilot run above is exactly that,
               and it is NOT the gate -- Tuesday is.
  W10 verdict  confirmatory only. Same function, and the partition argument
               is validated, never inferred, never pooled. Tested.
  H1 result    the coefficient above is NEVER quoted as the H1 result.
  C-010        still queued ahead of W4 Fri. Monday creates no failure mask,
               and the trend test never touches the scale.

NUMBERS
  rho / interval:       -0.9429, [-0.9429, -0.8286], PASS (development)
  distinct resamples:   2 of 27 -- the coarseness above
  pairwise inversions:  1 of 15, from the N=250 peak
  tests:                442 -> 464 passing, 2 skipped
  compute consumed:     0 GPU-hours

WHAT I AM ASKING YOU TO ATTACK
  1. The two-atom interval. Does the frozen pass rule need a minimum-seed
     condition, and if so is it three or five?
  2. Whether requiring the exact six-size grid is right, or whether a legitimate
     future caller needs a subset I have now made impossible.
  3. Whether "undefined coefficient anywhere in the resample distribution fails"
     is the correct handling, or whether only an undefined POINT estimate should
     fail while undefined resamples are dropped.
=== END UPDATE ===
```

### 2026-08-17 (W3 certified) · Week 3 frozen at `9c0d89d` · Claude
**Did:** Sol certified `9c0d89d`, covering the complete chain from `2875e60` through the pilot, the audit and D-061 … D-066. **Week 3 is closed and frozen** (D-067). Filed the certification, its accepted conclusions and — the part that matters more — its **boundaries**, which travel with it and are not relaxed by it: no confirmatory execution, no repair validation (C-008, C-009), **no masked failure-set analysis until C-010 exists, required before W4 Friday**, and MC-dropout rung 3 needs an explicit architectural decision because `WorldModel` has no dropout. Cleared Sol's non-blocking housekeeping: `CLAUDE.md` said 440/1 and now says 442/2, alongside the new base and status.
**What the six-review close actually cost, and where.** Every finding was verified before anything changed and every one stood. But only two were code defects reachable by a user; **three were about claims rather than code** — an invariance that does not hold for a vector, an enforcement a type cannot provide, and an isolation that held only on the hardware it was tested on — and one was **packaging**, where the right bundle existed and the wrong one was sent. The sentences were consistently more expensive to get right than the code was.
**Standing corrections now live in `CLAUDE.md`:** restoring state is not fixing a mechanism; verify a finding's *route*, not just its conclusion; and a test written against the machine it runs on can pass in the one configuration where the defect cancels.
**Result:** 442 tests, 2 skipped. **Zero GPU-hours** of the ~110–145 budgeted.
**Next:** W4 Mon — the trend test. Read it knowing the pilot's disagreement curve peaks at N=250, which is what a rank correlation over six sizes is most sensitive to.

---

### 2026-08-17 (W4 Mon) · The trend test, under a rule frozen before it saw data · Claude
**Did:** Sol certified `7dbcd32` as the documentation continuation — use it as the next `BASE`; the frozen *implementation* stays `9c0d89d` — and **authorised W4 Mon under a fully specified reading rule** (D-068). Built `src/bu/stats/trend.py`: one function for the W4 gate and the W10 verdict, 22 tests covering every clause Sol required plus the partition boundary.
**The rule was frozen first, and that is the point.** Spearman's rho over **all six** registered sizes, negative expected, **pass only if the whole 95% interval is below zero**, undefined or constant fails, out-of-order points carry no separate veto. The interval is an **exact** paired seed-block bootstrap — 27 or 3,125 ordered tuples enumerated, **no RNG at all**, quantile method declared in code. Removing N=100 or N=250, smoothing, or switching to Kendall are each forbidden by name.
**On the pilot** (development seeds — Schedule W4 Mon's criterion, **not** the gate): **rho = −0.9429, 95% CI [−0.9429, −0.8286], PASS.** Sol's prediction held exactly: the N=250 peak costs **one** of fifteen pairwise inversions, weakening rho from −1.0 naturally, with nothing removed.
**The limitation is the more useful result.** With three seeds the 27 resamples take only **two** distinct values (−0.9429 ×20, −0.8286 ×7), so the "95% interval" *is* the full support — its narrowness is a property of three consistent seeds, not evidence of precision. At five seeds the support is 3,125 and the quantiles mean something. Flagged for Sol before Tuesday, because if gate day 1 also runs at three seeds it inherits the same coarseness.
**One loophole closed while testing.** The size grid is now required to be exactly the six registered sizes. Without it the grid is a keyword argument, and a five-point statistic over a trimmed grid is indistinguishable from the registered one in every artefact carrying it — the "drop the awkward small end" move arriving through a parameter rather than a decision. Found because the first version of that test passed for the wrong reason.
**Result:** 442 → 464 tests, 2 skipped. **Zero GPU-hours.**
**Next:** W4 Tue, gate day 1 — five seeds across three configurations, recording the verdict **and the rung**.

---

### 2026-08-17 (W4 Mon closeout) · Three rulings, and the gate wrapper Tuesday needs · Claude
**Did:** Sol **certified `a84cf6c`** as the W4 Monday trend-test implementation and ruled on all three open questions (D-070). Built `src/bu/stats/gate.py` — the wrapper that makes a gate verdict *authorised* rather than merely computed.
**Ruling 1 — do not move the statistical rule after seeing the two-atom interval.** Separate the *statistical result* from *gate eligibility* instead: the three-seed pilot satisfies the frozen rule and cannot be a gate verdict. The wrapper requires exactly three predeclared configurations × exactly five development seeds × six sizes, and **rung 0 passes only if all three configurations pass** — no majority vote, no pooled curve, because configuration sensitivity is itself a reliability failure. The three configurations are predeclared with their **18 exact `config_id`s frozen as golden values**: a configuration spans six units, not one, and deriving the ids at run time would let an identity change silently redirect the gate (the D-016 lesson).
**Ruling 2 — keep the exact six-size refusal.** No legitimate subset caller exists for the registered statistic; an exploratory subset analysis must be a separately named descriptive function returning no `TrendResult` and no verdict.
**Ruling 3 — a correction to my reasoning, not the code.** Undefined replicates still fail closed and are never dropped — dropping them would condition the distribution on the statistic being defined and could **manufacture** a directional interval. But I had justified it by calling a flat curve "the strongest possible evidence against a trend", and Sol is right that it can equally come from **cancellation between opposing non-constant curves**. A test now builds exactly that: slopes −0.1, −0.3, +0.2 where one resample cancels to flat, **the point estimate is a perfect −1.0, and the result still fails** — which is why dropping the undefined replicates would have been dangerous rather than merely untidy.
**Result:** 464 → 483 tests, 2 skipped. **Zero GPU-hours.**
**Next:** W4 Tue, gate day 1 — 90 ensembles / 450 fits, the first real compute. Ask before starting it.

## 8. → TO SOL — *moved to its own file*

The delta Sol receives lives in **`DELTA_TO_SOL.md`** (D-023). It was moved out
because consolidating four sessions pushed this file past its 500-line paste
cap, and the two files have different audiences anyway: this one is Claude's
reconstruction of state, that one is Sol's feed.

It also removes an instruction that was easy to get wrong. "Paste §8" meant
scrolling to find a section boundary; "paste `DELTA_TO_SOL.md`" does not.

**Current status:** see the delivery flag at the top of `DELTA_TO_SOL.md`.

### 2026-08-18 (W4 Tue prep) · Sol's two blockers on the gate wrapper · Claude

**Did:** Sol reviewed delta 34, accepted the exact-grid rationale, the undefined-bootstrap correction, the cancellation regression test, the three-configuration design, five-seed eligibility and all-three-must-pass aggregation — and **refused to certify `311a23c` as the executable Tuesday gate** on two blockers, with an explicit instruction not to begin Tuesday's compute or request the GPU. Both verified before anything was changed (D-071).

**Blocker 1, and it is worse than the finding says.** The gate accepted bare curves and then stamped the eighteen golden `config_id`s onto the result without checking the curves came from those configurations. Reproduced: **five lines of invented floats returned `passed=True` carrying all eighteen golden ids, with no model ever fitted** — not "could look authorised", but a PASS indistinguishable from a real one in every artefact.

**The thing neither of us had named.** `ensemble_size` and `bootstrap_ratio` are deliberately non-identity fields, so **rungs 0, 1 and 2 share `config_id`, `run_id` and `fit_id` exactly** — verified directly. Sol's requested check, config_id against the golden list, is therefore *necessary but not sufficient*: it passes unchanged for rung-1 evidence presented as rung 0. The rung is only verifiable against the training parameters in the run record. Both checks are now in, and a test asserts the identity collapse so that if the rungs ever become identity-bearing, the provenance story gets revisited instead of silently changing.

**Blocker 2.** `reliability_gate(curves, rung=0, estimator="mc_dropout")` was accepted. The free-form override is gone; estimator and every training parameter come from a frozen `RungSpec` chosen solely by rung. Tested as a property rather than an argument name: a tampered `estimator` in a saved record does not survive `recompute()`.

**Built:** `GateEvidence` / `EvidenceCell` and an evidence-bound `reliability_gate(evidence, *, rung)`; the curve-only path demoted to the private `_gate_from_curves`; `GateEvidence.from_attempt()` reading one immutable attempt and failing closed on any missing field, a dirty tree, or the W3 pilot's own manifest; all ninety raw cells on the record with `recompute()` re-running the whole path from it. Sol's answer 2 was verified as *necessary*, not just adopted — `TrendResult` keeps only `mean_curve` and `per_seed_rho`, from neither of which the 5×6 matrix is recoverable.

**Frozen before rung 0 runs, on Sol's answer 3:** rung 0 = ensemble/5/1.0, rung 1 = ensemble/10/1.0, rung 2 = subbagging/10/**0.5**. Rungs 3–4 deliberately unfrozen until immediately before execution. **Pre-data semantic correction to P§11.3:** the plan says raise the bootstrap ratio to raise member diversity, but the implemented ratio is draws over episode count, so coverage is 1 − e^−ratio — measured **0.395 / 0.635 / 0.866** at 0.5 / 1.0 / 2.0. Raising it makes members *more* alike. Rung 2 lowers it, which is what the plan actually asks for.

**Numbers:** tests 483 → **507 passing**, 2 skipped. Zero GPU-hours; no gate cell executed; no data seen.

**Next:** Sol re-reviews delta 35 and the fix. **No Tuesday compute until it is certified.** Then the student's device answer, then gate day 1. C-010 before W4 Friday; C-011 (one attempt directory per rung) before the ladder.

### 2026-08-18 (W4 Tue prep, round 2) · The evidence contract, and the runner that emits it · Claude

**Did:** Sol reviewed delta 35, accepted everything D-071 built — frozen rungs, the subbagging correction, the removed estimator override, the 90-cell grid, raw-curve serialisation and recomputation, and the rung-identity discovery — and **refused to certify `867145d`** on one finding: the binding was to claims, not to execution. Verified first, and it reproduces exactly. A fabricated manifest with the correct 90 identities, correct rung parameters and invented floats **passed and returned PASS**. D-071's five-line attack had simply become a ninety-entry one (D-072).

**Fixed by moving the boundary to the artefacts.** Each run entry now carries its complete canonical `Config`; the gate reconstructs it and derives every identity from that, refusing any flattened value that contradicts it. The **complete** `TrainConfig` is checked against the frozen rung — Sol was right that `lr`, `batch_size`, `max_epochs` and `patience` were unchecked, and a test now asserts the frozen field list covers `TrainConfig` exhaustively. The manifest is cross-checked against `run.json` and `metrics.jsonl` written at training time, members are **counted from the metric stream** rather than believed, every artefact digest is verified, and each disagreement must reproduce from the row it names.

**Two things the ruling as written would not have caught, both found by building it.** `granularity` is a `train_ensemble` argument, not a `Config` field, so it could never be derived from the config — it is now attested in the run record and cross-checked. And my first attempt-identity derivation, `rung + spec hash + directory name`, **produced the same id for two different attempts** — exactly the collision Sol's ruling names. Building two proved it; the identity is now derived from a digest of the run records themselves.

**Built `src/bu/experiments/w4_gate.py`** — the runner, which emits evidence and decides nothing. Refuses confirmatory seeds and unfrozen rungs before doing any work; writes one immutable attempt per **rung-spec hash** (**C-011 done**, at the finer granularity Sol ruled); builds the normalising scale from the full movement evaluation pool before any mask and reuses that object across all six sizes (**C-010 partly done**, masked call site still W4 Fri); digests the evaluation pool so a curve measured on six different pools is refused.

**One defect found by probing rather than by review:** a missing `rows.json` raised an incidental `FileNotFoundError` rather than refusing. An accidental runtime error is not an invariant — it is now an explicit refusal.

**Numbers:** tests 507 → **532 passing**, 2 skipped. A 10-fit smoke run took **3.5 s** on CPU and reproduced the W3 pilot's uniform/N=100/seed-0 disagreement of **0.685593** exactly, so the full 450-fit rung 0 is minutes on CPU rather than the hour previously estimated. **Zero GPU-hours**; no gate cell executed; the smoke run went to a scratch directory, never to `runs/`.

**Next:** Sol reviews delta 36 — the runner, the manifest code, the gate changes and the tests. **No Tuesday compute until it is certified.** Then the student's device answer, then gate day 1.

## Archived from PROJECT_STATE.md §7 on 2026-08-20 — the W4 Tuesday gate and its closeout

*Moved when the file passed its 500-line paste cap. W4 Tuesday is certified at `ca545ed` and closed; the decisions these produced are D-071 … D-077 and remain indexed in §3. Nothing is condensed.*

### 2026-08-18 (W4 Tue prep, round 3) · The closeout, and an accepted architecture · Claude

**Did:** Sol **accepted the architecture** — canonical `Config` reconstruction as the source of identity, complete `TrainConfig` freezing, granularity attested outside `Config`, run and member records at the execution boundary, source-row binding, evaluation-pool consistency, content-derived attempt identity, runner and verdict separated. `4e92fda` accepted in design, not certified, because six fields the contract advertised were never actually compared (D-073). All six verified before fixing.

**The one that mattered most:** the run record carries **five** training-time attestations and only `granularity` was checked — so a manifest could borrow an honest run record while changing the evaluation pool it claimed to evaluate on, or the experimental obligation the run discharged. All five now cross-checked, missing ones fail closed. The others: manifest version and frozen rung spec were required but never compared; normalisation was checked for constancy across sizes but never against the row it was supposedly computed under; the attempt identity hashed only run records, which are written *before* training, so two evidence sets with copied start records and different outputs shared an id; declared counts and the metric schema version were unverified, the latter reusing `config.SCHEMA_VERSION` for a schema that evolves independently; and `run()` recorded a dirty tree, ran all 450 fits, and only then had the verdict refused.

**Sol's answers to my two open questions, both rulings against more machinery.** Per-transition exports are not needed to authorise the gate, and weight digests are not either — a checkpoint digest proves a file did not change, not that it was trained under the declared configuration. The trust model protects against accidental substitution, stale evidence, mixed executions and post-run mutation, **not** a malicious author fabricating every layer consistently. That gap is now written down as deliberate rather than left as my open worry. `EVIDENCE_CONTRACT_VERSION` also left `constants.py`: schema versions must stay evolvable, which is the opposite of a preregistered quantity.

**One test of mine was a tautology.** `assert X is not Y or True` cannot fail — the D-055 failure mode, in the very delta where I described avoiding it. Replaced with the property: move the gate's schema version and watch the refusal move with it.

**Numbers:** tests 532 → **548 passing**, 2 skipped. Zero GPU-hours; no gate cell executed.

**Next:** delta 37 is the micro-closeout. **If Sol passes it, rung-0 compute begins immediately, on CPU** — Sol has said so explicitly, and the measured runtime makes the GPU unnecessary.

### 2026-08-18 (W4 Tue) · Rung 0 passes · Claude

**Did:** Sol **certified `2efad258`** as the W4 Tuesday gate implementation and evidence contract — subsuming the three uncertified intermediates — and authorised rung-0 execution on CPU at the registered defaults. Confirmed the tree clean at that exact commit, ran it without `allow_dirty`, and **rung 0 PASSES on all three configurations** (D-074). Per Sol's instruction the ladder **stops**: rungs 1 and 2 are not run.

**Verdict:** rho = **−0.9429** for uniform, clustered and sparse alike; intervals [−0.9429, −0.9429], [−0.9429, −0.8286], [−0.9429, −0.9429]. 90 ensembles / **450 fits in 4 m 52 s** on CPU. `recompute()` reproduced the serialised verdict exactly; the suite is green after the run at 548 passing.

**The three rhos are identical because Spearman reads ranks**, and all three mean curves share one rank pattern — falling except a peak at N=250. −0.9429 is one adjacent transposition from perfect reversal, which is that peak costing one of fifteen inversions, exactly as D-069 measured at three seeds.

**The interval, said properly.** Two of three are a single point and that is **not** zero uncertainty: the exact bootstrap is discrete with 2–3 atoms over 3,125 resamples, and uniform and sparse are degenerate only just — second atoms at **1.63%** and **2.14%** against a 2.5% quantile threshold, so sparse is 0.36 pp from its upper bound moving. The verdict is robust to all of it (every atom is far below zero); the reported width is not a precision claim.

**The N=250 peak reproduces in 14 of 15 seed-configuration curves.** The exception, clustered seed 4, peaks at N=500 with N=250 below N=100 — kept and reported, not smoothed. Disagreement is not monotone in dataset size; the gate passes because one inversion is tolerated. This is a reliability result about the estimator, not H1's verdict.

**Two housekeeping fixes.** The verdict was first written *into* the attempt directory, mutating evidence after its manifest; it now sits beside it and the attempt re-verifies unchanged. And the full attempt — manifest, rows, 90 run records, 450 metric streams, 1.2 MB — is now tracked in git, widening the pilot's manifest-only exception, because the contract's trust boundary is those digests and untracked they cannot be checked from a fresh clone.

**A correction:** I told Sol rung 0 would be "minutes", then corrected that to ~50 minutes from the pilot's rate. It was 4 m 52 s — the first estimate was right and the correction was wrong. The pilot is ~10× slower per fit because it also writes per-transition exports, activation reports and figures. I scaled a rate without asking what it was a rate of.

**Next:** delta 38 carries the verdict for review. Then **W4 Fri**, threshold calibration — **C-010 must be finished first**.

### 2026-08-18 (W4 Tue closeout) · The result certified, and three rulings filed · Claude

**Did:** Sol **certified the rung-0 result** and `ca545ed` as the stored Week 4 Tuesday result, now the review base. The gate passes at rung 0 on all three predeclared configurations independently; the ladder is correctly stopped. Three rulings filed as D-075, all adopted, none requiring code.

**Ruling 1 — the intervals stay exactly as registered, and never travel alone.** Widening or replacing them after seeing their discreteness is what preregistration exists to prevent. But `[−0.9429, −0.9429]` must never appear without its explanation, and Sol supplied the wording for the results text — quoted verbatim in D-075 so it survives a reset. The atom/mass table is **necessary for honest interpretation**, not optional colour. The conclusion is unchanged: every atom is strictly negative, so the pass does not depend on which one holds the 97.5th percentile.

**Ruling 2 — clustered seed 4 is not to be investigated.** No integrity failure was found, the paired procedure already includes the seed, and the gate passes with it in. Looking now would be post-result exploration and could invite a model change on one development curve. Recorded descriptively and left to W10's untouched confirmatory seeds.

**Ruling 3 — tracking the 1.2 MB of evidence is correct**, because the verifier depends on the run records and member streams; digests without files leave a fresh checkout able to read every claim and verify none. Keeping `runs/` out of bundle diffs is acceptable given the omission is explicit and the files are in the certified commit. No checkpoints, no per-transition exports for this gate.

**Also accepted:** moving the verdict beside the attempt, and the runtime correction — report 4 m 52 s and state that the W3 pilot is not a comparable per-fit workload.

**Numbers:** unchanged. 548 passing, 2 skipped. Zero GPU-hours. The 450 CPU fits of W4 Tue remain the only compute spent.

**Next:** **W4 Fri**, threshold calibration — **C-010 must be finished first**, since it is the first cell that can violate the D-061 scale rule. W4 Wed and Thu are free because the ladder stopped; per Q-004 that gain goes to review and prose, never to scope.

### 2026-08-18 (W4 Wed) · C-010 and C-009 built, and a reproducibility variable nobody had recorded · Claude

**Did:** built **C-010** (D-076) and **C-009** (D-077), the two remaining obligations that needed no ruling first. Neither required a new scientific decision — D-061 and Sol's 2026-08-16 item already specified both.

**C-010.** `ScaledEvaluation` is the call site D-064 said the rule needed. `from_pool` **takes no mask**, so the scale is built before the object is capable of receiving one; `masked()` reuses that identical object and there is no parameter to override it. One test asserts the invariant is *load-bearing* — the registered masked ratio and a subset-scaled one must differ, because if both choices gave the same answer the rule would be doing no work. `select_attempt()` refuses to guess between attempts: there is no "latest", since a second attempt exists precisely because something was wrong with the first.

**The finding, from probing rather than review.** Proving the runner refactor numerically neutral reproduced N=100 exactly and N=250 **not** — a 0.19% move in mean disagreement. The refactor was not the cause: **thread count** was. The certified run used 8 threads, the comparison 4, and reduction order differs. Re-running at 8 reproduced both cells exactly. **Nothing recorded the thread count**, so the certified attempt was reproducible only by someone who already knew how it had been invoked — a gap in a contract whose whole purpose is that a verdict be checkable by someone who was not there. Now recorded, **additively**: making it required would invalidate the certified `attempt-001`, and that is Sol's call, not mine.

**C-009.** Both of Sol's items were **opt-outs**: `source_unit` was checked only `if not None`, so a dataset that never recorded its origin skipped the one clause catching a borrowed pool; `stream_version` was never compared at all, though D-052 bumped it *because the pools themselves changed*. Adding both refusals broke **no existing test** — nothing in 563 tests exercised either path.

**Numbers:** tests 548 → **565 passing**, 2 skipped. Zero GPU-hours; the reproducibility probe cost 15 CPU fits in a scratch directory. The certified W4 Tue evidence still verifies, and a regression now asserts it will keep doing so.

**Next:** **W4 Friday is blocked on Sol** reviewing C-010 (delta 40) — it is the first cell where a mask exists, so it is the first that can violate D-061. **C-006**, the W5 MDE simulation, remains buildable without a ruling: D-044 specifies it fully. **C-003** (predeclaring the D-031 reserve draw order) is a predeclaration and must reach Sol first.

## Archived from PROJECT_STATE.md §7 on 2026-08-20 — the W4 Thursday MDE and the W5 cells

*Moved when Gate 1 was signed off, which supersedes them. Four entries, 2026-08-18: the MDE simulation (D-078), the acceptance test and its permutation null (D-079, since amended by the D-094 Change Record), the recovered repair path (D-080) and the figure command (D-081). Nothing is condensed.*

### 2026-08-18 (W4 Thu) · C-006 built, and the MDE does not clear five points · Claude

**Did:** built **C-006**, the W5 minimum-detectable-effect simulation (D-078), to D-044's specification — actual group sizes and class membership, group-preserving held-out draws, unit weights, paired predictions, within-group correlation, and the balanced-accuracy **difference** with a group-bootstrap interval. No `n_eff()`: D-044 ruled that naming one invites the misuse that produced the first wrong number, so the analytic boundaries live only in the tests, as validation.

**Both of D-044's validations pass.** ICC = 0 matches the independent-units analytic; ICC = 1 matches the unit-weighted boundary, and a test asserts that boundary is **75.00 / 72.58** recomputed from the live design matrix, so a design change fails loudly instead of leaving stale power claims. The bootstrap interval is separately checked for calibration, and the false-positive rate at zero effect is under 10%.

**Corrected my own misreading:** D-044's "D = 0 / D = 1" are the **classes**, not design effects. Class 0 is 150 units in 125 groups (Σm² = 300 → 75.00); class 1 is 150 in 115 (Σm² = 310 → 72.58). **No group spans both classes**, so a group-preserving partition is automatically class-preserving — which C-005's splitter may rely on.

**⚠ The result: the design does not clear the five-point margin, and not by a little.** At the scheduled held-out counts the MDE at 80% power is **18–22 points**. Sample size is the driver, not correlation: even at **ICC = 0** it is 18 points, so the conclusion does not rest on the parameter least knowable before data. Checked against hand arithmetic — 19.8 analytic against 19.0 simulated at 40 per class; 9.8 against 11.0 at 300 held out.

**Every lever tested, none rescues it.** Pairing is the largest (19.0 → 11.5 at 0.9 → 8.0 at 0.99); baseline accuracy helps slightly; holding out **all 300** units gives 10.5 unpaired and 6.0 paired. Clearing five points conservatively needs **~1,500–2,000 held-out units** against the 60–80 scheduled — roughly a twenty-fold gap.

**Not acted on.** P§14.3's remedy is configuration count — never seeds — but that is a scope and compute decision for the student and Sol, interacting with the 8,197-fit budget and the 120 GPU-hour trigger. Two things need adversarial review before anyone acts: whether the simulated estimand is the one H3's test will use, and whether comparing an MDE against an *equivalence* margin is the right comparison at all. **DEV-008** records that α is not in the plan and that 0.05 two-sided is my stated assumption.

**Numbers:** tests 566 → **581 passing**, 2 skipped. No compute; this reads the design matrix, not run records. This file passed its 500-line cap, so six closed W4-gate entries moved to the archive.

**Next:** **stop.** Sol must answer before W4 Friday (C-010, delta 40) and before anything is decided about the MDE (delta 41). Both are queued.

### 2026-08-18 (W5 Tue/Wed, early) · The acceptance test and its permutation null · Claude

**Did:** built `src/bu/stats/acceptance.py` — the repair acceptance test (P§7.3, S§W5 Tue) and the permutation null calibrating it (S§W5 Wed), both validated on **synthetic data with a known truth**, which is what the schedule's "done when" asks for. No run records, no compute, nothing frozen, and no Sol ruling needed: P§7.3 specifies the test and §2 already carries it (D-079).

**Three conditions, each shown able to refuse alone.** A 35% simulated reduction is accepted and recovered to within 5 points. A **5% reduction over 3,200 transitions — statistically unmissable — is refused**, which is what the 20% practical floor is for. A repair in the wrong direction is refused on direction.

**The permutation moves whole runs, never transitions.** P§7.3 is explicit that permuting across episodes or transitions destroys the dependence structure; the unit is the (seed, arm) block, and a test asserts no run is ever split.

**The measured result, and why the headline number is the wrong one to quote.** False-positive rate **0 of 200** on null data. But counting only the two *statistical* conditions the permuted rate is **5.5% against a nominal 5%** — that is the number establishing the model's interval is correctly sized under the real dependence structure. The 20% floor adds conservatism on top. Quoting 0% alone would credit the model with calibration the floor was supplying: the same shape as D-042's bound-reported-as-a-measurement.

**Replaced a flaky test of my own rather than loosening it.** Asserting the two-condition rate lay strictly above 0 at 60 permutations needs luck (0.95⁶⁰ ≈ 4.6% see zero) and duly failed. It now checks the property directly — the model's SE must match the permutation spread within a factor of two.

**Gate 1 now stands at three of four:** reliability gate **passed** and certified; compute **within budget** (450 CPU fits, zero GPU-hours against a ~120-hour trigger); permutation null **calibrated**; **MDE does not clear five points** — the one needing Sol.

**Numbers:** tests 581 → **597 passing**, 2 skipped. No compute.

**Next:** W5 Mon's three repair functions and W5 Fri's figure script are the remaining unblocked cells. Everything else waits on deltas 39–42.

### 2026-08-18 (W5 Mon, recovered) · A repair path found uncommitted · Claude

**Did:** found `src/bu/experiments/repair.py` and `tests/test_repair.py` **untracked** at session start — a previous session's W5 Monday repair path, never committed (DEV-005 class). Reviewed it to standard rather than trusting it: read both in full, ran all 22 tests, probed it end-to-end on a real four-arm training run (10× data repair → 74.8% reduction, correctly accepted). Touches nothing frozen, writes no records. Committed (D-080).

**Caught my own error.** First claimed pytest had been counting its 22 tests all along; verified false (removing the files drops the suite to 597, restoring gives 619), so deltas 39–42's figures never included them. Corrected D-080 in place — undelivered, unseen by Sol — and added a reconciliation note to the delta file so its frozen "597" prose matches the 619 the bundle now runs.

### 2026-08-18 (W5 Fri) · Every figure from logs, one command · Claude

**Did:** built `make_figures.py` (D-081) — `python -m bu.experiments.make_figures` regenerates every figure from the immutable attempts, no compute. Produces the two W3 curves and a new certified W4 gate trend (three curves peaking at N=250, no error bars per D-075), and **fails loudly** on a missing log. 619 → **626 passing**.

**Where things now stand.** Everything through W5 that needs no Sol ruling is done: Mon (recovered), Tue, Wed, Fri. **Gate 1 at three of four.** The delta prose channel is at its cap (≈377/400) with deltas 39–42 undelivered, so D-080 and D-081 ride the complete diff since `ca545ed` and the ledger rather than new delta blocks. **Genuinely out of unblocked work now** — W4 Fri (freezes a §2 constant), the MDE decision, C-003, C-005/7/8 all wait on Sol.

## Archived from PROJECT_STATE.md §7 on 2026-08-20 — the three W5 closeout sessions

*Moved when the file passed its 500-line cap. Three entries, 2026-08-20: Sol's rulings on deltas 39–42 actioned and the conservatism finding (D-085 … D-090), C-008 and C-003 (D-091, D-092), and C-007 reaching repair acceptance (D-093). All are superseded by the later same-day entries but nothing is condensed.*

### 2026-08-20 (W5 closeout) · Sol's rulings actioned, and a null that was hiding a defect · Claude

**Sol returned PARTIAL ACCEPTANCE on deltas 39–42 and did NOT certify `25fd2c2`.** The certified base remains **`ca545ed`**. Delivery integrity checked both ways first: the delta and bundle SHA-256s Sol quoted match the bytes on disk exactly, so Sol reviewed what was shipped. Every finding was verified before anything changed, and all held — two were **worse** than stated.

**Did, in Sol's required order** (D-085 … D-090):
1. **Froze the calibration criterion before writing the corrected null** (D-085), so its provenance is history rather than a claim. Admissible counts computed in advance: statistical-only **k ∈ [4, 16]** of 200, full rule **k ∈ [0, 3]**.
2. **Paired within-seed permutation** (D-086). The withdrawn global shuffle corrupted **48.4%** of seeds (48.72% analytic) and **every** permutation broke at least one seed — the 0/200 and 5.5% figures were never measurements of the registered design.
3. **One model per repaired arm**, **seed-specific failure masks** (D-087).
4. **Evidence contract v2** — threading required and cross-checked, **v1 grandfathered** so certified `attempt-001` is untouched (D-088).
5. **Sol's rulings filed**, Gate 1's standing recorded (D-089).
6. **W4 Friday threshold runner built and NOT executed** (D-090), returned for the pre-execution review Sol asked for.

**THE FINDING — two errors were cancelling.** The corrected null exposed that the registered P§7.3 model has **no transition-level pairing term** while the comparison is paired transition-by-transition, so its SE is **1.51×** the true paired null spread and the test is **conservative**. The broken permutation had been hiding this exactly: breaking the pairing inflated the null's spread by **1.46×**, cancelling the over-wide SE to a reassuring ratio of **1.03** that passed its bound comfortably. Statistical-only rate **0/200, CI [0.000%, 1.828%]** — D-085 requires it to contain 5%. **Not fixed:** the acceptance model is a §2 frozen constant, so it is a Change Record and Sol's ruling. Marked `xfail(strict=True)` so the failure stays visible, with the 1.51× pinned by a test. Measured on synthetic data whose generator pairs the arms almost perfectly — the **direction** is established, the **magnitude on real data** is not.

**Also found:** the runner **recorded** interop threads but never **pinned** them (D-088); and repaired arms at the default K=5 would cost **8,360 fits against 1,672 budgeted**, taking the design to **14,885 vs ~8,700 — 1.71× budget**, which is the Gate 1 compute condition Sol had just marked PASS (D-087).

**A provenance note.** `config.py`, `gate.py` and `tests/test_audit_regressions.py` were found **modified mid-session** — after this session's last edit and last green run — implementing Sol's items 4 and 6. **I did not author them** and `list_sessions` showed no other session. They left the suite **red at 24 failures** (v2 required a `threading` field nothing emitted). I verified them by test rather than by reading, completed the production emitter, the interop pinning and the whole v2 refusal suite, and the tree is green again. Recorded because unattributed edits in a working tree are the DEV-005 class of hazard.

**Tests:** 627 → **672 passing**, 2 skipped, **1 xfailed** (D-085's unmet criterion, deliberately visible). **Compute: zero.** No fit spent, no attempt re-run, no data seen.

**Next:** deliver delta 43 with one clean bundle against `ca545ed`. Two questions must reach Sol — the acceptance model's conservatism, and W4 Friday's percentile and reference-model definition. **W4 Friday still must not execute.**

### 2026-08-20 (W5 closeout, continued) · C-008 and C-003, the last unblocked work · Claude

**Cleared the two open items that needed no ruling**, so that everything now waiting is genuinely waiting on Sol.

**C-008 — the confirmatory runner** (D-091). Sol raised this at `2875e60`'s certification and named it again in the delta-42 ruling as a precondition for any repair-validation evidence. The bypass `train_ensemble` used to **confess in its own docstring** — `bootstrap_episodes()` + `train(train_index=…)` — is closed at the **resampling site**, with `seed` now a *required* argument there: a caller cannot resample without declaring whose seed it is. That candid docstring is why the hole was findable at all. The change immediately caught real misuse: `tests/test_ensemble.py` had been exercising transition and initialisation-only bootstraps on **seed 1000, a confirmatory seed**, and nothing had objected. The runner has **no `granularity` parameter at all** — a parameter accepting one value invites a caller to pass another. A test caught `metric_schema_version` missing from the emitted record, which would have left a confirmatory run unverifiable by the evidence contract.

**C-003 — the reserve draw order** (D-092), committed as `reserve_order.json`: **231 units, 120 of intended class 0 and 111 of class 1.** The obvious derivation was wrong and would have been silently wrong: `select_sweep(k)` is a strict **superset** of `select_sweep(k−1)` but is **not prefix-stable**, so reading a draw order off list position produces a plausible, deterministic, incorrect commitment. The order comes from the **set difference at each step**, which is stable; admitted units alternate intended class, giving a balanced per-class order. `next_reserve_units(intended_class, n)` takes a class and a count **and nothing else**, so D-031's "without inspecting critic performance" is a property of the signature rather than a rule to remember, and over-drawing is refused because extending a reserve after seeing a shortfall is choosing rather than drawing.

**Tests:** 672 → **705 passing**, 2 skipped, 1 xfailed. **Compute: zero** beyond one tiny synthetic fit in a temp directory — no registered run, no logged result, no data seen.

**There is now no unblocked work left.** W4 Friday, the Gate 1 verdict, repair validation and anything built on the reserve order all wait on Sol.

### 2026-08-20 (W5 closeout, C-007) · The seed policy reaches repair acceptance · Claude

**C-007's widest remaining hole closed** (D-093). Repair acceptance had **no** confirmatory guard, so the repair path could produce registered repair-validation evidence on development seeds — and repair acceptance is where every label in the thesis is created. Guarded at **both** layers: `evaluate_arm` before the fit, and `acceptance_inputs` where the label actually comes into existence, since evaluations can be constructed without the producer. Tied to the **stage**, not a boolean: a probe must label itself `pilot` rather than exempt itself, because D-077 already had to close two opt-outs that existed for exactly that reason.

**Provenance correction.** The student reports that **an earlier session was interrupted**, which is the likely source of the three files found modified mid-session and recorded as unexplained in the previous entry and in delta 43. Recorded as *reported*, not verified — `list_sessions` returns nothing even including archived sessions. The classification is unchanged and sharpened: an interrupted session leaving uncommitted work is exactly the DEV-005 / D-080 pattern.

**Tests:** 705 → **709 passing**, 2 skipped, 1 xfailed. **Compute: zero.** Still no unblocked work left.

## Archived from PROJECT_STATE.md §7 on 2026-08-20 — the Sol correction rounds

*Moved when the file passed its cap after W4 Friday executed. Four entries, 2026-08-20: Sol's deltas 43–44 actioned with Gate 1 signed FAIL (D-094 … D-099), the delta-45 corrections (D-100), the delta-46 closeout (D-101) and the delta-47 non-finite guard (D-102). All are superseded by the calibration entry that follows them; nothing is condensed.*

### 2026-08-20 (W5 Sat) · Sol's whole ruling actioned; Gate 1 signed off FAIL · Claude

**All seven of Sol's closeout items done, plus the audit** (D-094 … D-099). Every finding verified before actioning; Sol's own corrected D-085 target checked independently and confirmed.

**Two Change Records, both before any data was seen.** **D-094** — the acceptance model gains the pairing. **The literal specification turned out to be degenerate**: a seed intercept, an episode component and a transition-within-episode component are all constant within a pair, so all three cancel in the contrast and become unidentifiable — `LinAlgError: Singular matrix` at 250 and 1,000 pairs, and 231 s where it fits, which would make 200 permutations a 13-hour run. Reduced to what *is* estimable it treats pairs as **iid**, blind to seed-level effect variation, with SE up to **8.7× too small**. That would have swapped a 1.51× conservative test for an anti-conservative one — the worse direction, since a narrow interval manufactures repairs out of seed noise and those become labels. Implemented instead: pair first, seed stays the replication level, t on n−1 df — **7 ms against 231 s**, and calibrated at every pairing strength (5–7/200 against an admissible [1, 10]). **D-097** — a distinct `threshold_calibration` stage, because `TrainConfig` is not in `run_id` and reusing `exp1` would have collided identities.

**Gate 1 signed off: FAIL** (D-098). Condition 3 was repaired this session and condition 4 still fails; Sol was explicit it must not later be renamed a pass. **Not** the condition-1 pivot — H1's machinery works; what failed is power. The 300-unit design continues under a recorded limitation, Direction C authorised.

**The W4 Friday runner is rebuilt and NOT executed** (D-097), which is what Sol asked to see. `calibrate()` now takes no argument that can change the number.

**Audit found two methodological limits of the balancing rule** (D-099), both raised rather than assumed away: it caps row count but **not tail influence** at the 95th percentile, where one stratum of nine is 11.1% of the pool; and its RNG is inert when strata are equal-sized, though real movement counts vary (815–853) so seed 0 does bind and ~4% of reference data is discarded to the smallest stratum.

**Tests:** 745 → **760 passing**, 2 skipped, **0 xfailed**. **Compute:** real fits only in temp directories on the cheapest registered obligation; **no registered evidence, no threshold calibrated, no data seen.**

### 2026-08-20 (W5 Sat, correction pass) · Sol's delta-45 corrections · Claude

**Sol accepted the paired seed-cluster analysis in principle and Gate 1's FAIL**, then listed narrow corrections. All done (D-100); no new experimental data was needed.

**A claim of mine narrowed.** D-094 said the three variance components "become unidentifiable". Sol is right that this overstates it — shared intercepts cancelling from the paired contrast does not prove mathematical unidentifiability in long-form data. What was established, and all that is claimed now: that specification was **singular in practice**, **computationally unacceptable** where it fit, and **failed to represent repair-effect heterogeneity**. Enough to justify the analysis without the stronger claim.

**The estimand made self-consistent**: the effect equally weights seed means, but the denominator was weighting raw transitions — the D-042/D-044 shape. Both sides now use `mean_s(mean_i baseline[s,i])`, with a test whose fixture gives seeds unequal counts so the two weightings genuinely differ.

**Exactly the frozen 20-seed set** is now required where the label is created; nineteen seeds or an after-the-fact subset is a different experiment. **No fallback** in registered acceptance — it fails closed rather than switching replication from seeds to episodes on the strength of the data. **Result language corrected** throughout.

**C-008's last two exposures closed**: `allow_dirty` and caller-chosen thread counts are gone, threading frozen at 4/4 inside the runner. **Threshold**: attempt names frozen to `attempt-NNN` so no permitted name escapes prior-attempt discovery; `INVALID` must state a reason; and `recompute_threshold` no longer reads the frozen spec out of the file it is checking — it compares every constant against the code, verifies run and member digests, and **reconstructs** the deterministic selection rather than reusing the recorded one.

**Rerun as required:** all four pairing-strength calibrations still calibrated. **Tests:** 760 → **786 passing**, 2 skipped, **0 xfailed**. **W4 Friday remains stopped.**

### 2026-08-20 (W5 Sat, closeout patch) · A hole in my own guard · Claude

**Sol's delta-46 closeout, all five items** (D-101). One was material and it was **my** defect, in the guard I had written two passes earlier to close exactly this class of thing.

`_validate_registered_consumption` treated every non-`pilot` stage as registered and derived the required seeds from that stage's own count. Reproduced before fixing: a five-seed **`exp1`** set and a five-seed **`threshold_calibration`** set each **created a repair label, 400 rows**. Both carry a registered stage and the right confirmatory seeds *for that stage*, so every other clause passed — while the repair protocol had never been run. I had generalised "registered" where the rule needed to name **one** stage. Label creation now requires `repair_validation` **and** the frozen 20 seeds; every other stage is refused by name.

Also: `allow_fallback` removed entirely (it survived the fallback it was named after, defaulting to True and ignored); the wording cleanup finished, with the one surviving description of the old model marked as superseded history; `recompute_threshold` extended to nine further record-integrity fields including each cell's transition count against its array length; and the stale balancing question removed from the delta, which had been saying the issue was settled and asking Sol to settle it.

**Tests:** 786 → **801 passing**, 2 skipped, 0 xfailed. **Gate 1 FAIL, the seed-cluster analysis and the balancing rule are settled and not revisited. W4 Friday remains stopped.**

### 2026-08-20 (W5 Sat, micro-closeout) · A seed could vanish and the result still said twenty · Claude

**Sol's delta-47 guard** (D-102), reproduced before fixing. `_frame` accepted non-finite errors and pandas drops them while pivoting and grouping — so a registered input could clear the 20-seed guard and then lose transitions, or a whole seed, inside the transformation. Measured: one seed of NaN moved the effect (−0.035383 against a clean −0.035657) and the interval, while `n_seeds` **still reported 20**; 37 scattered NaNs left `n_transitions` reporting 3,200. Worse than Sol stated: **+inf and −inf were both absorbed to the same finite answer**, so an upstream sign error would have been invisible.

Guarded at three layers — `_frame` refuses non-finite input outright, `paired_differences` uses `pivot` rather than `pivot_table` and asserts the row count against the validated pair count, and the seed means are checked to match the input seed set exactly. Ten tests. Also fixed a doubled word of my own that spanned a line break.

**Tests:** 801 → **811 passing**, 2 skipped, 0 xfailed. **W4 Friday remains stopped.**

### 2026-08-20 (W4 Fri) · THE THRESHOLD IS CALIBRATED · Claude

**Sol authorised one run from the accepted base. It ran once, into `attempt-001`, and will not be rerun** (D-103).

**`0.610702633857727`** — 95th percentile, `method="linear"`, failure is **strictly greater**. **NOT FROZEN**: `constants.py` is untouched and promotion is a separate D-035 Change Record after Sol reviews the evidence.

**Preconditions checked before executing**, because there is exactly one attempt: `HEAD` bit-identical to Sol's accepted `93dc296`, tree clean, branch in sync, frozen spec verified field by field. One cell was first run in a temp directory to validate the newly registered `threshold_calibration` stage — **wall time read, errors never**, since inspecting the distribution beforehand would have been pre-inspecting the threshold.

45 cells, 225 fits at n=5,000, **4.3 min**. All 45 unique, all K=5, balanced pool 9 × 4,103 = 36,927. **Recomputation from the stored artefacts alone is bit-identical.**

**A correction to my own D-099 audit:** I estimated ~4% of reference data discarded to the smallest stratum, from six probed cells. Actual is **1.28%** — pooling five seeds per stratum evens the counts out, which six single cells could not show.

**And a near-miss worth recording.** The evidence was **silently untracked**: `runs/*` is ignored with per-experiment exceptions and `runs/w4_threshold` had none, so the first version of the commit shipped **two** files while its own message claimed 136. Caught by checking the commit rather than trusting it. Had it gone out, the bundle would have carried digests with no files — the D-041 shape exactly, and `.gitignore`'s own comment warns about this class while nothing enforces it.

**Tests:** 811 passing, 2 skipped. **Compute:** 225 CPU fits (675 total), 0 GPU-hours. **First registered evidence the project has produced.**

### 2026-08-20 (W4 Fri, follow-on) · The near-miss mechanised, and the H1 statistic audited · Claude

**Work taken while delta 49 is with Sol.** Q-004 governs the lead — review, understanding and documentation, **never scope** — so C-005 and Week 6 are untouched.

**D-103's near-miss is now a test** (D-104). The property is narrow on purpose: not "everything under `runs/` is tracked" — D-075 deliberately tracks only the W3 pilot's manifest and rows — but *every file whose digest a tracked record attests, and which a verifier reads back, must itself be tracked*. **Shown to fail**: `git rm --cached` on one error array made it fail by name; restoring made it pass.

**`stats/trend.py` audited by probing — clean.** It is THE H1 statistic, shared by the certified W4 gate and the future W10 verdict, so a defect moves a registered endpoint. Ties agree with `scipy` exactly; the exact bootstrap is genuinely exhaustive (27 at 3 seeds, 3,125 at 5); the reading rule is right in all three directions; non-finite curves refused and degenerate ones fail closed.

**An asymmetry worth carrying:** `trend.py` already had the non-finite guard `acceptance.py` lacked until D-102. Two modules by the same hand, one guarded and one not — so a guard's presence in one place is no evidence about another.

**Tests:** 811 → **819 passing**, 2 skipped, 0 xfailed.

### 2026-08-20 (session close) · The audit gap closed · Claude

**Audited the modules that had never been probed** (D-105). `stats/gate.py` was the real gap: **review-covered but probe-uncovered**, four Sol reviews deep, which is precisely why nobody had looked — D-060's lesson is that nine reviews passed over Week 3 before an audit found seven defects.

All clean. The **certified W4 Tuesday evidence still verifies today** after everything this session changed (90 cells, passes) — the regression that mattered most, now checked rather than assumed. Rung binding is enforced through `attempt_id`, not an editable field; rungs 3–5 refused as unfrozen; the 3×5×6 grid exact. `runrecord.py` refuses overwrite and records git state plus `env.packages`. `critic/schema.py` is genuinely fail-closed — an **unknown** feature name is refused, which is what D-013 chose a whitelist for. `reserve.py`'s frozen digest really does gate the drawer.

**`w3_pilot.py` deliberately not probed**: its data was voided by D-051/D-052, nothing downstream reads it. Recorded rather than left ambiguous.

**Three of my own probes were wrong** — a bad argument type, a string passed where a list was wanted (so a whitelist appeared to refuse everything), and a parameter that does not exist. Each looked like a defect for a moment. A wrong probe produces the same shape of output as a real finding, which is why all three were chased down before being written up.

**Tests:** 819 passing, 2 skipped, 0 xfailed. **No code changed — this entry is measurement.**

### 2026-08-22 (delta-49 review) · Sol withheld D-035 — the bundle carried digests, not bytes · Claude

**Sol did not reject the run.** It found the reported execution consistent with the authorised specification on every field — `93dc296`, one attempt, 45 unique cells, nine strata × five seeds, K=5, 4/4 threading, 36,927 balanced transitions, the threshold itself, constants untouched, no rerun — and accepted the D-099 → **1.28%** correction, the tracking test and the audits. **Promotion was withheld for one reason: the artefact contents were never delivered** (D-106).

**Verified before acting, and it is worse than Sol stated.** `SOL_BUNDLE.txt:214` declares `DIFF EXCLUDES: runs/`. So the bundle listed all 136 artefacts with **12-hex truncated digests and no bytes**. Sol could not parse the grid, check a digest, reconstruct the selection, or recompute anything.

**The D-041 shape through a third route.** Delta 12 shipped digests-without-files via *file selection*; D-103's near-miss via *`.gitignore`*; this via the *diff exclusion in the delivery*. **The delta that reported catching the near-miss reproduced it one layer over.** D-104's test passes and is simply about a different property. **Tracking evidence and delivering it are two obligations, and the first is no evidence about the second** — the same asymmetry D-104 itself recorded about guards in `trend.py` and `acceptance.py`.

**A number reported with no definition.** `digest-of-array-digests` was given to Sol as `01b390cb8aef41ca…`. **No code computed it and no file defined it.** Asked for the untruncated value, I could not look it up — it was reconstructed by searching candidate definitions, and is now pinned in the script: sha256 over the concatenated **raw 32-byte** array digests ordered by `errors_file`. **A digest without its definition is not a digest** (D-042/D-044, in a new place).

**Delivered as an archive, because the arrays are binary NumPy** and a pasteable bundle cannot carry them. `scripts/sol_evidence_archive.sh` builds from the **commit object, never the working tree**, so "exactly as tracked at `84cfdb9`" is structural. **Verified on the deliverable:** it extracts its own output and recomputes the threshold **from the extracted bytes alone** — `0.610702633857727`, bit-identical — because the repository being correct does not imply that what was sent is sufficient. Determinism was **proved by rebuilding**, and the empty-subtree guard **proved by firing**, rather than asserted.

`archive 4a2dd555…dade1b` · `json 310a4483…651e86dc` · `arrays 01b390cb…f5624002` · 214,062 bytes · 136/136 files.

**Also corrected: stale text in the two files a reset Claude reads first.** §1 still said "Next actions — Week 3", still listed W4 Friday as "NEXT, and blocked on Sol" two sessions after it ran, and still named the Gate 1 verdict as waiting. `CLAUDE.md` still opened its "Next, in order" with deltas 39–42, all answered on 2026-08-20. None of this is caught mechanically — the protocol suite checks §1's *structure*, never whether its prose is true.

**Tests:** 819 passing, 2 skipped, 0 xfailed. **No rerun, no new compute** — 675 CPU fits total, 0 GPU-hours.

### 2026-08-22 (D-035 promotion) · The failure threshold is permanently frozen · Claude

**Sol authorised the promotion** after verifying the delivered archive itself rather than accepting the report: paths confined to the attempt, no symlinks, exactly 136 files, **all 45 array digests, all 45 run-record digests and all 45 member-record digests**, every run record's commit / stage / family / confound / observability / n / layout / attribute / K / threading, the deterministic selection reconstructed at RNG seed 0, and a **binary-identical** NumPy recomputation. Its independently computed array-composite matches D-106's reconstructed definition.

**`FAILURE_THRESHOLD = 0.610702633857727` is now in `constants.py`**, exact and unrounded, **permanently frozen** (D-107). The most irreversible act in the project so far.

**The strict boundary decides real labels — measured, not assumed. Two transitions in the calibration pool sit exactly at the value.** Under `>` they are not failures; under `>=` they would be.

**`ScaledEvaluation.failure_mask()` takes no threshold.** Sol required no caller-selectable override, and the reasoning is C-010's exactly (D-076): `from_pool` takes no mask so the scale cannot be subset-derived; this takes no threshold so the failure set cannot be re-cut. It scores the **ensemble mean prediction** — what the calibration measured — not the mean of member errors.

**Verified against the evidence:** the constant recovers the stored balanced pool's 95th percentile exactly; 1,846/36,927 = **4.9991%** failures; Sol's unbalanced check **1,879/37,406** reproduces.

**The tests were proved falsifiable by mutation**, each catching exactly one defect: rounding the constant, relaxing `>` to `>=`, and adding a `threshold=` override. **Two weak checks of my own were caught this way and fixed before they shipped.** The first boundary test asserted `errors > t` on a tensor the test built — Python's operator, not the implementation — and now runs through the real constructor on a fixture whose error is *exactly* the threshold, with an assertion that it stays exact so it cannot go vacuous. Then the new §2/code agreement check searched the **whole file**, where the value appears five times, so §2 could read `0.6107` and still pass; it is now scoped to §2 alone and shown to fail.

**A process failure worth recording.** Proving falsifiability the first time, I restored mutated files with `git checkout` while the promotion patch was still **uncommitted**, and destroyed it. Retyped in full; nothing lost. **`git checkout` restores to the last commit, not to the state you were in** — mutate against committed work or a copy.

**Scope held.** Narrow patch only. **No failure set, no repair label, nothing downstream** — Sol requires certification of this closeout first. Gate 1's signed FAIL stands.

**Tests:** 819 → **830 passing**, 2 skipped, 0 xfailed. **No rerun, no new compute** — 675 CPU fits, 0 GPU-hours.

### 2026-08-22 (post-promotion probe) · One threshold, nine prevalences · Claude

**Work taken while the D-107 closeout is with Sol**, under Q-004: review and understanding, **never scope**. No code changed, nothing downstream built.

**The question nobody had asked.** D-035 justifies one global threshold on the grounds that balancing makes it defensible *"once D-032 has fixed the error to one scale"* — but D-061 fixes the scale to each **evaluation pool**, and every unit has its own. The two rules had never been checked against each other.

**Measured with no training** (`targets()` is a pure slice, so the scale is a std over the environment): the scale spans **33–36%** across the nine calibration strata, **ordered systematically by layout** — clustered 0.2018 < uniform 0.2226 < sparse 0.2475. A smaller scale inflates the normalised error, so failure prevalence is ordered inversely: **1.58% sparse, 4.68% uniform, 8.77% clustered — a 5.53× spread** behind the pooled 5%.

**Mostly the normalisation, not difficulty.** The raw error is **bounded, not approximated**: clustered and uniform raw-error intervals **overlap** ([0.05737, 0.06032] against [0.05704, 0.05929]) while their failure rates differ **1.87×**. Across all three layouts raw error spans **1.09×** and prevalence spans **5.53×**.

**Why it matters:** the failure set is what H2 is defined over and what H3's critic must predict. Layout — a registered design factor — enters the label through the scale. That is the leakage D-035 excludes, arriving through a different door.

**A correction I owe Sol.** Delta 49 said the unbalanced/balanced agreement (5.02% vs 5%) meant *"the strata are not wildly heterogeneous in the upper tail."* **Invalid** — balancing discards only 1.28% of rows, so the two pools are nearly identical and a pooled rate cannot speak to per-stratum dispersion. They are heterogeneous, 5.53×.

**Caught in my own probe first:** the initial version used `mean(scale)` and called the two dimensions equal to ~1%; they differ by up to ~5%. Replaced with the exact interval before the number left the machine — D-042's lesson applied in time rather than after.

**Not actionable by me.** The threshold is frozen and must not be recalibrated, so this cannot be fixed by changing it. The remedy is Sol's ruling, and it belongs **before** any failure set or repair label exists — which is exactly where the project sits.

**Tests:** 830 passing, 2 skipped, 0 xfailed. **No new fits** — 675 CPU fits total, 0 GPU-hours.

### 2026-08-22 (delta-51 ruling) · Certified, and a claim withdrawn · Claude

**D-107 is CERTIFIED.** Sol confirmed the exact float and hex, strict `>`, equality as non-failure, ensemble-mean scoring, no caller-selectable threshold, the scale built before any mask. **The threshold is final — never recalibrate, round, per-layout, or override it.**

**D-108's numbers are accepted; its interpretation is withdrawn** (D-109). Sol's correction, verified before applying: **the probe bounds the layout-averaged cell-mean raw-error norm, and prevalence is an upper-tail probability.** Overlapping bounds on *means* cannot say why *tails* differ. Four claims withdrawn — "does not mean one thing", "mostly the normalisation", "the label is mostly the per-pool scale", and the P§7.5 leakage framing. **The last was wrong on the code**: `layout` is already in `FORBIDDEN_FIELDS`, so it cannot reach critic X.

**What stands, in the wording that now travels with it:** *under the frozen per-evaluation-pool normalisation, failure prevalence differs materially by layout in the calibration evidence — layout-conditioned base-rate heterogeneity and a measurement-invariance limitation. The aggregate mean-error bounds do not identify how much of the tail difference is normalisation versus the error distributions.*

**Verifying Sol's arithmetic found an estimand error of mine.** Sol's figures reproduce from neither pooled rows nor the balanced selection — they reproduce to **3×10⁻¹¹** from the **unweighted mean of the 15 per-cell rates**. D-108's table had mixed both aggregations without naming either. **D-044, exactly.** Both are now reported and labelled; the ratios barely move (1.8735 pooled-row vs **1.872846** cell-mean).

**And the collapsed scale column was hiding the truth.** D-108 printed one scalar per layout (0.2018 / 0.2226 / 0.2475), which looked cleanly separated. As honest **per-dimension ranges**, clustered [0.19210, 0.21764] and uniform [0.20808, 0.23779] **overlap**. Sol also caught that the committed probe never printed that column at all — a published number not reproducible from the artefact offered to reproduce it.

**Sol registered a six-point layout analysis rule** (§2 and D-109): endpoints unchanged; prevalence reported by layout, causal attribute and seed; layout-stratified H2/H3 as **secondary robustness only**; layout stays experimenter-only metadata; leave-one-layout-out may be preregistered as a secondary stress test.

**Corrections applied:** probe rewritten to claim only what it supports and to reproduce every column it prints; the `test_the_unbalanced_sanity_check_still_reproduces` docstring corrected, since it still carried the invalid homogeneity inference.

**Tests:** 830 passing, 2 skipped, 0 xfailed. **No new fits, no threshold change** — 675 CPU fits, 0 GPU-hours.

### 2026-08-22 (methodology prose) · The mandated sections, and a wrong word in the deviation log · Claude

**Q-004 work while delta 52 is with Sol** — documentation and prose, never scope. No code behaviour changed, nothing downstream built, no new fits.

**§4 requires five things in the methodology and one had no prose at all: the reliability-gate rung reached.** DEV-006 and DEV-007, both marked *goes in methodology: yes*, had none either. Six sections drafted into `docs/method_draft.md`: the primary error metric, position-causal conditions, the rung-0 gate result, the frozen threshold, the layout-prevalence limitation, and what the design can and cannot detect.

**The atom/mass table was recomputed from the certified evidence rather than retyped** — D-075 requires it to travel with any W4 result, so a transcription slip would reach the thesis. All 3,125 resamples per configuration, enumerated from `runs/w4_gate/`, reproduce D-074 exactly. Sol's discreteness sentence sits verbatim beside it.

**A wrong word in the deviation log, caught before it became a thesis claim.** DEV-007 calls the primary error **"grid-normalised"**. It is not: `per_dimension_scale` returns the per-dimension **standard deviation** of the evaluation pool's targets (D-061). That would have misdescribed the units every reported number is in — and the distinction is exactly the one D-061 exists for, since the scale is a **vector** and does not cancel in the H2 ratio. DEV-007 is not edited (§4 is append-only); D-110 is the correction of record.

**And a claim of mine narrowed before it shipped.** I wrote that the five NumPy quantile methods "differ by up to a factor of two on short vectors" — generalising from D-099's single probe vector (1.8× there, but only 9.00–10.00 on a smooth ten-point vector). Both are now given, and the point is stated as version-independence rather than gap size. **The same failure mode as D-108, caught one step earlier.**

**Tests:** 830 passing, 2 skipped, 0 xfailed. **No new fits** — 675 CPU fits, 0 GPU-hours.

### 2026-08-22 (delta-52 ruling) · Three narrowings, and the blocker closed · Claude

**D-109 CERTIFIED. The D-108 blocker is DISCHARGED** — failure-set construction is no longer blocked by it, *subject to the project's other gates*, which Sol was explicit still stand: **repair validation** and **reserve consumption**. Sol reconfirmed both prevalence estimands to six figures and accepted the cell-mean/pooled-row distinction as correctly identified and labelled. The threshold is unchanged and permanently final.

**Three prose corrections to D-110, all verified before applying, all correct** (D-111).

1. **Layout and threshold selection.** I wrote layout *"plays no part in threshold selection."* **Literally false**, and one grep away: `reference_strata()`'s docstring says the pool balances over *"(layout, causal_attribute) strata."* Layout **is** a preregistered balancing stratum. I was reaching for a claim about future discretion and wrote one that denied a fact about the past.
2. **The MDE simulation.** My section called it *"a simulation of the actual H3 estimator … with a group-bootstrap interval"* and then said, four sentences later, that it uses a Wald rule *where the registered analysis uses a group-bootstrap percentile*. **Both cannot be true.** A self-contradiction inside one section is worse than either half alone, because the reader resolves it in whichever direction flatters the result.
3. **"Sample size drives this, not correlation"** — contradicted by its own next sentence, which reports pairing at 0.99 reaching eight points. Now: sample size is the **principal** limitation **across the tested dependence assumptions**. The 1,500–2,000 figure is labelled a **rough diagnostic extrapolation**, not a computed requirement.

**All three are the same move: a defensible claim stated one degree stronger than the evidence carries** — as with D-108's causal attribution and D-110's quantile generalisation. Every correction is a *narrowing*, never a retraction, which is exactly why it is easy to miss while writing.

**The append-only convention is ratified.** Sol: keep D-108 as historical evidence of what was claimed, D-109 as the correction of record, do not rewrite history, and keep current summaries pointing at D-109. Settled, and it applies to DEV-007 → D-110 too.

**The certified base is now `f6bcd63`** (§1, `CLAUDE.md`). **`13bf5f5` must never be used** — it carried the rejected D-108 interpretation and was never certified as a whole. D-043 in the concrete.

**Tests:** 830 passing, 2 skipped, 0 xfailed. **Prose only** — no source, no fits, no threshold work.

### 2026-08-22 (methodology closeout) · The last mandated section · Claude

**§4's mandated methodology list is now discharged as far as events allow** (D-112). The Week 2 decision on whether the Experiment 2A conditions are drawn from the sweep or additional to it (D-007) was the only one of the five with no prose. The reliability-gate rung, the PPO substitution and DEV-006/DEV-007 are covered; the remaining two — a repair-budget or configuration-count reduction, and a cut experiment — **have not happened**, so there is nothing to write yet.

**The arithmetic was checked in code, not quoted from the ledger.** `canonical_units()` = **75**, of which `experiment_2a_units()` = **20**; `sweep_candidates()` is the full matrix **minus** the canonical ids, so the 225 sweep draws cannot collide; `design_units()` = **300**, with **300 distinct** ids and the canonical set a subset. Double-counting would give **375** against a registered 300 — the concrete size of the inflation D-007 prevents, and every interval on that count would be too narrow.

**Tests:** 830 passing, 2 skipped, 0 xfailed. **Prose only** — no source, no fits.

### 2026-08-22 (schedule check) · Weeks 4 and 5 are not complete · Claude

**§1 has claimed "Weeks 1–5 are complete" for many sessions. Checked against the schedule document rather than the ledger, it is wrong** (D-113).

**W4 Friday is half done, and the missing half is a Gate 1 condition.** The cell specifies the threshold calibration **and** a *"timing harness: measure one full condition end to end and extrapolate total GPU-hours against the ~120-hour estimate."* **No harness exists.** Gate 1's condition 2 was signed **PASS** on *"14,885 fits against ~8,700, i.e. 1.71×"* — **a fit count, not GPU-hours**, and the conversion is exactly what the harness would have measured. **Zero GPU-hours have ever been spent.** The schedule is explicit that this is *"a gate, not a formality — the design sits at the edge of the budget with no meaningful headroom"* (110–145 GPU-h against a ~120 trigger). A CUDA device is present; the measurement was simply never taken.

**W5 Friday is half done.** The figure script exists (D-081); the *"class-balance procedure in code at the labelled-unit level … plus a fixed cap of traces per selected unit"* does not. The only `balance` in `src/bu` is `_balanced_accuracy`, which is the metric. D-031/D-092 cover **intended**-class balance and the reserve order — related, but not balance at the **labelled**-unit level within each split. **S§W11 Mon assumes this procedure exists.**

**A deviation that was never written**, now **DEV-009**: S§W5 Tue specifies a statsmodels **MixedLM** with an episode-mean fallback; the implemented test is an equal-seed paired difference with a t interval and no fallback (D-094/D-100). Sol-authorised before data, and in §2 and the ledger — but absent from §4, and "mixed-effects" appeared **zero times** in this file.

**Why it stayed invisible:** each gap sits beside something done well and reported at length. The threshold is the most-reviewed artefact in the project and shares a cell with the harness nobody built; the acceptance change survived four Sol rounds and two Change Records without anyone asking where its deviation record was. **The ledger tracks decisions, not cells.** Nothing checks schedule coverage, and §1's summary was true of the *intent* and never re-checked.

**Written: DEV-009**, a recording obligation and mine. **Not done: the timing harness** — it re-opens a signed gate condition and would be the first GPU compute — **and the class-balance procedure**, which is inside Sol's gated reserve-consumption area. Both go to Sol.

**Tests:** 830 passing, 2 skipped, 0 xfailed. **No new fits.**

### 2026-08-22 (W4 Fri, part two) · The timing harness, eight sessions late · Claude

**Built and ran the missing half of W4 Friday** (D-114). Wall time only, `stage="pilot"`, nothing registered written — the discipline D-103 used and Sol accepted.

| configuration | extrapolated training time | vs the 120-hour trigger |
|---|---|---|
| CPU, **4 threads** (the certified config) | **6.40 h** | 0.053× — **19× headroom** |
| CPU, 24 threads | 8.72 h | 14× |
| CUDA (RTX 4080 SUPER) | 7.92 h | 15× |

**Fewer threads is faster and the GPU barely helps** — the model is a small MLP, so synchronisation and launch overhead dominate. **The design is effectively CPU-bound and the GPU is not the resource the budget is denominated in.**

**Gate 1's condition 2 was signed on a fit count; the condition names GPU-hours.** Measured, the design is inside budget **by 14–19×**, and the direction holds across every configuration. The schedule's premise — *"sits at the edge of the budget with no meaningful headroom"* — was written about the plan's specification and **is not true of the implemented system** (scripted policy, small MLP, gridworld).

**A consequence that is Sol's to rule on.** Sol refused expansion toward the 1,500–2,000 units the five-point MDE needs as *"incompatible with the registered scope **and budget**"*. **The budget half is now measurably not binding** — a 5–6× design extrapolates to ~32–52 h, still under 120. **This does not make expansion advisable**: scope, the twenty-week calendar, ~14 h/week and data-generation cost are all untouched, and Gate 1's FAIL stands regardless. It removes one of two stated grounds.

**The accounting was wrong first, and it was D-033's error.** Summing `obligations()` gave **6,750** baseline fits against **6,375** — **exactly the 375 phantom fits** — while also charging one fit per repair *obligation* instead of per seed. Rebuilt on `execution_plan`, it reproduces 8,047 exactly. A second implementation of a number the project has already been wrong about is not a shortcut, it is the bug. Pinned by a test shown to fail.

**Tests:** 830 → **835 passing**, 2 skipped. **No registered fits**; timing runs only.

### 2026-08-22 (W4 closeout) · Week 4 is complete, and a departure nobody logged · Claude

**Week 4 verified cell by cell against the schedule's *Done when* column** — the column I truncated when first reading it, and where W4 Friday's second task was hiding. Mon ✓, Tue ✓ (verdict **and rung**, rung 0, certified), Wed and Thu correctly **not run** (conditional on a failure that did not happen), **Fri ✓** (threshold frozen *and* measured estimate compared against the trigger, D-107 + D-114), Sat ✓ (875 words). The Week 4 focus note's *"record the rung even when the gate passes immediately"* is satisfied in the ledger, §2, §5 and the prose. **W5 remains open on one cell**: Friday's class-balance procedure.

**Checking W4 turned up a W5 departure that was never logged.** S§W5's focus note says of our exact situation: *"If the MDE does not clear five percentage points, **raise the configuration count now**. It costs Kaggle time, not your time."* The MDE does not clear five points; the count was not raised; **and that appears nowhere in §4** — the deviation log the methodology draws from. D-078 quoted the instruction and D-089 records Sol's refusal, but declining an explicit scheduled remedy was never written as a deviation. Now **DEV-010**.

**What D-114 changes and what it does not.** Sol refused on two grounds, *scope **and** budget*. The budget ground is measurably not binding — 6.40 h measured, ~32–52 h for a 5–6× design, against a 120-hour trigger — and the schedule's pre-emption *"it costs Kaggle time, not your time"* is **confirmed**, not refuted. **The scope ground is untouched**: the twenty-week calendar, ~14 h/week, and generating 5–6× the data are unaffected, and 1,500–2,000 held-out units is a ~twenty-fold gap that is fairly read as a different study. **Sol's to re-rule; nothing acted on.**

**Tests:** 835 passing, 2 skipped. **No fits.**

### 2026-08-22 (delta-53 ruling) · A false conclusion, a frozen cap, and the balancer · Claude

**Sol certified D-111** (base → **`51907c6`**), **accepted D-113**, **withheld D-114**, and **authorised the W5 balancer**.

**>>> My expansion conclusion was arithmetically false, and it inverted an answer rather than merely overstating one.** I read the MDE's 1,500–2,000 as *total* units and got a 5–6× design; they are **held-out** units. Against 60–80 held out of 300, expansion is **18.75×–33.3×** — **120 h at best, ~213 h at worst**, against a 120-hour trigger, before collection, ablations, orchestration and host differences. **The budget ground stands; both of Sol's grounds hold; no expansion is authorised.** Verified before accepting. D-042's shape at its purest — *a number without its estimand*, where "units" named two different populations. DEV-010's text is corrected in place.

**D-114 is not certified, and every objection lands.** The harness times **one baseline ensemble at one seed**, not one full condition through its seeds and repairs; it **subtracts ablations**, which stay in the budget until a reduction is actually decided, and omits collection and orchestration; it **persists nothing**, so the numbers are prose to trust rather than evidence to audit — the delta-49 failure in a new place; **one observation per size**; and local CPU/RTX numbers **are not Kaggle GPU-hours**. **W4 Friday timing is OPEN.**

**Frozen on Sol's authorisation, before any labelled data exists:** `CRITIC_TRACE_CAP_PER_UNIT = 50`, `CRITIC_BALANCE_SEED = 0`. **The cap is a maximum, not an eligibility threshold** — a unit with fewer than 50 eligible traces is kept whole, never excluded and never resampled up.

**The W5 balancer is built** on synthetic inputs (`src/bu/critic/balance.py`): per-split independence, undecidables excluded first, `m = min(n₀,n₁)` per split, deterministic `blake2b` selection, capped draws without replacement, zero-trace units refused, X/y/groups separate, a manifest, the D-039 cross-split group assertion, and `unit_weights()` holding the unit-weighted estimand.

**>>> My determinism test was vacuous, and only mutation testing found it.** It spawns interpreters under two `PYTHONHASHSEED` values to prove the selection does not depend on Python's randomised `hash()` — and swapping `blake2b` for `hash()` **did not fail it**. The fixture had 6 units per class, so `m = 6`, **every unit was selected**, and ordering could not matter. Rewritten 12-against-3 so 9 are excluded, with in-fixture assertions that it selects selectively at all. It fails on the mutation now. **A fixture that selects everything tests nothing** — D-055's shape, reached through the data instead of the assertion.

**Also done:** DEV-009's methodology section, and D-112's arithmetic corrected to Sol's wording (375 is *sweep-plus-all-canonical*; duplicating only the 20 2A units gives **320**).

**Tests:** 835 → **848 passing**, 2 skipped. **No fits, no reserve consumed, no real labels.**

### 2026-08-22 (W4 timing rebuilt) · Week 4 is complete · Claude

**Sol's authorisation was explicit** — *"you are authorised to complete W4 timing with pilot-only compute"* — so this did not wait. The host question had one branch available: no Kaggle access here, which is the case Sol said to record as a deviation. **DEV-011** now records that every fit this project has ever run has run locally, and that the plan's Kaggle T4 has never been used.

**All six requirements met** (D-116): 8,197 fits **including the 150 ablations**; 2,947 collection events counted per condition; warm-up plus 3 repetitions with every raw observation kept; median **and** maximum, with **the verdict on the maximum**; one representative condition — the largest repair-validation unit, 20 seeds, baseline ensemble plus 10× data-repair arm, **120 fits over 40 conditions** — run end to end; evidence persisted **and tracked**; host stated honestly.

**6.95 local wall-hours** conservative (5.68 median) against the 120-hour trigger, **0.058×**. The reconciliation is the load-bearing part: the full condition **measured 489.2 s** against **455.8 s** predicted (median) and **573.0 s** (max) — measured sits 7% above the median and **below** the maximum, so the conservative basis is conservative in fact.

**>>> The reconciliation caught a defect in itself.** attempt-001 reported measured/predicted = **0.03**. `reconcile()` had filtered on `n_transitions == 5000`, matching **every** unit at that size — 1,464 plan entries against the 40 that ran, **37.9×**. Corrected, re-derived from attempt-001's own raw data: **1.028**. attempt-001 kept with a `SUPERSEDED.md`, because attempts are immutable and this is the clearest proof in the project that an end-to-end check does what a microbenchmark cannot do on itself.

**>>> And the evidence was silently untracked — the third time.** `runs/*` swallowed `runs/w4_timing/` exactly as it swallowed `runs/w4_threshold/` (D-103) and as file selection swallowed delta 12's artefacts (D-041). Caught by running `git check-ignore` before committing instead of trusting the commit. **Three occurrences, three mechanisms, one shape.**

**Nothing here revises Gate 1**, still **FAIL**, and nothing revives expansion: D-115 fixed that arithmetic, and at **18.75×–33.3×** it is **130–232 wall-hours** — firmer now that ablations and collection are counted.

**Tests:** 848 → **855 passing**, 2 skipped. **No registered fits**; pilot timing only, ~35 min.

### 2026-08-22 (W4/W5 audit) · Six findings in code that was specified, tested, and never probed · Claude

**Audited this session's new code by probing it** — `critic/balance.py` and the rebuilt `w4_timing.py` had been specified point by point by Sol and covered by 23 passing tests of mine, and **never probed**. That is exactly the condition D-105 found `gate.py` in, four Sol reviews deep.

**The balancer failed open on the case Gate 2 exists to detect.** With one class absent from a split, `m = min(n₀, n₁) = 0`, and it **returned an empty evaluation set and raised nothing**. Not hypothetical: Gate 2's second condition is whether the surviving per-class unit count still clears the MDE requirement, and D-089 records that usable class counts may shrink once ambiguous and undiagnosed units are excluded. **Every comparable place in this project fails closed** — `masked()` refuses an empty mask, `acceptance` refuses non-finite errors, `trend` refuses non-finite curves. This was the one that did not. Also: **string labels were silently undecidable** (numpy integers, checked, are fine), and a **duplicate `unit_id` merged two units into one** under the registered unit-weighted estimand.

**The timing record could not be audited by machine.** JSON has no integer keys, so `fits_by_size` round-tripped as **strings** and feeding a stored record back into `extrapolate()` raised. **The numbers were right** — coerced, they reproduce bit-identically — but "auditable without trusting copied prose" is not satisfied by a record only a human can re-derive by hand. `recompute_totals()` is now the timing analogue of `recompute_threshold`. And **`_rate`'s fallback was optimistic while its docstring claimed to be conservative**: unreachable today, which is precisely why it would have survived until the design grew a larger size.

**Certified artefacts re-verified after every change** — W4 Tuesday's gate still passes (90 cells), W4 Friday's threshold still recomputes to the frozen constant exactly.

**Not one finding was a coding error in the ordinary sense.** Each was a guard that was absent, a claim that did not match behaviour, or evidence that could not be re-derived — the same class D-099 and D-105 found, and the reason this project audits *after* reviewing rather than instead of it.

**Tests:** 855 → **863 passing**, 2 skipped. **No fits, no reserve, no real labels.**

---

### 2026-08-22 (delta-54 closeout) · Boundary integrity and evidence provenance · Claude

**Sol withheld certification of the timing and the balancer, and W4/W5 stay OPEN until this closeout is certified.** All seven findings reproduced before being fixed. Every one was a **boundary** defect — both algorithms were right; the public input surface let silent design violations through.

**The balancer's six fail-open paths.** Invalid labels were caught **only when they emptied a class**, so a split with a valid `0`, a valid `1` and a string `"0"` balanced happily and filed the string as *undecidable* — my own guard from one review earlier fired only at `m == 0`, so the all-string fixture passed and the **mixed** one never existed. **Booleans refused** (`True == 1`, and `bool` subclasses `int`). `unit_id` uniqueness was **per-split**, so one content-hashed unit could sit in train *and* held-out under different group ids — training and evaluating on the same configuration. The **frozen cap was caller-overridable**. An **unrecognised split name was silently dropped**. **`balance_split()` bypassed the cross-split group guard** although it is public and is what the tests call. **Duplicate trace ids defeated "without replacement"** — sampling draws distinct *positions*, so `(4, 4, 9)` could select trace 4 twice.

**The cross-unit verdict is gone.** The record said *local wall-hours* and the program printed a ratio against a **GPU-hour** trigger — and a test of mine asserted it as a PASS. In the one harness that exists *because* a compute condition was adjudicated on a proxy for its own quantity. `comparison_status` now reads **"not adjudicable across hosts"**; the bare field name is gone too, because it invites the comparison.

**Provenance repaired, and the defect was real.** attempt-002 named `f0ac645` with `tree_clean: false`, and `f0ac645` **predates** the rebuild in `e3e9411`. Provenance is now captured **before** the run, a dirty tree is **refused** (proved by dirtying one), and a sha256 sits beside the record. **attempt-003** ran from a clean tree at `1a28647`: **5.715904170861654 / 6.913811402539251** local wall-hours, **recomputing bit-identically**, reconciliation **1.0684**.

**And a new W5 gap, found while checking whether the weeks were finished.** S§W5 Thu requires *"configuration count set from it, **with the exclusion-rate assumption stated**"*. No exclusion rate is stated anywhere — it appears three times only as a forward promise — **and S§W6 Mon is scheduled to check batch 1 against it.** Sol's to ratify.

**Tests:** 863 → **873 passing**, 2 skipped. **No fits, no reserve, no labels.**

---

### 2026-08-23 (delta-55 micro-closeout) · attempt-003 certified; the last three boundaries · Claude

**Sol CERTIFIED attempt-003 and ruled W4 Friday's timing obligation substantively COMPLETE under DEV-011.** It verified the record independently — recomputing from the raw repetitions — and confirmed the commit, the clean-tree flag, the digest, both hour figures and both reconciliation ratios. The bundle digest Sol quoted matches the delivered file byte-for-byte. **No fourth timing attempt was required and none was run. W5 remained open only for this closeout.**

**Gate 1 condition 2 is NOT ADJUDICABLE, which is not a PASS.** Gate 1 remains **FAIL** independently on the MDE condition, and expansion stays refused on scope and power grounds.

**>>> The dimensional error survived the fix that was meant to end it.** D-115 corrected a false expansion claim and, in correcting it, compared **local CPU wall-hours** against a **GPU-hour** trigger — *"120 h at best and ~213 h at worst against a 120-hour trigger"* — and CLAUDE.md's current-state section carried *"compute PASS"* and *"130–232 local wall-hours"* against the same trigger. **That is the comparison `w4_timing.py` was rebuilt to refuse, reproduced in prose.** The conclusion is unchanged and both of Sol's grounds stand; the 18.75×–33.3× multiplier is unaffected because it is a ratio of unit counts and carries no host. Historical entries stay append-only; DEV-010, CLAUDE.md and §1 carry the correction (D-119).

**All six items reproduced before being fixed; one was worse than reported.** The balancer's *"recognised split"* was **caller-defined** — `held-out` units with `splits=("held-out",)` passed, because the guard could be satisfied by repeating the typo. Trace ids were **coerced with `int()`**, and the measured behaviour is not a crash but **silent row substitution**: `4.9 → 4`, `"4" → 4`, `True → 1`, `-1` indexing from the end, each a real but unintended trace, each passing the duplicate check because uniqueness was tested before type. `BALANCE_SCHEMA_VERSION` was **still 1** after the delta-54 closeout added a manifest field — confirmed from git — and is now **2**, before any real manifest exists.

**Timing provenance, and a failure mode worse than assumed.** `_git()` dropped the return code. The assumed consequence was an empty string; measured, `git rev-parse <bad-ref>` **echoes the ref to stdout** and exits 128, so it returned `'definitely-not-a-ref'` — a plausible 20-character string that would have been stored as a commit. Now fail-closed, with a 40-lowercase-hex guard in the **harness**, where previously the only length check lived in a test on the delivered artefact that skipped when the field was absent. The digest test **asserted only that the sidecar existed** — the D-071 shape in the one artefact whose purpose is provenance — and now compares contents.

**>>> A fourth catch of the shape `.gitignore`'s own header describes.** Sol's requested correction note landed inside `runs/w4_timing/attempt-*/`, whose allowlist names three filenames and nothing else. **It would have been invisible in the next bundle.** Allowlisted, and the test asserts it is *tracked by git*, not merely present.

**The exclusion-rate assumption is ratified as DEV-012** — **0.00**, explicitly a zero-inflation **planning convention** and not a measurement, target `ceil(300 / (1 − 0.00)) = 300`, estimand **(ambiguous + undiagnosed) / all attempted labelled units** reported pooled and by intended class, and any observed exclusion above zero at S§W6 Mon means the assumption was missed. **Zero is never to be called observed, estimated or pilot-derived.**

**Tests:** 873 → **895 passing**, 2 skipped. **No fits, no timing rerun, no reserve, no labels.**

---

## Delta 56 — DELIVERED 2026-08-23, CERTIFIED by Sol (D-120)

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 56 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-23 (delta-55 micro-closeout) · attempt-003 certified; the last three boundaries

```
=== UPDATE FOR SOL ===
DELTA_ID: 56
PREVIOUS_DELTA_ID: 55
DATE: 2026-08-23
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: Your micro-closeout, complete. Seven items: three balancer boundaries,
         the timing schema correction, fail-closed provenance, the compute-
         condition correction of record, and DEV-012. Plus one catch of my own
         that would have made your requested correction invisible.

Delta 55 confirmed delivered: you quoted bundle sha256 25e58960...d1512e0d17,
which matches the file byte-for-byte. You reviewed exactly what was generated.

ALL SIX OF YOUR ITEMS REPRODUCED BEFORE BEING FIXED. Every one held. TWO WERE
WORSE THAN DESCRIBED, both in the same direction -- the failure mode was not a
loud error but a plausible-looking wrong value.

--------------------------------------------------------------------
1. BALANCER -- "RECOGNISED SPLIT" WAS CALLER-DEFINED  [FIXED]

Reproduced: units with split "held-out", splits=("held-out",) -> ACCEPTED, and
balance_split(split="held-out") -> ACCEPTED, 4 traces selected.

CANONICAL_SPLITS = ("train", "validation", "held_out") is now the only source of
split names. Enforced on the REQUESTED name and on EVERY SUPPLIED UNIT's name,
in balance() and balance_split() alike. A caller can no longer legalise a typo
by repeating it.

I kept the original property as a SEPARATE test rather than folding it away:
canonical-but-not-requested ("validation" units when only "train" was asked for)
must still be refused. The canonical check now fires first, so without a second
test that second property would have quietly stopped being covered.

--------------------------------------------------------------------
2. BALANCER -- TRACE IDS COERCED WITH int()  [FIXED -- WORSE THAN STATED]

You said these "can pass the duplicate check and then be silently converted or
interpreted as a valid index." Correct, and the measured consequence is not an
error at all -- it is SILENT ROW SUBSTITUTION:

    4.9   -> trace 4      (a real, different trace)
    "4"   -> trace 4
    True  -> trace 1
    -1    -> indexes from the end of the array

Nothing raised in any case. The balancer returned a clean selection over the
wrong rows.

Now: exact non-negative integers only. NumPy integers accepted (np.int64/int32
verified), booleans refused BEFORE the integer check since bool subclasses int,
floats and strings refused, negatives refused, THEN uniqueness. Order is load-
bearing and pinned by a test: validating uniqueness first makes 4 and 4.0 two
distinct ids.

--------------------------------------------------------------------
3. BALANCER -- SCHEMA VERSION NOT BUMPED  [FIXED]

Confirmed from git rather than from reading: BALANCE_SCHEMA_VERSION = 1 was set
in f0ac645, unit_to_comparison_group was added in 1a28647. Never bumped, against
its own comment.

BALANCE_SCHEMA_VERSION = 2, set before any real manifest exists, so no stored
artefact is ambiguous. Pinned by a test on both the constant and the manifest.

--------------------------------------------------------------------
4. TIMING SCHEMA CORRECTION  [DONE -- attempt-003 UNTOUCHED]

runs/w4_timing/attempt-003/SCHEMA_CORRECTION.md records that the stored
schema_version: 1 is a metadata defect corresponding to the provenance-aware
schema. TIMING_SCHEMA_VERSION = 2 for future records.

The JSON is byte-identical and still hashes to
bb504b2c1369f3bc390e4f5196207c08f94ddd74025f359486090a6aa0bb3b80.
No rerun. No rewrite.

--------------------------------------------------------------------
5. DIGEST-CONTENT REGRESSION + FAIL-CLOSED GIT  [FIXED -- WORSE THAN STATED]

The digest test asserted only that the file EXISTED. A sidecar holding a stale
hash, the wrong hash, or the word "banana" passed it -- the D-071 shape, in the
one artefact whose entire purpose is provenance. It now recomputes the sha256
and compares contents, with a companion test proving the comparison can fail.

_git() dropped the return code. I expected the failure mode to be an empty
string. IT IS NOT. `git rev-parse <bad-ref>` ECHOES THE UNRESOLVABLE REF TO
STDOUT and exits 128:

    _git("rev-parse", "definitely-not-a-ref")  ->  'definitely-not-a-ref'

A 20-character plausible-looking string, which would have been written into a
provenance record as a commit. Now raises on non-zero exit, and _require_commit()
demands exactly 40 lowercase hex characters.

Note where the old 40-character check lived: in a TEST ON THE DELIVERED
ARTEFACT, which skipped when the field was absent. The harness itself validated
nothing. The guard is now in the harness, at the point of capture.

--------------------------------------------------------------------
6. >>> MY OWN CATCH -- YOUR CORRECTION WOULD HAVE BEEN INVISIBLE

The correction note you asked for lands inside runs/w4_timing/attempt-*/, whose
.gitignore allowlist names timing.json, timing.json.sha256 and SUPERSEDED.md
AND NOTHING ELSE. SCHEMA_CORRECTION.md was silently ignored.

That is the D-041 shape -- prose and digests without the bytes -- and the header
comment on those very rules says it has been caught three times already. This
is the fourth. Allowlisted, and the test asserts the note is TRACKED BY GIT
rather than merely present, because "exists locally" is what failed before.

--------------------------------------------------------------------
7. COMPUTE CONDITION -- CORRECTION OF RECORD  [DONE]

Current summaries now read exactly as you specified:

  W4 local timing evidence: complete and certified
  Local estimate: 5.72 / 6.91 LOCAL WALL-HOURS
  Registered trigger: 120 GPU-HOURS on the planned Kaggle T4
  Cross-host comparison: NOT ADJUDICABLE
  Gate 1 condition 2: NOT ADJUDICABLE under DEV-011, NOT PASS
  Overall Gate 1: FAIL independently on the MDE condition
  Expansion: still not authorised, on scope and power grounds

I have to report where that error actually was, because it is worse than a
stale summary. D-115 was ITSELF the correction of a false expansion claim -- and
in correcting it I wrote "120 h at best and ~213 h at worst against a 120-hour
trigger". Local CPU wall-hours against a GPU-hour trigger. THE DIMENSIONAL ERROR
SURVIVED INSIDE THE FIX THAT WAS SUPPOSED TO END IT, and CLAUDE.md's current-
state section still said "compute PASS" and "130-232 local wall-hours" against
the same trigger.

The 18.75x-33.3x multiplier is unaffected -- it is a ratio of unit counts and
carries no host -- and the conclusion is unchanged: both of your grounds stand,
expansion stays refused. Where the budget ground is retained it is now grounded
in the registered GPU-hour design estimate and the scope decision, not in
arithmetic across hosts.

Historical D-114/D-115/D-116/D-118 text is untouched, per append-only. DEV-010
carries an appended FURTHER CORRECTION, and D-119 is the correction of record.

--------------------------------------------------------------------
8. EXCLUSION RATE -- RATIFIED AS DEV-012

Recorded exactly as you ratified it, as a DEVIATION, before any real labels
exist:

  planning exclusion-rate assumption: 0.00
  interpretation: a ZERO-INFLATION PLANNING CONVENTION, not an empirical
                  prediction that exclusion will be zero
  initial gross configuration target: ceil(300 / (1 - 0.00)) = 300
  no anticipatory class oversampling
  observed estimand: (ambiguous + undiagnosed) / all attempted labelled units,
                     reported POOLED and BY INTENDED CLASS
  W6 Mon comparison: any observed exclusion above zero means the planning
                     assumption was MISSED
  response: report the shortfall; use ONLY the predeclared D-092 reserve
            procedure, subject to its existing authorisation gate
  Gate 2: continues to use surviving min(N0, N1), NEVER total units

DEV-012 states in terms that zero is never to be described as observed,
estimated or pilot-derived.

--------------------------------------------------------------------
9. Q-012 -- WHAT IS AUTHORISED AFTER W5 CLOSES?  [QUESTION, NOT A CLAIM]

If you certify this closeout, W4 and W5 are both complete and the last open
schedule cell is closed. I do not know what I am authorised to do next, and I
would rather ask than assume.

The project runs about four weeks ahead of the calendar (DEV-002). Q-004 rules:
hold every date and gate, spend the gain on REVIEW, UNDERSTANDING, DOCUMENTATION
AND PROSE, NEVER SCOPE. Read literally, that authorises no further
implementation at all.

But two obligations you raised are still unbuilt:
  C-005  the grouped critic splitter -- a comparison group never spans a split
  C-007  require_confirmatory=True in the remaining critic loaders

Both are W6-W11 work. Building them is not Week 6 EXECUTION -- no collection, no
labels, no reserve. So they may be authorised, or building ahead may be exactly
the VERIFICATION LAG Q-004 names: implementation outrunning the student and the
reviewer, leaving choices embedded in code before they are understood.

I am not asking you to expand scope. I am asking which of these is right:
  (a) build C-005/C-007 now, delivered for review before anything depends on them
  (b) build nothing; spend the gain on prose, methodology and review as Q-004 says
  (c) something else you would rather I did with four weeks of slack

Registered as Q-012. I have started none of it.

--------------------------------------------------------------------
NUMBERS (D-011)

  tests          873 -> 895 passing, 2 skipped, 0 xfailed
                 (22 new: 11 balancer boundary, 11 timing provenance)
  attempt-003    UNCHANGED, sha256 bb504b2c...0bb3b80, still verifies
  timing         5.715904170861654 / 6.913811402539251 LOCAL WALL-HOURS
  comparison     not adjudicable across hosts
  compute        NONE THIS SESSION. No timing rerun, no fits.
                 Registered total unchanged: 675 CPU fits, 0 GPU-hours.
  data seen      none. Synthetic units, stored records, git metadata.
  base           51907c6

W5 is open only for this closeout. No expansion, reserve consumption, real
labels, recalibration, or Week 6 work has been performed or is claimed.
=== END UPDATE ===
```
