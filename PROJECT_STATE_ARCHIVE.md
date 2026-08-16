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
