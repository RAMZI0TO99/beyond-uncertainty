# → TO SOL
**This file is what the student pastes to Sol.** Nothing else.
It accumulates until delivered (D-008) and is only then replaced; if the flag
below reads NO, **append**, never overwrite.
**Where the delivered deltas actually are** (corrected 2026-08-23, D-120 — the
line here previously claimed 10–54 were archived and they were not): deltas
**1–7 and 10–33** are in `PROJECT_STATE_ARCHIVE.md`; **8 and 9** never existed
as delivered blocks (DEV-005); **34–55** were replaced without being archived
and live only in **git history**, each at the commit that delivered it
(`git log -S "DELTA_ID: NN" -- DELTA_TO_SOL.md`); **56 onward** are archived on
replacement, as the convention always intended.
**Send delta + `SOL_BUNDLE.txt`.** For review, `BASE` is **`4e55291`** — Sol
certified delta 63 on 2026-08-23 (D-131). For patch application, the exact real
repository target is **`66edf4a11dce39b91974d5c331cca81424f83b6e`** (D-140).
These are different anchors; do not apply the series directly to `4e55291`.
**Delta 64 carries a student-obligation progress report only** — the student's
methodology chapter draft (provenance disclosed, D-132) and the end-of-session
integrity audit. Later Claude/Codex work is carried separately in deltas65–71;
the student explicitly authorised it under DEV-013…022.
```bash
EXCLUDE="PROJECT_STATE_ARCHIVE.md" BASE=4e55291 ./scripts/sol_bundle.sh \
    <files changed by the next authorised work> > SOL_BUNDLE.txt
```
---
## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*
> **Delivered to Sol:** ☐ **NO** — DELTA_IDs64–71(D-008). All eight
> preserved blocks remain below. Delta70's mandatory additive closeout is
> `docs/week7_sol_closeout.md`. Deliver all seven and the companion together.
>
> COVERS SESSIONS:
> - 2026-08-23 (delta-63 certification) · The whole prose closeout is CERTIFIED; base → `4e55291`
> - 2026-08-23 (student chapter) · The first full methodology chapter arrives; provenance disclosed
> - 2026-08-23 (session close) · End-of-session audit; three stale claims fixed; everything committed
> - 2026-08-29 (student-authorised session) · Sol out of the loop by the student's direction; D-133 guard defect fixed; C-005/C-007 built; thirteen stale claims fixed
> - 2026-08-30 (post-Fable audit) · C-005/C-007/provenance correction
> - 2026-08-30 (Sol2 Week-6 readiness) · Provenance hardening and Week 6 blocker discovery
> - 2026-08-30 (Sol2 Week-6 integration) · Persisted evidence, isolated launch and final audit
> - 2026-08-30 (Sol2 Week-6 execution) · Owner-authorised CPU preflight and registered run
> - 2026-08-31 (Sol2 Week-7 implementation) · Verified evidence and baseline configuration preparation
> - 2026-09-01 (Sol2 Week-8 start) · Exact bounded inventory and pre-analysis specification

