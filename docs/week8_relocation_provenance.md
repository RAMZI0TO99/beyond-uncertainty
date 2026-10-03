# Week8 relocation provenance — implementation checkpoint, 2026-09-19

The owner authorized the relocation amendment after the recorded304-pair
filesystem-identity mismatch was disclosed. Work must remain local: no push,
publication, deployment or external communication. This is not Sol certification.

Current implementation at23:35UTC: bounded metadata readers are wired into the
parent, inspector, worker and fit child through captured helper admission. Parent
final validation now proves the original and relocated epochs separately. These
changes remain an uncommitted candidate, with focused current/frozen-import QA.
Downstream label provenance and additive D-171/deviation/delta82 documentation
are implemented. A fresh complete gate and clean local release remain before
native status or recovery.
Read the latest root handoff and autonomous-2026-09-19-185105/SESSION.md. No prior
gate certifies this changed code; production recovery has not started.

## What the verifier establishes

`src/bu/experiments/week8_relocation_provenance.py` verifies a separately pinned
record against a caller-supplied fixed policy. It does not import the production
controller, mutate evidence, authorize recovery or substitute historical digests.
Original logical paths and copy digests remain separate from physical locations
and newly observed digests. All original evidence bytes remain unchanged.

Two observations must agree on file hashes, device/inode identities and metadata.
File paths and handles are checked before/after reads; directory entries are
checked for motion. Overlapping or escaping mappings, aliases, hardlinks, reparse
points, changed or extra/missing files, unregistered empty directories and changed
control documents refuse. The expected record hash and expected mapping must come
from outside the untrusted record. Canonical-byte equality rejects unknown or
duplicate JSON keys and incomplete records. This is not a filesystem lock: the
production consumer must still revalidate under its liveness/transition rules.

Windows host observation: isolated CPython3.13.5 exposes different `ctime` values
through `lstat` and `fstat` on some unchanged files. Cross-API comparison uses
device/inode, size, mtime, birthtime, link count and mode. Full metadata including
ctime is compared within each API before/after reading; no motion check is removed.

## Initial evidence record (preserved)

Under `D:/Aenv/pro2/resume-2026-09-05/relocation-bindings/attestation-001`:

- Independently materialized `original/relocation.json` and `copy/relocation.json`.
- Record SHA256: `916af968a234c69e74474ba37caef303f5066bb4bcffe10e409a2df6525f48a3`.
- Policy SHA256: `9644b007b8414e2f802917a4d25fa2e94996ab5ca22bd8d46ffa65651835bbaf`.
- 304 pairs:155 earlier reusable source pairs and149 synced epoch001 pairs;
  9700 evidence files,617 control documents. All content hashes match. None of the
  304 original copy-identity digests is reproduced. All299 event digests and their
  chain were recomputed and checked against the frozen aggregate and tail hashes.
- Policy was derived from the pinned original ledger/events, not copied from
  the earlier audits. All304 current pair digests independently agree with those
  earlier audits. Original documents and the frozen fitting checkout were not edited.

Expanded attestation002 is in the autonomous session directory. It retains304pairs
and9700files and binds629documents, adding original authority records, contexts and
canaries. Record SHA256:`dd3f546bfa05c4df1cef653fc2ea7e3602cb50ad5506775286d50b79b6f6d187`.
Policy SHA256:`a25fa279a5ccce335ac04b31ecba209c38f2fa77a3f67db14356e228348095dc`.
The metadata loader pins these independently and does not regenerate them.

The operational lease namespace was restored from the preserved collection at
19:18UTC:6files/1049bytes, all hashes matching and archive unchanged. Original
lease ownership/bytes remain intact; no transition or release occurred. The
control-restoration-001 receipt is in the autonomous session directory. Native
liveness and D-161 transition remain required. The original worker's erroneous
schema1 lease check was corrected to exact integer2, matching frozen4515 and the
preserved lease; see LEASE_SCHEMA_FINDING.md and lease-schema-001 QA.

## Explicit metadata adapters

`scripts/week8_relocation_metadata.py` is stdlib-only and has no CLI. It is designed
to load as a verified non-bu helper in historical processes. Original JSON remains
unchanged. New schema2 checkpoints carry current physical paths and an explicit
link to the old checkpoint/context and manifest, with a separate context filename.
An existing/partial new publication or third checkpoint refuses; no automatic
healing or replay. Genuine active/released lease checks remain required.

