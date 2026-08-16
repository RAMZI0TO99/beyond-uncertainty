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