```
DELTA70_ADDITIVE_CLOSEOUT2026-09-01: COVERS the same ongoing Sol2Week7execution session. Mandatory companion `docs/week7_sol_closeout.md` SHA256 `ebfbb3fc8fe65b7679382147608ac9532b180f30d32e2f049c67fc0170ba373c`. NUMBERS:578newfits/1330models; E1474/834,E2A95/475,sweep3/15+6/6;0other/unknownattempts;12094.442840200325s supervised-attempt wall;GPU0. E1labels30:N0=29,N1=0,ambiguous0,undiagnosed1,min0;6units×20seeds,24×3,all60intervalsformed. Sweep:N0=N1=ambiguous0,undiagnosed1,3seeds; exact effects/CIs in companion. GuardedQA4085pass/8skip/51subtests;XMLf892e470...;failedpath/probe history preserved. E2A readback4c4ae415...;accounting3856368d...; all source/exposure/CI support and replay limits in companion/results. Machine-complete only: student~400Week6/~500Week7 own-voice, delivery and externalSol certification remainopen. No E2Alabels,H2/H3,exclusionrates,reserve,extra224sweepgroups,scope/dateadvance. Generated isnotdelivered.
=== UPDATE FOR SOL ===
DELTA_ID: 64
PREVIOUS_DELTA_ID: 63
DATE: 2026-08-23
BUNDLE_FILE: SOL_BUNDLE.txt -- carries the student's chapter for
             reference only; no ruling requested
SUBJECT: Student-obligation progress: a full methodology chapter draft exists,
         provenance disclosed (student-written, AI-polished), audited 32/32
         clean. Defense walkthrough pending. No ruling requested.

STUDENT-OBLIGATION PROGRESS REPORT -- NO RULING REQUESTED.

The student delivered docs/methodology_chapter.md: a complete 17-topic
methodology chapter, internal apparatus stripped as the thesis version
requires. Asked directly how it was produced, THE STUDENT DISCLOSED
UNPROMPTED: they wrote the content and an AI polished the prose.

I audited it against the certified record before any judgment: 32/32
checkable claims and numbers verify exactly, zero factual errors, every
D-121..D-131 correction incorporated -- including rulings from hours earlier.

STATUS, stated in the file's committed provenance header (removed from the
final thesis version): ASSISTED DRAFT under your D-125/D-131 framework. The
explain-and-defend walkthrough is deferred at the student's request, not
waived. Until it is done and you have ruled, the chapter does not enter the
thesis and is not described as independently authored.

--------------------------------------------------------------------
2. END-OF-SESSION INTEGRITY AUDIT -- CLEAN AFTER THREE FIXES

Run mechanically across every surface at session close: git integrity (tree
clean, nothing unpushed, your base 4e55291 an ancestor of HEAD); all nine docs
tracked (no D-041 shape); the delta chain complete (56-63 archived with
headers, 64 open); live-surface base/test-count consistency; D-citation
validity; and a whitespace-normalised stale-claim scan.

Three stale claims found and fixed, disclosed rather than silently patched:
  - CLAUDE.md said "delta 64 is open but empty" (it carries this report);
  - CLAUDE.md retained the categorical "Clearing five points needs" phrasing
    your F-corrections replaced -- now the rough-extrapolation wording;
  - the delta header still said "intentionally EMPTY".
One scan hit was a correctly-labelled quotation of an old error; left alone.

SESSION SUMMARY, for your continuity: deltas 55-63 delivered and resolved;
D-119..D-132 filed; four certifications (attempt-003, delta 56, delta 60,
delta 63); base advanced 51907c6 -> 801a33d -> c5c8e6f -> 4e55291; tests
873 -> 895; W4 and W5 completed and certified; the prose closeout and the
C-005/C-007 prose spec certified; the plan/schedule audit accepted with all
findings ruled.

SOL_BUNDLE.txt regenerated at HEAD carries docs/methodology_chapter.md FOR
REFERENCE ONLY -- so you can read the student's draft ahead of the walkthrough.
No ruling is requested until the walkthrough is done.

Nothing else to report; no Claude-side work is claimed for certification in
this delta.

--------------------------------------------------------------------
NUMBERS (D-011)

  tests          895 passing, 2 skipped, 0 xfailed
  ran            no experiment or data pipeline; only the existing suite
  compute        none
  base           4e55291 (certified, D-131)
  built          the STUDENT's chapter draft (assisted; provenance disclosed);
                 Claude built nothing and requests no ruling

=== END UPDATE ===
```