New baseline bindings distinguish current observations from original source-ledger
or epoch001 rows, or identify a genuinely new-epoch baseline. Old completed-fit
results keep their original context and binding. Historical classification comes
from the pinned file inventory, not the checkpoint a mutable result claims. The
membership API alone is not current verification: registered files must still
pass historical_file_at. The one unpaired orphan remains an explicitly fixed
feature repair, subject to the original inspector/parent/supervisor checks.
Scientific fitting, source-pair and repair-pair validators remain unchanged.

EventReaders now validates the pinned299-event prefix and one separately admitted
new-context tail. It rejects missing/extra/temp/gapped twins without healing,
duplicates/retries and events after terminal state. ReuseReader returns resumed
for the149attested synced jobs after original/current provenance reconciliation,
without recopying or appending events. Orphan/new jobs retain the original lower
supervisor path. Frozen-import tests proved orphan sync without another attempt,
new-job fixedworker identity, success/failure, and no automatic retry.

ControlReaders reads the exact original prepare/preflight/launch-control receipts
with explicit historical/current paths. Monitor-only checkpoint/event validation
opens no fit evidence or environment validator. The full branch reopens310copies;
later new receipts delegate to the original current-path reader. Frozen fixed-root
name/resource/overlap guards remain active via an explicit registered-root binding.

ReleasedInventoryReader returns truthful current source rows, unchanged original
ledger, and separate relocation/source_provenance fields. It distinguishes155old
ledger sources, preserved epoch001pairs, the unpaired original orphan after a real
new copy, and actual new-epoch fits. Active leases and incomplete pairs refuse.
Downstream labels now use the parent's independently reopened released inventory
and retain the original scientific pair verification for every current row.

Latest focused receipts: frozen-events-0013passed; frozen-events-00216passed;
frozen-controls-0024passed; frozen-controls-inventory-0019passed. Every wrapper
proved source unchanged and frozen4515clean, with importedbu path/SHA receipts.
frozen-controls-001 stopped during synthetic fixture construction because the
original immutable writer refused overwrite; the fixture was corrected, never
the immutable production writer. These focused runs are not a full release gate.

## Remaining production integration

Captured helper loading is implemented in raw authority using the existing
VerifiedSourceLoader, two fixed non-bu names and captured controller bytes/blob
bindings. Live module/class/function/loader/policy validation detects tampering;
occupied module names or repeated loading refuse. Inspector candidate now installs
the metadata readers inside verified historical Git scope and verifies restoration.
Its version2 receipt binds helpers/attestation and separately records historical
and current pair identities. Focused helper19, inspector/Git34, parent refusal17
and frozen inspector scope2 checks passed in their recorded revisions.

Parent initial receipt parsing and independent relocation accounting are now
implemented. Its admitted helper scope restores readers on success/refusal,
compares the inspector binding with its own admission, and reopens each preserved
pair before/after independent tree and current-copy hashing. Inventory schema2
records both historical/current identities and its own relocation binding.
The parent final two-epoch checkpoint/event/tree validation is implemented below.
Worker admission/scopes and inventory schema2 are now implemented. Admission
loads its own captured helpers/evidence before the exclusive claim; the original
frozen launcher runs inside source/preflight/checkpoint/completed/event/reuse
scopes and the existing verified Git/supervisor/no-pickle boundaries.
The incident publisher now captures controller_process and validates the full
incident before immutable publication. Both parent and worker consume the same
record; altered process and relocation evidence refuse. Fit-child invocation3 now
includes the worker's own relocation binding and its fully validated transition
file binding, both covered by the native startup acknowledgment. Child admission
reopens its own fixed attestation and compares the binding, then installs source,
preflight, checkpoint, completed-job and exact orphan-history readers around the
unchanged callback/payload. The orphan reader verifies fixed transition twins,
original archived lease bytes and distinct active ownership, and forbids ordinary
release for the original token. Parent released-history calls use the existing
full transition validator through a scoped exact-token bridge.
Downstream label equality and parent final validation are implemented and covered
by the focused checks recorded below.
Do not invoke production status or recovery from this intermediate candidate.

Parent focused QA:parent-relocation-0015passed before a synthetic empty-document
policy fixture error;00211passed before a fixture shared its trusted/untrusted
binding; both fixture defects corrected without changing production guards.
003105passed before an existing synthetic child-profile startup timed out at30s.
Fresh unchanged parent-profile-0013passed5.43s; no project Python remained after
the timeout. parent-incident-0015passed3.86s. All candidate inventories unchanged
during QA; failed receipts remain preserved. Counts overlap and are not a fullgate.

Worker integration QA:worker-relocation-001152passed32.20s, including actual
parent publication consumed by both validators; frozen-worker-scope-0012passed
50.08s against unchanged4515imports; parent-process-contract-001100passed36.65s.
All wrappers sourceunchanged/exit0. No production launcher was invoked.

