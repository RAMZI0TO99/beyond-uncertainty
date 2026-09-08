# → TO SOL
**Paste this file to Sol. It accumulates until delivered (D-008); while NO, append and never replace undelivered blocks.**
**Archive correction (D-120):** deltas1–7 and10–33 are in `PROJECT_STATE_ARCHIVE.md`;8/9 never existed as delivered blocks (DEV-005). Deltas34–55 were replaced without archive and remain only in Git history (`git log -S "DELTA_ID: NN" -- DELTA_TO_SOL.md`). Delta56 onward is archived upon replacement.
**Review base:** Sol-certified `4e55291` (D-131). **Real-repository patch target:** `66edf4a11dce39b91974d5c331cca81424f83b6e` (D-140). Do not apply the patch series directly to the review base.
Delta64 carries the student's provenance-disclosed methodology chapter/progress report and session audit (D-132). Deltas65–80 carry separately owner-authorized implementation under DEV-013…023.
**Send this delta and `SOL_BUNDLE.txt`; generated is not delivered.** Preserve delta70's mandatory companion `docs/week7_sol_closeout.md`.
```bash
EXCLUDE="PROJECT_STATE_ARCHIVE.md" BASE=4e55291 ./scripts/sol_bundle.sh <files changed by the next authorised work> > SOL_BUNDLE.txt
```
---
## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*
> **Delivered to Sol:** ☐ **NO** — DELTA_IDs64–80(D-008). All seventeen preserved blocks remain below. Delta70's mandatory additive closeout is `docs/week7_sol_closeout.md`. Deliver all seventeen and the companion together.
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
> - 2026-09-02 (Sol2 Week-8 recovery) · Outcome-blind E2A interruption recovery
> - 2026-09-02 (Sol2 Week-8 hardening) · Serialized postmortem and pre-import raw authority
> - 2026-09-02 (Sol2 Week-8 recovery) · Externally anchored recovery release gate
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
=== UPDATE FOR SOL ===
DELTA_ID: 68
PREVIOUS_DELTA_ID: 67
DATE: 2026-08-31
SUBJECT: D-153 / DEV-018 — owner continues Week-7 implementation; review deferred.
BUNDLE_FILE: cumulative session_2026-08-30-sol2.patchseries (0001..0016) plus real-repo SOL_BUNDLE.txt.
The owner explicitly asked Sol2 to proceed and said you would review later. This defers review, not certification. Week-6 own-voice prose remains open. NEW: exact source-bound150-fit Experiment-1 adapter; descriptive per-configuration figure preparation; immutable100-fit Exp2A/675-fit sweep baseline preparation. No configuration pooling, H1 verdict, repair assignment, reserve or launch. Five Exp2A baselines overlap the completed smoke: requirements are not new work. Every future execution must reconcile those source-verified fits first. PREPARATION: project-local week7-preparation-2026-08-31/week7_baseline_preparation.json; SHA256 9b380e4bbefa4d3c1c5a52e6ab89f8b63cac42dbfaf90cf5b19419fcc9152044. TESTS: preparation24/0 in34.19s; evidence61/0 in134.39s; figures41/0 in11.30s; old+new figures48/0 in17.79s; state13/0 in0.64s. Full-suite closeout follows. FINAL: 1,798 passed / 7 skipped / 0 failed in1,519.40s. Initial full run1796/7/1 exposed an old outside-repository scratch assumption; real-Git fixture isolation corrected, production unchanged, infrastructure47/1/0. Added real150-source-to-PNG composition1/0 passed and is included in the final full suite. Prior failure retained. DATA: no real Experiment-1 payload, new fit, label, inference or GPU in this increment. Prior deltas remain undelivered and unaltered in substance; delta67 was only reflowed. Please review implementation and the existing unresolved repair/inference choices. Week7 engineering progressed, not whole-week completion; human prose stays open.
=== END UPDATE ===
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
=== UPDATE FOR SOL ===
DELTA_ID: 71
PREVIOUS_DELTA_ID: 70
DATE: 2026-09-01 · COVERS SESSION: 2026-09-01 (Sol2 Week-8 start) · Exact bounded inventory and pre-analysis specification
SUBJECT: D-160/DEV-022 — owner opens bounded Week8 early; E2A reuse corrected; sign consistency fixed before application; external review deferred.
STATUS: implementation in progress. CPU-only exact scope E2A261fits/441models + E2B125/625 + sweep-0023/15; reserve/other groups/H2 verdict closed. Student Week6/7/8 own-voice work remains open. Full evidence, failures, tests and NUMBERS will be appended here before closeout.
=== END UPDATE ===
=== UPDATE FOR SOL ===
DELTA_ID: 72
PREVIOUS_DELTA_ID: 71
DATE: 2026-09-02 · COVERS SESSION: 2026-09-02 (Sol2 Week-8 recovery) · Outcome-blind E2A interruption recovery
SUBJECT: D-161/DEV-023 — one incident-specific E2A recovery after external host termination; no outcome-driven adaptation.
STATUS: Before mutation, epoch001 is frozen at execution4515d516:299 twin events,150starts,149syncs,0failure/sync-pending, one complete local-only job178f4ef3ae1e-s1001 with successful child receipt and an 11/15-file byte-equal interrupted durable partial,111 untouched. Old lease c66ea754/PID48960 remains; no terminal report/launch receipt. D-161 requires committed kernel-backed liveness proof, twin incident/terminal evidence, explicit orphan lease archive, partial quarantine+independent copy, old-source bootstrap, reuse150 and execute only111. Expected recovery counts111executed/150resumed/261synced/523events; any second interruption stops. CPU4/4,batch128,timeout3600,floor8GiB,seeds/jobs/sources/estimands unchanged;GPU0;reserve/real split/other sweeps/H2 closed. Scientific outcomes were not consulted. Implementation/tests and actual recovery hashes/results will be appended before closeout; external review pending.
D-162 ADDENDUM: a live-host implementation probe showed the pinned Windows venv launcher remains as the base interpreter's direct parent. D-162 clarifies, without editing D-161, that only this exact stable launcher/controller pair shares the controller identity: canonical Python/PyPy names, pinned launcher kernel path, strict older-parent creation time, stable PID/path/time/parent relation across both snapshots, and neither frozen old PID. Equality, ambiguity, drift or every other live recognized Python/PyPy process blocks. No scientific value was opened or emitted; external review remains pending.
D-163 ADDENDUM: sandbox-owned worktrees were rejected by host-user Git. Two read-only inspector attempts safely refused with no scientific value or production mutation (reason digests7c2a9d...72b9d and7498e2a...d681e; the latter at historical preflight.py:_verify_environment:146). Recovery now uses only exact per-command/process-local safe.directory for the fixed worktrees; global/repository Git config changes are forbidden, the Git executable remains path/SHA-bound, and the worker rejects any altered/additional GIT_CONFIG_* input. Scientific procedure/counts remain unchanged; successful inspector evidence is pending.
=== END UPDATE ===
=== UPDATE FOR SOL ===
DELTA_ID: 73
PREVIOUS_DELTA_ID: 72
DATE: 2026-09-02 · SUBJECT: D-164 — serialize worker-terminal and lower-complete postmortem sealing.
An adversarial audit found a finalization race if the lower epoch completed but the worker died before its terminal twin. One persistent one-link/non-reparse lock now serializes worker terminal versus controller postmortem publication. Postmortem is allowed only after full lower completion, immutable claim, unchanged empty runtime object, exact current controller and worker death are all re-proved while locked; it never fabricates a worker terminal or resumes an incomplete epoch. Real subprocess/race/link tests were added. Scientific rules/counts/outcomes/GPU remain unchanged; final clean release evidence and external Sol review are pending.
=== END UPDATE ===
=== UPDATE FOR SOL ===
DELTA_ID: 74
PREVIOUS_DELTA_ID: 73
DATE: 2026-09-02 · SUBJECT: D-165 — standard-library pre-import raw authority for the one-use recovery.
Recovery now enters only through the absolute committed script under pinned Python `-S -s -P`, exactly six startup PYTHON variables and no PYTHONPATH. Before project import, a separately hash-pinned helper (`69b7771d...e46d6`) binds both Python executables, Git and both exact worktrees via raw plumbing plus two filesystem/byte inventories; untracked/ignored/link/unstable content refuses. Native Windows environment-block reads catch mis-cased controls despite `os.environ` normalization. Gate is command-bound and controller/worker revalidate it, the worker before claim. No production mutation or scientific value occurred; final matrices, clean commit, inspector and execution results will be appended here before closeout. External Sol remains certifier; “Sol2” is only the owner's active collaborator label.
=== END UPDATE ===
=== UPDATE FOR SOL ===
DELTA_ID: 75
PREVIOUS_DELTA_ID: 74
DATE: 2026-09-02 · SUBJECT: D-166 — externally anchored release, retained execution bytes and verified nested fit children.
Pre-production audits found five remaining D-165 gaps: direct script launch, controller commit learned inside its own authority, released file paths after inventory, historical native multiprocessing/pickle at each fit, and direct post-recovery E2A commands. D-166 closes them before any accepted recovery record. Every status/adjudicate/recover/seal/monitor/finalize/report/figures call now uses an externally hash-checked outer `-c` literal (35758e8e...), hard-coded entrypoint hash (146d306d...), helper hash (cf4727d6...), final controller commit and cleared environment. Raw authority retains read handles for all controller/execution/Git/site files, executes captured project/site Python bytes through verified importers, and checks native origins against the locked inventory. Each new fit starts pinned `-S -s -P -c`, receives only canonical captured child/helper bytes, repeats static authority, bypasses native spawn and pickle serialization, calls the frozen old `_fit_worker`, and returns the old protocol through one atomic no-overwrite file. Fixed nested literal hash is 95584458...250e73. Current working checks: 211 green before one stale inspector fixture; corrected inspector/raw tail 49 pass/2 expected skips; delegated nested suite 24/24, with two exact-environment/canonical-invocation cases added afterward. Final clean combined tests, commit, release receipt and independent inspector are still required. Production remains 299events/150starts/149syncs/111untouched; no recovery mutation, scientific value or GPU use. Trust residuals: pinned CPython/Windows/native DLL base and no claim against a concurrent same-user attacker; run is quiescent/fail-closed. External review remains pending; Sol2 is implementer, not certifier.
=== END UPDATE ===
=== UPDATE FOR SOL ===
DELTA_ID: 76
PREVIOUS_DELTA_ID: 75
DATE: 2026-09-02 · SUBJECT: D-167 — native startup closure, exact Git and two-process nested ownership.
Three independent pre-production audits stopped D-166. D-167 introduced the fixed inbox Windows PowerShell 5.1 trust root, external stage/receipt ceremony, exact pyvenv plus complete base-runtime/venv-Scripts inventories retained through child exit, empty native cwd/temp, raw/gate schema3 startup proof, exact absolute runrecord Git, and launcher/base-interpreter retained-handle ownership with startup acknowledgement. Working focused matrices were native4/1skip, stage8, receipt20/1skip, nested54, worker113, controller74, inspector15, postmortem49/3skip and raw34/2skip. Production stayed299events/150starts/149syncs/111untouched; no scientific value, mutation or GPU. Final combined gate/commit/release/status remained pending. D-168 below supersedes only the six newly audited mechanics.
=== END UPDATE ===
=== UPDATE FOR SOL ===
DELTA_ID: 77
PREVIOUS_DELTA_ID: 76
DATE: 2026-09-02 · SUBJECT: D-168 — fixed stage root, isolated Python and one-use historical fits.
Two further independent audits found six P1s before production: inherited CLR profiling controls before PowerShell; non-isolated CPython startup; mutable executable stage record/downstream-unbound stage bytes; reuse of one one-shot fit context across111 attempts; historical bare git_state/core.fsmonitor; and possible surviving base interpreter on pre-ack refusal. Fixes are one release-independent compressed stage source, sole canonical envelope, absolute cmd /d exact10-row environment, receipt V2 binding source/encoded/environment policy, non-executable audit record, aggregate stage0 binding, raw/gate schema4, exact `-I -S -B -X utf8 -c`, no trusted PYTHON environment, fresh context per fit, raw-authority GitState adapter, and retained launcher/base-child cleanup proof. Integration additionally found/fixed ordinal stage-policy ordering.
VERIFICATION: both final audits found no P0. Their only two P1s were the deliberately deferred raw/outer pins; all five consumers now bind raw `dd40628b...137d` and outer `52a4d90f...840e`. The startup-audit runbook P2 was corrected. The process audit's one non-blocking dynamic-alias P2 was also closed with exact inventory/rebinding refusal and three direct tests. Final working-copy partitions are stage/receipt/native/raw86pass/3capability-skips, worker/nested/controller/inspector277/0, entrypoint47/0 and neighboring regression320pass/5capability-skips. JUnit hashes are e2b8b815...c8734,7990ea32...456,fbde9658...02d4 and409217a5...8d1a. Final exact-tree full gate, residue relocation, clean commit, receipt/stage records and read-only status remain pending at this entry. Production remains exactly frozen; CPU-only tests, GPU0, no scientific values. D-161 counts and procedure unchanged. External Sol remains reviewer/certifier; Sol2 is implementer.
=== END UPDATE ===
=== UPDATE FOR SOL ===
DELTA_ID: 78
PREVIOUS_DELTA_ID: 77
DATE: 2026-09-05 · SUBJECT: Owner-authorized continuation and verified exact-path restoration.
COVERS SESSIONS: 2026-09-05 (Sol2 resumed workspace) · Verified restoration and recovery release preparation
The old executable project directories were absent after collection/relocation. Python/Git executable hashes still match D-168. Under explicit filesystem approvals, one verified duplicate test-scratch copy was removed (the collection twin remains), the standalone main repository was moved back, and54Week6–8entries were copied to their original absolute paths. Source/experimental bytes were checked against the existing collection manifest; no evidence path, seed, constant, source commit or scientific result was rewritten.
NUMBERS (operational only): collection55,924files/875,262,380bytes verified; duplicate327,644files/2,692,163,477logical bytes verified; restored55921files/874729672bytes verified. Production commands/newfits/GPU/scientific-value consultation=0 during restoration.
The exact-tree full recovery gate, clean release commit, V2 receipt/stage records and independent status remain required before the single D-161 continuation. External Sol review, student prose and all existing scientific scope limits remain open/unchanged. Operational receipts live at D:/Aenv/pro2/resume-2026-09-05.
=== END UPDATE ===
=== UPDATE FOR SOL ===
DELTA_ID: 79
PREVIOUS_DELTA_ID: 78
DATE: 2026-09-06 · SUBJECT: Complete implementation QA and exact pinned-runtime restoration.
COVERS SESSIONS: 2026-09-06 (Sol2 recovery release) · Full QA and pinned-runtime restoration
NUMBERS (operational only): 5193 passed, 18 expected skips, 51 passing subtests; 5,211 distinct collected nodes, zero remaining failures/errors. Candidate-manifest SHA256=cb103e0b92d91b9873f0989c570308c9bdf5c421cc5a5daf20c5d2e171948090; combined JUnit SHA256=4d4eea58e7987dc9d7e277c74c70c7e2148b8afd0e76958720a2611ab5193f97. Source stayed unchanged across all runs.
DISCLOSURE: batch08 attempt001 stopped before terminal publication with four timing-fixture setup errors; four nodes were routed to repository-local scratch. Batch09 had257pass/4skip/1native-startup failure. The installed base runtime differed by one4413-byte json.tool cache datedSept3; excluding it reproduced frozen hash0a5aff918e4a46fae2427a593261f8e3640ba439ba4ffebf5081b15eb7df6760 exactly. Approved quarantine preserved the file, changed no Python source/dependency/pin, and the targeted startup smoke passed1/1. The combined report records the original nonzero run and the exact passing replacement case; original XML is untouched. Batch03 wall time includes overnight Windows suspension.
No production command/new fit/GPU/scientific-value consultation occurred. The documentation-only governance check, clean commit, V2 receipt/stage records and independent status remain before the one-use recovery. Epoch001 remains150complete/149durable/111untouched; scientific limits, external Sol review and student prose remain unchanged. Full receipts are at D:/Aenv/pro2/resume-2026-09-05.
=== END UPDATE ===
=== UPDATE FOR SOL ===
DELTA_ID: 80
PREVIOUS_DELTA_ID: 79
DATE: 2026-09-08 · SUBJECT: D-169 — first release startup refusal and controller contract correction.
COVERS SESSIONS: 2026-09-08 (Sol2 controller contract correction) · First release refusal and verified correction
Release50251fb3cc63479677c2e19fc242cb6d809c9d05 passed its5211-node gate; first V2 receipt6a1fb77e...76b2d and stage audit remain immutable. Independent status refused before mutation with error92746c99...0323: controller Python path/environment is not exact. D-168 clears Python startup variables, but the controller still expected six legacy names besides the entrypoint's post-admission PYTHONPATH. A real isolated-entrypoint contract replay reproduced the exact refusal, then passed with seven extra-variable rejection cases after the minimal controller correction. Flags, executable/runtime pins, admitted paths, scientific rules and frozen fitting source are unchanged.
Owner-requested quota pause stopped batch07attempt001 onSeptember6; it remains preserved and contributes no gate coverage. September8 continuation verifies the same candidate and uses batch07attempt002. NUMBERS (operational only): focused8/8; new full gate 5200 passed, 18 expected skips, 51 passing subtests; 5,218 distinct nodes, zero remaining failures/errors; JUnit SHA256=ade0273e0dda2436a2705fa8552daafb86c4a6e9fefb7f4556b4f023cbb290b0. First release/refusal and red regression are preserved separately. No recovery/lease mutation/new fit/GPU/scientific-value consultation. New clean release, attempt002 receipt/stage audit and independent status remain before D-161's unconsumed sole recovery. External Sol review and student prose remain open.
QA environment history: batch09's one native-startup failure cleared after preserving25 extra base-runtime bytecode caches and restoring the original whole-runtime pin; its exact one-node rerun passed. Batch10attempt001 had22 fixture failures because the required-empty stage0 runtime held two DesktopCentral logs from the first status period. Both logs were preserved byte-identically, the same runtime parent was emptied, and batch10attempt002 passed284/3skip on unchanged source. All original reports remain; reconciliation explicitly discloses these replacements. Approved relocation of77,616 retired first-release QA files to C:/Aenv/beyond-uncertainty-retired-qa-2026-09-08 preserved every hash and restored D: headroom; production/current-candidate/interrupted QA evidence was untouched.
=== END UPDATE ===

```