```
=== UPDATE FOR SOL ===
DELTA_ID: 65
PREVIOUS_DELTA_ID: 64
DATE: 2026-08-29
BUNDLE_FILE: session_2026-08-29.patchseries (git format-patch, attached) +
             SOL_BUNDLE.txt to be generated on the REAL repository after the
             student applies the patches -- see PROVENANCE CAVEAT
SUBJECT: A student-authorised session ran WITHOUT your pre-approval (DEV-013):
         a real defect in C-008's obligation guard found and fixed (D-133),
         C-005/C-007 implemented from your certified spec (D-134/D-135),
         thirteen verified stale-prose claims fixed (D-136), all on a git-less
         snapshot with a reconstructed environment (D-137). Nothing consumed
         data, labels, seeds or reserve; everything is reversible and awaits
         your ruling.

READ FIRST -- GOVERNANCE. The student directed: "work without Sol for now ...
we will report to sol everything in the end of this session." That overrides,
for one session and on the owner's authority, the D-120/Q-012 allocation under
which nothing was authorised to be built. It is recorded as DEV-013 -- and as
a hit against the Q-001/D-001 tripwire -- not presented as compliant. You may
rule any part void; every change is an isolated commit and reverts cleanly.

PROVENANCE CAVEAT (D-137). The working copy is a dotfile-stripped export --
no .git, no .venv. Your certified base 4e55291 exists in no local history, so
BASE-anchored bundling was impossible here. Instead: a local baseline commit
(ff18c9e) captures the snapshot exactly as received; every change is a commit
on top; the session exports as a patch series the student applies to the real
repository, where the tree must come back clean before SOL_BUNDLE.txt is
generated against BASE=4e55291 as usual. The pinned environment was rebuilt
from pyproject.toml (all eight pins + pytest exact; deviations: Python 3.13.5
vs the repo's 3.12, CPU-only torch so three CUDA tests skip here). Four
evidence-tracking tests failed on Windows path separators with the evidence
fully tracked (458 files); fixed with as_posix() (D-028's class).

1. THE DEFECT (D-133). _registered_obligations() in confirmatory.py was built
from the no-arg execution_plan(), which defaults to full_matrix() -- the
531-unit POOL -- not design_units(), the registered 300. Measured: all 231
pool-only sweep units were ACCEPTED as registered obligations at confirmatory
seed 1000. No such fit was ever run. Fix: execution_plan(design_units()),
the same call w4_timing makes. Shrink-only, verified: registry 4,675 -> 3,022
keys, new set a subset of the old. Two property tests bracket it: all 231
pool-only units refused (shown failing before the fix), all 225 design sweep
units still accepted. RAISED FOR YOU: execution_plan's fail-open default has
now bitten a guard once and needed the explicit argument three times; should
the default go?

2. C-005 / C-007 IMPLEMENTED (D-134/D-135) from the spec you accepted at
D-130 and certified at D-131, student-authorised ahead of the W6-W11 slot.
Four new files only: src/bu/critic/split.py (833 lines), loading.py (372),
tests/test_critic_split.py (754), tests/test_critic_loading.py (401) -- 92
property tests. balance.py, schema.py, metrics.py, constants.py UNTOUCHED.
Key properties, each with a test you can run: whole-group assignment (D-039)
fed unmodified into the certified balancer's assert_groups_do_not_span_splits;
mixed-INTENDED-class groups refused, mixed OBSERVED labels accepted (D-128);
the four ordered steps separate -- the certified balancer simply receives
only observed 0/1 along the splitter path (excluded_undecidable pins to []
end-to-end); deterministic constrained allocator, blake2b tie-break only,
determinism proven across interpreters under two PYTHONHASHSEEDs; fail-closed
with exact shortfalls; SPLIT_SCHEMA_VERSION 1 manifest recording both class
concepts, every count recomputable from mapping + inputs (D-072). C-007: the
confirmatory requirement is a property of the loading boundary -- the flag is
a body literal, the parameter does not exist; a separate development path
dead-ends before the critic; consumers come from an authoritative registry
and an unregistered loader fails the coverage test; missing stage/seed
metadata fails closed. NOT created: CRITIC_SPLIT_SEED and the registered
numeric targets -- your spec names both as Change-Record-gated, so the
splitter fails closed where they would be needed and tests inject synthetic
values as fixtures.

OPEN QUESTIONS FOR YOUR RULING (full list in D-134/D-135):
  a. Is fixture injection of a synthetic split seed acceptable until the real
     Change Record lands (the public API exposes no seed)?
  b. The allocator is a registered, frozen, deterministic procedure that can
     conservatively refuse a feasible instance (refusals distinguish provable
     aggregate infeasibility from procedure fixpoint). Acceptable under
     fail-closed discipline, or do you require a complete search?
  c. The boundary refuses stage='pilot' even at confirmatory seeds (two-roads
     reading; the spec's letter gates on seeds and metadata). Wanted, or
     overreach?
  d. Groups with zero decidable units are placed deterministically by
     tie-break and reported, not balanced. Sufficient?
  e. The coverage scanner tokenizes call sites rather than raw substrings
     (frozen schema.py mentions load_runs() in prose); empty loads and empty
     wrappers are refused beyond the spec's listed refusals. Both fine?

3. PROSE (D-136). Thirteen verified stale claims fixed across README ("runs/
gitignored, regenerable" -- the inverse of the evidence contract), CLAUDE.md
(threshold "calibrated but not frozen" -- false since D-107/D-109; the dead
acceptance fallback; the stale dateline and delta pointers), PROJECT_STATE
sections 1 and 6, config.py's header (the four identities). Section 1's
Gate-1 paragraph also corrected in rewrite from "Compute PASS, contingent" to
NOT ADJUDICABLE per your D-119 ruling. Every edit cites its controlling
D-number; append-only sections untouched.

4. WHAT DID NOT HAPPEN. No real data, no labels, no reserve, no confirmatory
execution, no threshold action, no constants.py change, no expansion, no
recalibration. The MDE/Gate-1 record is untouched. The student's walkthrough
obligation (delta 64, unchanged above) remains open.

--------------------------------------------------------------------
NUMBERS (D-011)

  tests          987 passing, 4 skipped, 0 xfailed on the snapshot host
                 (was 895/2: +92 new C-005/C-007 tests; +2 skips are CUDA
                 tests on this CPU-only torch; 4 Windows path failures fixed)
  ran            the test suite only; no experiment or data pipeline
  compute        none (CPU test fixtures only)
  base           4e55291 remains your certified base (D-131) -- NOT advanced;
                 local snapshot baseline ff18c9e, 7 session commits, patch
                 series attached; the HEAD is the commit carrying this delta
  built          D-133 guard fix; C-005 splitter; C-007 boundary; D-136 prose
                 fixes; D-137 environment reconstruction; D-133..D-137 +
                 DEV-013 filed

=== END UPDATE ===
```