Child integration QA:child-transition-00143passed before a synthetic native-spawn
fixture lacked a metadata-scope double; corrected that fixture only. Fresh002
212passed59.26s. frozen-child-history-00122passed83.72s with genuine4515bu imports
and source/hash receipts. helper-child-reader-00119passed48.82s proves the expanded
helper still loads from captured bytes and its bindings remain guarded. All source
inventories unchanged. These focused gates do not certify a complete release.

Parent final QA:parent-final-002141passed515.70s before the existing child-profile
startup test timed out at30s. Fresh unchanged parent-final-profile-0013passed5.42s;
no project Python remained. Failed output is preserved. parent-final-001 was only
a runner argument rejection before test invocation (unsupported -k), no coverage.
parent-jobs-00110passed223.32s with real small261jobtrees and149pair attestations.
All running-test candidate inventories remained unchanged. These are focused
checks, not a complete gate. Tests cover distinct contexts, resealed scientific
setting/relocation substitution, original-byte drift, extra checkpoint, active or
changed released lease, duplicate starts, historical/current identity swaps and
the orphan/new-copy boundary. No production evidence was used in these fixtures.

Parent _checkpoint_documents now independently proves original schema1 metadata
and new schema2 cloned scientific settings under a normally released lease. The
original context stays immutable beside the separate relocated context. Initial
monitoring retains its single-old-checkpoint guard. _final_events uses the exact
old299/new224 contexts and original schema/seal primitive, retaining261starts,
261syncs,1completion,150old/111newstarts and original prefix/tail pins. Final jobs
reopen the149attested pairs and retain both identity digests; orphan+111new copies
must match current event identities. All150oldtrees and result/receipt bindings
remain checked. Parent reader admission owns the installed reader instances.

The implemented boundaries retain these separate historical/current identities:

1. Raw authority, controller entrypoint and child bundles: bind the relocation
   record/policy and approved reader implementation to the exact clean release.
2. Controller `_validate_initial_controls` and inspector `_validate_control`:
   validate original bytes and seals before interpreting relocated locations;
   preserve original checkpoint, event and source-ledger identities.
3. Frozen-source metadata readers: `P._load_receipt`, `P._load_control`,
   `Launch._read_start`, preflight/source-ledger readers and `_baseline` reopen or
   compare old absolute paths. Use explicit bounded evidence-access interfaces;
   do not replace `Path` globally, rewrite source text, normalize original JSON
   before verification, or represent an old digest as a current observation.
4. Historical reuse: inspector `_inspect_jobs`, controller
   `_capture_outcome_blind_inventory`/`_validate_final_job_trees` and lower
   reconciliation compare identity digests. Only the exact304 recorded pairs may
   use the new historical-to-current attestation. New copies continue to require
   newly observed exact identity digests; no general fallback is permitted.
5. Worker/fit-child: preserve4515 scientific fitting bytes and verified spawn
   authority. Adapt only approved metadata access. Scope adapters to verified
   calls, validate their installation/restoration and bind the attestation in
   every resulting recovery record. Captured helper scopes and the fit child's
   verified D-161 orphan-history lookup bridge are implemented, pending fullgate.
6. Lease handling: retain the restored namespace and immutable archive without
   silently manufacturing a normal old release. Preserve D-161's kernel-liveness
   and stable transition lock.

Before production: a fresh complete gate, clean local release, new
immutable native status and exact liveness/count checks. Preserve150reuse,
111execute,261sync,CPU4/4,batch128,3600seconds,8GiB floor,one recovery and no retry.
Prior partial/full gates do not certify this changed candidate. All failed QA
attempts remain preserved. No production recovery or scientific fit has started.

Label integration: the parent independently reopens the complete released
inventory through its own admitted readers and compares checkpoint/ledger/commit
pins, physical roots, every current source and its historical provenance. Unknown,
missing, duplicated or altered origins refuse. The finalizer retains its original
pair checks and416/384/32 obligation partition. labels-provenance-002 passed78
tests in1348.55s, including original label and entrypoint suites; the earlier001
fixture shared its origin with the trusted ledger and was corrected in the test
only. All raw-helper consumers now pin SHA256
20a9be7eb663c8431f975dd0de3c822817e31a3b07001221ee0b6de5973483e3.

The synthetic profile routing test now allows120s instead of30s after two
30s failures passed immediately in fresh isolated runs. This is not a production
timeout change or a claim about the cause of host delays. release-docs-profile-001
passed17 tests in5.63s:13 governance,3 profile routing,1 runbook. Source inventories
were unchanged during both successful runs. Fresh complete release QA remains
pending; these focused checks do not certify production readiness.


