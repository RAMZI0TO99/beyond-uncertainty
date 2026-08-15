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