```
=== UPDATE FOR SOL ===
DELTA_ID: 66
PREVIOUS_DELTA_ID: 65
DATE: 2026-08-30
BUNDLE_FILE: session_2026-08-29.patchseries (patches 0001, 0003..0008) +
             SOL_BUNDLE.txt generated in the REAL repository after application
SUBJECT: Post-Fable audit corrections (D-138..D-140, DEV-014): D-133's
         execution-history claim corrected; C-005 false infeasibility fixed;
         C-007 provenance hardened and its scope narrowed to loading boundary
         only; git-less provenance fixed; exact patch target established.

GOVERNANCE. The student explicitly asked Codex to continue Fable's work before
Sol reviewed delta 65 and authorised parallel agents. This is DEV-014, a second
recorded instance of Q-004 verification lag. It does not expand authority into
real data, labels, reserve, registered constants, threshold work, expansion or
experiment execution. You may accept, amend or void these changes.

1. CORRECTION TO D-133 (D-138). Delta 65's statement that only tests had used
confirmatory-range seeds is false: the certified threshold calibration ran 45
cells x 5 members = 225 real fits at seeds 1000..1004 (D-103). The relevant
narrow claim remains true: no fit was executed for any of the 231 pool-only
units the bad guard admitted. The guard tests now quantify the exact obligation
domain: every removed (unit, arm, role, seed) key is refused and every exact
design key is accepted, rather than sampling one baseline key per unit.

2. C-005 AUDIT (D-139). The heuristic could stall and label a mathematically
feasible whole-group split infeasible. Reproduced synthetic counterexample:
profiles (2,1), (3,1), (3,0), (1,1), exact train (3,1), validation (1,1),
held-out (5,1). The fast deterministic heuristic remains, followed on a stall
by a complete binary feasibility model using the already-pinned SciPy/HiGHS.
Only solver-proven infeasibility is now called infeasible; an indeterminate
solver fails closed under a different message. The stable blake2b-derived
objective chooses reproducibly among witnesses. Target/floor contradictions,
bad mappings, blank ids/groups, pilot candidates, digest-field omissions and
an inert split seed now have positive regression tests. This post-spec solver
choice still requires your ruling before real use.

3. C-007 AUDIT AND SCOPE CORRECTION (D-139). ConfirmatoryRuns now revalidates
its mutable DataFrame at every consumer and cross-checks tuple metadata against
row seeds/stages. The development road refuses confirmatory or mixed seeds.
load_runs requires top-level and config stage copies to exist and agree. The
coverage scanner now catches imported aliases, qualified calls, direct
metrics.jsonl reads and nested package modules. However, C-007 is NOT
end-to-end complete: no adapter yet binds loaded run ids to repair-derived
SplitCandidate labels, and legacy LabelledUnit carries no seed/stage. The code
publishes C007_INTEGRATION_STATUS="loading_boundary_only". No scientific
adapter was invented without a registered mapping.

4. PROVENANCE AND HANDOFF (D-140). GitState.trustworthy now requires a clean
tree AND an exact 40-lowercase-hex commit. Confirmatory/threshold runners and
gate evidence reject UNCOMMITTED; allow_dirty cannot admit a git-less gate.
Dirty diffs are preserved as raw Git bytes, avoiding Windows cp1252 corruption.

The exact REAL-repository application target is
66edf4a11dce39b91974d5c331cca81424f83b6e (post-D-132/delta-64, read from the
existing bundle). The Sol review base remains 4e55291. Checkout the first,
verify every committed target:path blob against BASELINE_PREIMAGE_BLOBS.txt,
apply patches, then generate the cumulative Sol bundle with BASE=4e55291.
ff18c9e is only reconstructed local history and includes a reconstructed
.gitignore; it is not an exact remote snapshot marker. Five of Fable's seven
post-baseline commits transfer; egg-info untracking and patch-directory ignore
are local housekeeping. Do not use git am --3way.

5. WHAT DID NOT HAPPEN. No real data or labels were consumed, no reserve used,
no threshold or evidence changed, no registered split seed/target/floor added,
no experiment run and no scientific result recomputed. constants.py and the
certified balancer remain untouched. The student's chapter walkthrough remains
pending.

--------------------------------------------------------------------
NUMBERS (D-011)

  tests          1,014 passing, 4 skipped, 0 xfailed/failing in 406.28 s
                 (focused audit set: 302 passing, 1 skipped in 298.81 s)
  skipped        3 CUDA-device requirements on CPU-only torch + 1 intentional
                 vacuous identity-exclusion case
  ran            full suite including tiny real-fit fixtures; no project
                 experiment/data pipeline
  compute        no experimental compute (test fixtures only)
  review base    4e55291 (Sol-certified, unchanged)
  patch target   66edf4a11dce39b91974d5c331cca81424f83b6e
  built/fixed    D-138 exact obligation coverage; D-139 complete splitter and
                 loading-boundary hardening/scope marker; D-140 provenance and
                 portable handoff; DEV-014 filed

=== END UPDATE ===
```
```
=== UPDATE FOR SOL ===
DELTA_ID: 67
PREVIOUS_DELTA_ID: 66
DATE: 2026-08-30
BUNDLE_FILE: session_2026-08-30-sol2.patchseries (patches 0001..0015) + SOL_BUNDLE.txt generated in the REAL repository after application
SUBJECT: D-141..D-152 / DEV-015..017 — Week-6 software integrated and audited; owner-authorised frozen-CPU execution opened before external review.
GOVERNANCE. The student designated the active Codex implementation agent "Sol2", asked it to work with you instead of the historical local labels Fable/Oups, and extended the work through Week-6 integration. This name grants no review authority: you remain the external reviewer/certifier. DEV-015/016 record the implementation lag. The owner later authorised real compute, was told the frozen route is CPU and agreed to keep the device on (D-145/DEV-017). Execution remains uncertified until your review; you may accept, amend or void it.
1. PROVENANCE / EVIDENCE (D-141). Git failures now fail closed; run/config/fit identity copies, exact inventories, package pins and clean-commit attestations are cross-checked. Critic wrappers bind their frames. Serialized gate and threshold evidence rehashes its source rows. Existing certified evidence still recomputes; no statistic or frozen scalar changed.
2. WEEK-6 IMPLEMENTATION (D-142, corrected and closed in scope by D-144). The registered 20-seed repair-label runner persists one immutable plan before work, resumes only source-verified fits, uses one baseline scale for all arms, and writes a label whose 60 fit sidecars are reopened and exactly rederived. Each physical fit can attest multiple registered roles without duplication. Full action/episode/step inventories bind latent pairing; encoded-pool digests bind arms whose feature schema is unchanged. Duplicate-fit helpers refuse.
3. PRE-EXECUTION AUDIT (D-146). It stopped launch with every root empty; four smoke roots are separated from four Experiment-1 roots to avoid canary collision. Mounted sync now stages/fsyncs/atomically publishes before readback; every spawned fit is pinned to the preflight commit before pools and on reload; age-only lease recovery refuses. The exact 60-fit smoke now has its own no-compute preflight, fresh timed processes, lease/staging/incremental sync and label plus four counts only—Week-8 exclusion analysis stays closed. Experiment 1 writes matching local/durable start evidence and has a strict non-scientific partial monitor.
4. SCHEDULE CORRECTION (D-144). Missing whole-design repairs are Week 7+, not a blocker to this smoke or baseline Experiment 1. Eight of fifteen canonical repair units have one registered model repair; seven have none. Multi-role fits are represented once; exclusion comparison remains Week 8 and canonical repair validation Week 9. DEV-012's 0.00 is planning only, not an observed rate.
5. FIREWALL / OPEN BOUNDARY. X/y/groups exposes only allowlisted X. C-007 reaches persisted labels but lacks the label-to-SplitCandidate bridge; splitter/balancer remain synthetic-only pending registered parameters and authority.
6. EXECUTION / CORRECTION (D-147…D-149). Preflight passed at `750266c7`; 60/60 sidecars (140 member trainings) completed/synchronized without retry. D-147 corrected the fail-closed feature digest rule; D-148 made C evidence read-only. At clean finalizer `f6833f2`, 60 fits verified/copied, 0 executed/retrained. Observed label **0 (data only)** for intended `hypothesis_class` smoke unit.
NUMBERS: attempted/N0/N1/min/ambiguous/undiagnosed = 1/1/0/0/0/0; confirmatory seeds 1000–1019. Paired-seed-cluster 95% t intervals over 20 seed clusters: data effect −0.1493043 [−0.1716447,−0.1269639], 22.5413%, PASS; feature effect −0.0292878 [−0.0627686,0.0041930], 4.4217%, FAIL; threshold 20%, 191 episodes/ 1,102 failure-set transitions. One-unit smoke, not a rate or hypothesis result. Suite 1,669/7/0; GPU zero; historical C aggregate unchanged. Experiment 1 at `f036fe0`: 150/150 executed/synced, 0 failed/recovered, 750 member trainings, 46m03.962s; final validated monitor and byte-identical project copy. A raw-tail check exposed two per-fit summaries mid-run; no adaptation—please audit D-150.
7. D-151: P§7.3 says **>20%**, but creation/reload used `>=`; both now use `>` with exact-boundary tests. Smoke label 0 unchanged; full suite 1,671/7/0. AI-only 406-word scaffold/reminder created; Week 7 source audit opened no results. Week-7 label/figure/trend adapters are incomplete; please rule missing repairs and W7/W10 timing. D-152 confirms Phase A is already complete/certified; plan PHASE 1 is per-condition, not global launch authority. Closeout 184/1/0 in 121.95s; Week 6 awaits only the student's own-voice Thursday prose. Apply after exact target 66edf4a11dce39b91974d5c331cca81424f83b6e; review from BASE=4e55291; never `git am --3way` or infer reconstructed ancestry.

RULINGS / AUTHORITY REQUESTED:
  a. Review D-141..D-152 and DEV-015..017 plus the cumulative patch series.
  b. Review the owner's frozen-local-CPU execution choice; no Kaggle/T4 or GPU result may be inferred and the two hosts' compute units stay distinct.
  c. Approve or amend quarantine-and-restart (no within-fit checkpoint) for an interrupted fit.
  d. The owner has authorised real Week-6 smoke/Experiment-1 compute under D-145 before your review; audit the resulting exact evidence and counts.
  e. Rule the seven canonical and 173 whole-design missing model repairs, the W7/W10 trend timing, then the final C-007 bridge. None is guessed here.

=== END UPDATE ===
```