## 2026-09-20 QA runtime correction and native-copy investigation

Fresh collection contained5555nodes. Gate001 accepted governance13, batch01
401pass/4host-capability skips and batch02539pass, with unchanged candidate bytes.
Batch03 terminated with Windows0xc00000fd during a synthetic fixture's
shutil.copy2/CopyFile2 call. Its252progress markers have no terminal JUnit and
are not accepted coverage. All failed output remains. The attempted driver-stop
command found the driver already gone and did not terminate any process.

A separate full runtime audit found90changed standard-library pyc files, with
no added/missing files or changes in Scripts/Git/site. The critic-balance
cross-process test replaced its environment and omitted-B, dropping inherited
no-bytecode protection. It now passes-B explicitly without changing its seed
comparison or assertions. Changed caches were preserved and exact originals
restored; no cache was regenerated as authority and no runtime pin changed.
runtime-release-002 independently verified allfour trees twice against their
reviewed inventories and the29declared venv relocation edits. The original
shared C: installation was read only. Post-focused checks also prove all5368
base files remain exact. Frozen4515science and all production evidence unchanged.

Focused qa-environment-repair-001 reproduced the native fault after101markers;
no complete focused result is claimed. Two fresh identical122-node selections
then passed:002 with a diagnostic project-local LOCALAPPDATA in492.78s,003 with
the original C:user profile in401.43s; both candidate inventories unchanged.
Thus the evidence does not establish a profile cause or justify changing the
production profile/copy implementation. The native failure remains intermittent.
Windows crash metadata identifies KERNELBASE; both captured stacks contain
thousands of repeated addresses in ManageEngine Endpoint DLP's injected library.
This is strong diagnostic evidence, not a symbolized/unwound stack or proof of
root-cause elimination. No security software was disabled, patched or removed.
Two independent synthetic copy probes each verified100copies/27200files with
unchanged sources, with and without CPU4/4 PyTorch; they are not release gates.

Eight dumps were proved to belong to project processes and moved from C: into
autonomous-2026-09-19-185105/crash-dumps-001 and002 with every hash verified.
Diagnostics and all receipts remain private. Active runbook stage0 literals now
match the relocated policy; historical records keep their original values.
Clarification to D-171's preceding wording: the production child's explicit
LOCALAPPDATA is C:/Users/aladdin-alyanai/AppData/Local, outside its execution
tree; it was not moved into the project. Diagnostic002's profile was temporary.

Fresh complete exact-candidate gate002, final governance, clean local release,
immutable attempt005 native status and all original liveness/count guards remain
required. No status005,adjudication,ownershiptransition,recovery,newfit,outcome
consultation or public action has occurred. D-161 remains exactly one recovery.


## 2026-09-20 complete relocation gate and preserved failure history

Fresh fullgate002 reconciled all22partitions: 5536 passed, 19 expected skips, 51 passing subtests; 5,555 unique nodes, zero remaining failures/errors. Combined JUnit SHA256=a26ce16652ce08271a06ac334d2613d445a6c549a2f4cfee13cf36e0369360d2. The failed batch09attempt001 (163pass/1child-exit timeout) contributes no gate coverage; diagnostic15pass/2hostskips is separate, and fresh262-node batch09attempt002 passed258/4hostskips on the unchanged candidate. The timeout cause remains unproved. The first continuation helper stopped before QA because LF/CRLF manifest serialization differed; all263rows were identical, and continuation002 corrected only that orchestration comparison. All failed/diagnostic attempts remain preserved. Final documentation governance, fresh runtime verification, clean local commit and immutable native attempt005 status/counts/liveness remain before the unconsumed sole recovery. No production fit, adjudication, ownership transition, outcome consultation, GPU or public action; external Sol review/student prose remain open.

Gate receipts: resume-2026-09-05/autonomous-2026-09-19-185105/full-gate-002/release-verification.json and release-junit.xml; individual immutable reports are under resume-2026-09-05/qa-relocation. Every accepted partition matches candidate manifest 08651ad1dece659f29cc128886613040ee301aac0e1b01a865db43a09470644a. Gate001 and the earlier native-copy diagnostic crash remain disclosed above; green QA does not establish elimination of the injected-library/native-copy intermittence. Production profile, security software, frozen4515science, evidence and scientific rules are unchanged. Only seven documentation files change after this gate; their before/after bytes are preserved in docs-final-gate002-001 outside the controller. Separate final governance/runtime/commit receipts must establish each subsequent milestone; this document does not claim them.