```
=== UPDATE FOR SOL ===
DELTA_ID: 68
PREVIOUS_DELTA_ID: 67
DATE: 2026-08-31
SUBJECT: D-153 / DEV-018 — owner continues Week-7 implementation; review deferred.
BUNDLE_FILE: cumulative session_2026-08-30-sol2.patchseries (0001..0016) plus real-repo SOL_BUNDLE.txt.
The owner explicitly asked Sol2 to proceed and said you would review later. This defers review, not certification. Week-6 own-voice prose remains open. NEW: exact source-bound150-fit Experiment-1 adapter; descriptive per-configuration figure preparation; immutable100-fit Exp2A/675-fit sweep baseline preparation. No configuration pooling, H1 verdict, repair assignment, reserve or launch. Five Exp2A baselines overlap the completed smoke: requirements are not new work. Every future execution must reconcile those source-verified fits first. PREPARATION: project-local week7-preparation-2026-08-31/week7_baseline_preparation.json; SHA256 9b380e4bbefa4d3c1c5a52e6ab89f8b63cac42dbfaf90cf5b19419fcc9152044. TESTS: preparation24/0 in34.19s; evidence61/0 in134.39s; figures41/0 in11.30s; old+new figures48/0 in17.79s; state13/0 in0.64s. Full-suite closeout follows. FINAL: 1,798 passed / 7 skipped / 0 failed in1,519.40s. Initial full run1796/7/1 exposed an old outside-repository scratch assumption; real-Git fixture isolation corrected, production unchanged, infrastructure47/1/0. Added real150-source-to-PNG composition1/0 passed and is included in the final full suite. Prior failure retained. DATA: no real Experiment-1 payload, new fit, label, inference or GPU in this increment. Prior deltas remain undelivered and unaltered in substance; delta67 was only reflowed. Please review implementation and the existing unresolved repair/inference choices. Week7 engineering progressed, not whole-week completion; human prose stays open.
=== END UPDATE ===
```

```
=== UPDATE FOR SOL ===
DELTA_ID: 69
PREVIOUS_DELTA_ID: 68
DATE: 2026-08-31
SUBJECT: D-154/D-155/DEV-019 — owner delegates scientific choices; fixed amendments and sweep-pairing refusal.
COVERS SESSIONS: 2026-08-31 (Sol2 scientific decisions) · Fixed repair extension and H1 reporting amendment
BUNDLE_FILE: cumulative session_2026-08-30-sol2.patchseries (0001..0018), real-repository SOL_BUNDLE.txt from unchanged BASE=4e55291, and week7-analysis-2026-08-31-attempt-001-evidence.zip (SHA256 800b9a92698817058eeb846e358bb8d2dfd3e8910c1b8d543cbcb31b99ebeef9). Not delivered/certified merely by being generated.
The owner expressly permitted Sol2 to resolve the missing scientific choices; this is not your certification. Original plan/history preserved; prior development, smoke label and two exposed Experiment-1 summaries disclosed. No claim of fully blinded preregistration.
D-154: new capacity_extension_repair is full-observation width256→512 only, one model, all other budgets/settings unchanged; existing capacity→256 untouched. All173 gaps receive one fixed intervention:7×20+166×3=638 extra single-model fits;8,835 planned trainings,300units/240groups unchanged. Not a runtime/realizability/label-completeness claim.
H1: unchanged per-configuration statistic,5configs×5seeds×6sizes; diagnostic error trends; all-five disagreement summary explicitly amended, not a calibrated global test. One immutable Week7 report; Week10 interpretation reuses it. No pooling, tuning, extra seeds or labels inferred from trends.
D-155: independent source review found, and main reproduced,225/225sweep-only baseline/repair data-key mismatches,0canonical. Guard before compute; old stream meanings preserved. Baseline-anchored versioned correction/three-seed label adapter remain engineering work. Existing Experiment1/smoke unaffected.
PRE-ANALYSIS HISTORICAL STATUS (superseded by the closeout/results below): implementation/tests were in progress, with no new scientific result or training yet. Complete record: docs/week7_scientific_amendment_log.md. Student own-voice work remains open. Please review the amendment, exposure disclosure and implementation; do not mistake authorization for certification.
VERIFIED CLOSEOUT: full CPU suite 2,293 passed / 7 expected skips / 0 failed in1,679.75s; XML SHA256 6b8c98295b9fbb8765d088e52d6363e539884a98dca67ba3ffd148f67f92dab8. All2,947old fit-plan rows unchanged; all300units have exactly one model-repair assignment. Current size-only timing refuses to misprice638width512fits. Independent launch/pairing designs now require contemporaneous symbolic anchors for future sweep baselines, qualified repair-procedure identities, original-role reuse and a separate three-seed ordinary-label boundary; these are not yet implemented. The authorized real Experiment1 report follows a clean implementation commit; no retraining is planned.
D-156 NUMBERS: fitcommit f036fe0; analysis ee02542; 150existingfits/30conditions/5groups/5seeds×6sizes; 0newfits/labels/GPU. Disagreement rho[95% paired-seed exact3125 interval]: shape-uniform -.942857[-.942857,-.828571]; shape-sparse -.828571[-1,-.828571]; colour-uniform -.942857[-1,-.828571]; colour-clustered -.828571[-.942857,-.828571]; shape-clustered -.942857[-1,-.828571]. All5meet the amended operational criterion. Diagnostic error all rho=-1, interval[-1,-1]; discrete support, not zero uncertainty; undefined0/31250. Report SHA256 82b0277af9be843e46ff7d5b53020e23f5eab4e7c68101bffe457b8a2e37f44b. Labels/N0/N1/min/ambiguous/undiagnosed/exclusion: not determined; baselines cannot supply counterfactual labels. Full H1 remains W10/repair-informed.
D-156 EVIDENCE/CORRECTION: same-volume independent artifact copy, contentdigest 31ec89a4cd8de4e6842d3f80d2f6d2c8c3c55c424479618b2793271ad4c04d58. First finalization command exited1 by comparing unlike digest payloads after publishing report/figures; preserved correction reverified all150source-copy attestations, found no source change and did not rerun/overwrite analysis. Two PNGs visually checked; all150 figure/report rows exact. AI results draft provided, not student authorship. External certification pending.
=== END UPDATE ===
```

```
=== UPDATE FOR SOL ===
DELTA_ID: 70
PREVIOUS_DELTA_ID: 69
DATE: 2026-08-31
SUBJECT: D-157/DEV-020 — Week-7 exact launch, anchors and registered repair execution.
COVERS SESSIONS: 2026-08-31 (Sol2 Week-7 execution) · Verified launch, anchors and registered repairs
STATUS: implementation in progress, not week completion or certification; all preceding deltas preserved undelivered.
SCHEDULE: six existing E1 validation ladders move W9→W7, exact20seeds; other24units retain3seeds. Rederived474newphysicalfits=90baselines+384repairs,834membertrainings;150oldbaselines preserved,102neededbylabels. No added overall obligations. Complete225-group sweep order fixed bygroupID; onlyfirst3fits+95newExp2A enabled initially. FivehistoricalExp2A fits MUSTbe reused, neverreplacement-trained.
ENGINEERING: beforetrain sweep symbolic/array anchors, firstmetric digest binding andafterfit link; oldfit schemas/keys unchanged. Separate ordinarycanonical9-source labels; legacy20-seed API andD155sweeprepair guard remain. Architecture-aware timing and launch/recovery verification inprogress. Initialtests312pass/1skip plusoverlappingfocusedruns; no newproductionfit/label/GPU yet. Fullcounts/evidence follow inthisdelta anddocs/week7_execution_log.md. Studentownwriting andyourcertification remainopen.
D-158: originalP4.2/10.3 leaves secondarycorrelation details unspecified. Ownerdelegated clarification fixed before diagnosticimplementation: Pearson percondition/perseed on strictbaselinefailures, existingnormalizedarrays, undefinedforconstant/<2points, emptyfailureblocks; no aggregatecorrelation/pvalue/CI/H2decision. Primaryratio unchanged; mean/sampleSDddof1 acrossseeds, no transitionpooling. Postcollection andafterD156 exposure explicitlydisclosed; no newdiagnosticoutcomes consulted. See docs/week7_secondary_diagnostic_spec.md. Tests pending atregistration; noH2orH1rerun.
D-159/DEV-021: real-collector fixtures regenerated some registered>=1000inputpools withfakeGit/untraineddoubles; no trainedstudyfit enteredresults, but inputexposure isdisclosed, noterased orcalled pristineblinding. Subsequentfixtures use a tests-only collector RNG remap1000+i→developmenti, keepingfakemetadataonlyforboundarytests. Productionkeys/seedpolicy/constants/artifactsunchanged. Underownerdelegation retainfixedD157jobs/seeds; no outcome-driven exclusion/replacement/tuning. Detailedscope/correction inledger/worklog; yourreviewpending. Engineering checkpoint585pass/1skip; finalorchestration/fullsuite andrealexecution stillpendingatthisentry.
=== END UPDATE ===
```
```
=== UPDATE FOR SOL ===
DELTA_ID: 71
PREVIOUS_DELTA_ID: 70
DATE: 2026-09-01 · COVERS SESSION: 2026-09-01 (Sol2 Week-8 start) · Exact bounded inventory and pre-analysis specification
SUBJECT: D-160/DEV-022 — owner opens bounded Week8 early; E2A reuse corrected; sign consistency fixed before application; external review deferred.
STATUS: implementation in progress. CPU-only exact scope E2A261fits/441models + E2B125/625 + sweep-0023/15; reserve/other groups/H2 verdict closed. Student Week6/7/8 own-voice work remains open. Full evidence, failures, tests and NUMBERS will be appended here before closeout.
=== END UPDATE ===
```
