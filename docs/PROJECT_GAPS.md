# Project gaps and remaining work

Assessment date: **October 17, 2026**. Project: **Beyond Uncertainty**.

This assessment answers three questions: what is unfinished, what the saved evidence actually proves, and what would close each gap. It covers engineering, operational qualification, scientific results, statistical limitations and reproducibility. It is a dated assessment, not a replacement for the controlling decisions or an execution authorization.

The reviewed baseline is documentation commit `c57dc4b928046f05595aec98bd409bd468e4c939`, I10 implementation commit `75acc5101bedf18734add168523cd87384611147`, and I9 implementation commit `471105e8f77e8e8e06ccb54fb84d0821267e4213`. Current navigation starts at [HANDOFF](../HANDOFF.md), [CONTINUE](../CONTINUE.md), and [AGENTS](../AGENTS.md). Scientific interpretation follows the claim-specific correction index and controlling entries in [DECISIONS](../DECISIONS.md).

The assessment used read-only inspection of saved reports, contracts, Sources and research records. No original project program, fixture, Native8 measurement, Parser workflow, runtime ceremony, recovery or scientific experiment was executed for this document. The authoritative thesis-plan and schedule DOCX files were not re-audited here; this is not a new complete methodology review or independent statistical reanalysis.

## 1. Overall assessment

**The project is missing more than final results.** There are substantial implementation and integration gaps between individually reviewed components, missing evidence from a real current-family workflow, unfinished scientific analyses, and an existing statistical-power limitation. Successful component tests are meaningful progress, but they do not establish that the complete research pipeline works.

The evidence does **not** establish that the entire plan is invalid or that the project must be restarted. Several important safeguards and components work within their tested scopes. The immediate engineering priority is to qualify the producer interface and its real caller, then demonstrate a bounded workflow through the relevant physical and consumer checks. The scientific priority is to complete the permitted research obligations, real label-to-critic data path and final inference while preserving the already accepted design limitations.

Five distinctions matter throughout this document:

1. **Source review** accepts exact program bytes or contracts. It does not show those programs ran successfully.
2. **Synthetic or extracted-function tests** establish the exercised cases. They do not establish complete-program behavior or physical operating-system effects.
3. **Physical IO tests** can establish real file behavior for their owned synthetic payloads. They do not automatically qualify the genuine selected family or its Native8/Parser dependencies.
4. **An accepted runtime workflow** would establish that workflow's operation. Scientific claims still require the intended data, labels, analysis and uncertainty reporting.
5. **A scientifically valid outcome can be negative or inconclusive.** Completion does not require every hypothesis to be supported.

The dated Source inventory is **36 of 45 selected paths: 35 successors and one carried composer**. Nine roles remain pending. This is a file inventory, not an 80% project-completion estimate. Frozen STEP080 remains **35/45**, with ten pending roles; no STEP081 is declared. Later evidence does not automatically change the frozen restore snapshot.

## 2. Terms and evidence already available

The implementation reports use several specialized terms:

| Term | Meaning in this assessment |
| --- | --- |
| Source | Exact reviewed program text, often stored with an inert `.source` suffix. |
| Canonical publication | Creating the accepted files and records at the selected final paths, with authenticated provenance. |
| Receipt ABI | The exact fields, types, identities and relationships a producer emits and a consumer accepts. |
| Owner/lease/purpose admission | Checks that the actual actor, current interval and exact requested action are authorized under the preserved rules. |
| M3 recorded semantics | Checks joining saved facts, receipts, complete rendered bytes, predecessor inverses and diffs. |
| Native8 | Physical native measurement of the selected eight phase Source subjects; not eight generic unit tests. |
| Native10 / Python PATH9 / descriptor9 | The complete protected native metadata vector and two independent Python metadata vectors. |
| Parser | The owned PowerShell parent/child workflow that performs four required `ParseFile` calls and records results and cleanup. |
| FIT in continuation records | Source/data byte assembly. It does not mean scientific model training or accuracy. |
| Root adoption | A separate recorded acceptance of the exact evidence and its stated limits. |

The existing achievements below should be preserved. None of their counts should be added together into a single coverage or project-readiness score.

| Component | Accepted evidence | Boundary that remains |
| --- | --- | --- |
| I0 owner-support validator | 17 passing in-memory test methods. | Not actual I1 lease issuance or a live owner/clock workflow. |
| I1 lease helper | Reviewed Source. | Full helper and actual native timestamp entry remain unrun. |
| I2 family producer | Reviewed Source; I10 later repairs its phase basename predicate. | Complete producer, external canonical receipt ABI and consumer integration remain unqualified. |
| I3 Native8 helper/wrapper | Reviewed owner-context port with protected functions and eight-subject loop preserved. | No accepted current-family Native8 run. |
| I4 Parser parent/child | Reviewed Sources preserving 47 IO spans and both complete mains. | Current Sources remain unrun; no current composed Parser result. |
| I5 generic/phase-peer interfaces | Reviewed held context ports preserving original dependency checks. | Final producer/result bindings and downstream execution remain held. |
| I6 publication adapter | 55/55 first-run synthetic memory cases. | Reads no measured Source bodies; no real family publication, Native8 or Parser qualification. |
| I7 publisher IO | 54/54 owned-file cases on real Windows files with synthetic payloads, including scoped fault branches. | Genuine-family entry and public caller composition remain held. |
| I8 prewrite admission | Accepted 97/97 run in its third scoped suite; both earlier failed suites retained. | Metadata owner/lease/publication-purpose checks do not supply the missing real caller or M3 semantics by themselves. |
| I9 recorded M3 semantics | Accepted 98/98 synthetic memory cases. | No physical stability, original-check execution or real publication proof. |
| I10 phase naming | 134/134 cases in one scoped pure AST run. | Only `need` and `require_phase_successor_basename` executed; whole I2, selection, renderers and CLI did not. |
| STEP080 portability | Saved clone/restore qualification of its dated frozen bytes. | Does not reproduce native filesystem identities, current later Sources, execution authority or scientific results. |

Evidence: [I0/I1](development/native-owner-implementation/20261015-i0-i1/I0_I1_IMPLEMENTATION.md), [I2](development/native-family-implementation/20261015-i2/I2_FAMILY_IMPLEMENTATION.md), [I3](development/native-measurement-implementation/20261015-i3/I3_NATIVE_IMPLEMENTATION.md), [I4](development/native-parser-implementation/20261015-i4/I4_PARSER_IMPLEMENTATION.md), [I5](development/native-interface-implementation/20261015-i5/I5_INTERFACE_IMPLEMENTATION.md), [I6](development/native-publication-adapter/20261015-i6/I6_PUBLICATION_METADATA_ADAPTER.md), [I7](development/native-publisher-implementation/20261015-i7/I7_HELD_PUBLISHER_IO_IMPLEMENTATION.md), [I8](development/native-publisher-admission/20261015-i8/I8_PREWRITE_OWNER_LEASE_PURPOSE.md), [I9](development/native-m3-prewrite/20261017-i9/I9_RECORDED_M3_SEMANTICS.md), [I10](development/native-producer-qualification/20261017-i10/I10_PHASE_BASENAME_QUALIFICATION.md), [clone qualification](development/portability/STEP080/GITHUB_CLONE_QUALIFICATION.md).

## 3. Gap register

Status labels distinguish **unfinished implementation**, **missing qualification**, **observed refusal**, **accepted limitation**, and **engineering judgment**. An observed refusal does not by itself identify a root cause. Missing qualification does not mean every underlying implementation is defective.

Priorities describe dependency order, not a measured severity score: **P1** is the immediate engineering path, **P2** is subsequent operational integration, **R** is required research completion or interpretation, and **S** is supporting assurance/process work. Some R/S preparation can proceed independently when permitted; real execution still needs its own prerequisites.

| ID | Gap | Classification | Priority | Concrete closure artifact |
| --- | --- | --- | --- | --- |
| G01 | I2 external canonical receipt ABI | Unfinished implementation/qualification | P1 | Reviewed producer successor and accepted complete-producer output checks. |
| G02 | Actual I8 + I9 + I7 caller composition | Unfinished integration | P1 | Reviewed caller binding and scoped positive/refusal results at the real write boundary. |
| G03 | Staged bootstrap and publication chronology | Unqualified composition | P1 | Acyclic stage plan and actual correctly ordered publication/witness/reconciliation records. |
| G04 | Current owner, lease and host bindings | Missing operational qualification | P1/P2 | Genuine current action-specific admission and actual actor/clock/resource evidence. |
| G05 | Native8 input/result carrier | Unfinished integration | P1/P2 | Reviewed compatible carrier and adopted genuine finite-eight support result. |
| G06 | Native physical stability | Observed refusals; cause unresolved | P2 | Fresh admitted measurement preserving every original comparison, with saved vectors/outcomes. |
| G07 | Current Parser workflow | Missing physical/runtime qualification | P2 | Accepted four-subject parsing result, owned-process evidence and cleanup. |
| G08 | Parser saved-result adapter | Unfinished implementation | P1/P2 | Reachable version2 envelope adapter and independently adopted saved output. |
| G09 | Downstream phase-peer/binding/configuration | Unfinished integration | P2 | Authenticated current consumer joins and accepted downstream outcomes. |
| G10 | Nine remaining Source roles and whole-family closure | Unfinished family | P2 | Complete reviewed selection and coherent dependencies, followed by separate execution qualification. |
| G11 | Original fixtures, ceremony, runtime and recovery | Missing complete-workflow evidence | P2 | Fresh admitted required scopes and adopted outcomes through the complete required chain. |
| G12 | Coverage of composed behavior and failure paths | Missing assurance | P1/P2 | Contract-to-test matrix and scoped integration/fault results. |
| G13 | Scientific labels, eligibility and critic split bridge | Unfinished implementation/data qualification | R | Real label-to-candidate adapter and qualified group-preserving dataset split. |
| G14 | Complete H1/H2 scientific evidence | Incomplete research outcomes | R | Permitted experiment obligations and registered analyses with honest scope. |
| G15 | Trained critic and held-out H3 comparison | Incomplete research outcome | R | Qualified training, baseline comparison and held-out analysis. |
| G16 | Final power/inference and permitted claim scope | Accepted limitation plus unfinished analysis | R | Validated final inference/null calibration and explicit limitations. |
| G17 | Environment and artifact reproducibility | Assurance limitation | S/R | Qualified runtime/dependency artifacts and appropriately scoped reproduction evidence. |
| G18 | Current-state clarity and milestone focus | Engineering judgment/process risk | S | Maintained dependency map, dated evidence levels and milestone closure records. |
| G19 | Student prose and external scientific review | Documented reporting obligations | R/S | Student-authored final prose and disposition of the outstanding scientific review. |

## 4. Detailed engineering gaps

### G01. I2's external canonical receipt ABI remains unqualified

**Current evidence.** The latest [I2 API003](development/native-producer-qualification/20261017-i10/i2/CURRENT_OWNER_M3_DEFERRED_METADATA_INERT_API_003.json) still declares `external_canonical_receipt_ABI_qualified: false`. I10 fixes inherited phase basename handling: preserve `.TEMPLATE.ps1` and `.BOUND.ps1`, substitute only the authenticated three-digit ordinal, require an ordinal later than 018 and the preceding selection, and keep it below 1000. That narrow predicate passed 134 cases. It does not qualify the producer's complete selection, rendering, inverse construction, CLI or receipt handoff.

**Why it matters.** The downstream publication adapter needs authentic producer output with the exact accepted contract. A new Source hash or a passing naming kernel cannot substitute for this contract. I6 deliberately refuses the held producer route; the newer hash alone does not remove that hold.

**Work required.** Specify and review the producer's complete external interface against I5/I6/I7 consumers. Preserve the original seven-link checks, exact path identities, caps, whole render/inverse/diff requirements and stage-purpose checks. Exercise the appropriate complete producer path in a separately admitted bounded scope, and independently check the resulting outputs with the recorded-semantic validator.

**Closure criteria.** A reviewed successor, matching API and independent adoption identify exactly which producer route is qualified, which consumer accepts it, and the complete positive/refusal evidence. No qualification flag should change merely to bypass a consumer rejection. Actual canonical writing remains a separately admitted action.

Evidence: [I10 qualification](development/native-producer-qualification/20261017-i10/I10_PHASE_BASENAME_QUALIFICATION.md), [I2 Source003](development/native-producer-qualification/20261017-i10/i2/build_M3_metadata_current_owner_deferred_003.py.source), [I6 adapter report](development/native-publication-adapter/20261015-i6/I6_PUBLICATION_METADATA_ADAPTER.md).

### G02. The actual prewrite caller does not yet compose I8, I9 and I7

**Current evidence.** I8 validates owner, existing lease and publication-purpose metadata. I9 validates recorded M3 semantics. I7 has tested private file operations but retains held public entry. These are distinct layers; a qualified real caller joining them at the actual write boundary is absent.

**Why it matters.** Individually valid inputs can still describe different requests, selections, leases or bytes. A caller can also observe changes between separate callbacks and physical IO. The current evidence does not establish a live race; it establishes that the route which must exclude such mismatches is not qualified.

**Work required.** Bind the same request, owner support, action-specific scope, lease, selection, producer/publisher code proofs, rows, drafts, receipts, outputs and actual actor to both validation layers and the ensuing IO. Call the exact reviewed kernels; do not replace their results with caller-supplied dictionaries claiming validation. Establish what bytes are cached, when observations occur, which observations must remain current, and how the actual write consumes the accepted data.

Specific contract joins need explicit treatment:

- I7/I8 support up to eight rows; I9's accepted request bound is four. Respect the stricter bound and I9's restriction against a matching TEMPLATE/BOUND pair in one request. Do not silently widen I9.
- I8 distinguishes up to 252 ordinary inputs from four purpose auxiliaries. Do not flatten those auxiliaries into the ordinary publication-purpose closure.
- I9's immutable cache applies within its own prewrite call. It is not proof of one shared physical snapshot across I8, I9 and IO. Bound shared callback and byte consumption as well as each component's local budgets.
- I8's `disk_free_bytes` and I9's recorded `free_disk_bytes` require an exact typed bridge. Blind field normalization is insufficient.
- Protect the union of future outputs before callbacks. Textual alias checks do not establish absence of hard-link, junction or other physical alias effects at the real caller boundary.

**Closure criteria.** Review and adopt the actual caller Source, then demonstrate both accepted composition and refusal of cross-layer mismatches: different valid selections, different leases, changed draft bytes, stale time/resources, callback mutation, future-output aliases and shared-budget exhaustion. Saved results must distinguish metadata-only tests from actual owned IO.

Evidence: [I8](development/native-publisher-admission/20261015-i8/I8_PREWRITE_OWNER_LEASE_PURPOSE.md), [I9](development/native-m3-prewrite/20261017-i9/I9_RECORDED_M3_SEMANTICS.md), [I7](development/native-publisher-implementation/20261015-i7/I7_HELD_PUBLISHER_IO_IMPLEMENTATION.md).

### G03. Bootstrap order and post-publication proof chronology need qualification

**Current evidence.** Creating a BOUND phase depends on its matching canonical TEMPLATE and the accepted `capture_bound`, `metadata_binding` and `metadata_bound_review` prerequisites. Those latter records are outside the finite eight phase Sources. I6's batch path expects all eight canonical pins and eight draft paths before its first metadata callback. It therefore fits a later audit position rather than admission of the first file birth.

**Why it matters.** An implementation that requires all final outputs before producing its first prerequisite is circular. Inventing future hashes, placeholder metadata or a dummy publication record would conceal the circularity rather than close it.

**Work required.** Qualify the staged order described in the [acyclic bootstrap addendum](development/native-publisher-implementation/20261015-i7/I7_ACYCLIC43_AND_STAGED_EIGHT_SOURCE_BOOTSTRAP_ADDENDUM_001.json): admit an appropriate early subset, publish genuine prerequisite Sources/records, produce the dependent BOUND files, and run the all-eight metadata audit only when its actual inputs exist. Respect G02's per-request restrictions.

The later evidence sequence also needs exact separation:

1. Prewrite admission uses already existing drafts, author receipts and valid action authority.
2. Physical publication creates actual files and the publication43 record after the relevant observations.
3. A genuine external execution witness records actual process/argv/exit/streams/time after the call it witnesses.
4. Canonical delta review and adoption assess the born artifacts.
5. Reconciliation26 authenticates the earlier publication without rewriting it.

The `Root_publication` proof may resolve through a new reconciliation26 to the original publication43. The `canonical_publication` proof must refer directly to the original publication43 and exact author receipt. These roles are not interchangeable. I6's authenticated witness metadata is not independent proof that every asserted PID/exit event occurred.

**Closure criteria.** An independently reviewed dependency order has no forward self-reference, future hash or fabricated witness. The saved actual sequence proves each prerequisite existed before consumption and retains the original publication separately from its later reconciliation.

**Important boundary.** This does **not** create an all-45-files-before-Native8 rule. The accepted design permits separately selected finite-eight measurement before the whole 45-role family is complete.

Evidence: [admission design](development/native-admission-design/20261015-owner-v2/NATIVE_ADMISSION_DESIGN.md), bootstrap addendum above, [I6](development/native-publication-adapter/20261015-i6/I6_PUBLICATION_METADATA_ADAPTER.md), [I7](development/native-publisher-implementation/20261015-i7/I7_HELD_PUBLISHER_IO_IMPLEMENTATION.md).

### G04. Current owner, lease, purpose and host bindings are not issued execution evidence

**Current evidence.** I0's memory tests and I1's Source review do not issue a real lease. New actual lease/family selection, paths, ordinals, duration, INIT, purpose and result values remain unissued/null. The current Source scheduling window is Source-only; historical execution leases remain historical.

**Why it matters.** A saved JSON contract or a reviewed program cannot supply the actual current actor, clock, native identity, resources or exact action authority. Copying bytes onto a host does not recreate a previous physical process or filesystem identity.

**Work required.** Complete the reviewed owner/clock-entry route before actual native timestamp-image entry. Establish the real host binaries, exact argv/module identities, action purpose, current resource observations and applicable lease checks for each admitted operation. Resolve any expired Source scope before later gated Source work; obtain execution evidence through its separate route.

**Closure criteria.** Accepted records identify actual actors and observations, their order and ages, the precise allowed action, and unchanged bounds. A Source window must never be described as an actual execution lease. This document grants neither.

The standing user instruction removes mandatory renewed Pro3 coordination: continue within the authorized scope and report a genuine resource pause when needed. Pro3 contact is not an unresolved project prerequisite.

Evidence: [I0/I1](development/native-owner-implementation/20261015-i0-i1/I0_I1_IMPLEMENTATION.md), [current handoff](../HANDOFF.md), [current Source scope](development/native-producer-qualification/20261017-i10/ROOT_CURRENT_I10_PRODUCER_CALLER_SOURCE_SCOPE_001.json).

### G05. Native8 lacks a qualified current input and accepted result carrier

**Current evidence.** I3's Source port preserves all 15 protected functions and the exact eight-subject loop, but remains held and unrun. It needs qualified I2/I5 publication/provenance inputs and a result carrier compatible with the later Parser/interface contracts. Root writer raw metadata observations do not stand in for Native8.

**Why it matters.** Correct Native8 internals are insufficient if the wrong selected Sources are measured or the downstream Parser cannot authenticate the resulting support.

**Work required.** Review the current dependency binding and the complete carrier, including selected Source identities, owner/purpose provenance, all protected comparison vectors, outcomes and consumer references. Ensure I4 can consume the accepted support without relabelling an old record as new authority.

**Closure criteria.** A reviewed I3 successor and compatible consumer contract precede a separately admitted actual finite-eight run. The resulting support must be independently reviewed and adopted for the exact current selected subjects. A correct carrier schema alone does not close G06.

Evidence: [I3 report](development/native-measurement-implementation/20261015-i3/I3_NATIVE_IMPLEMENTATION.md), [I4 report](development/native-parser-implementation/20261015-i4/I4_PARSER_IMPLEMENTATION.md), [I5 report](development/native-interface-implementation/20261015-i5/I5_INTERFACE_IMPLEMENTATION.md).

### G06. Physical native stability has unresolved refusal evidence

**Current evidence.** Two preserved attempts refused the first full Native10/PATH9/descriptor9 stability guard:

- **Attempt001:** comparison vectors were not saved and the changed field is unknown. Physical drift was neither established nor ruled out. This cannot be called a demonstrated LastAccess failure.
- **Attempt002:** the first 14,587-byte WRITE-before TEMPLATE read retained matching content and independently stable Python PATH9/descriptor9 vectors. Native10 `ftLastAccessTime_FILETIME_ticks`, index 2, changed from `134361647848810457` to `134361648002150029`: **153,339,572 ticks, or 15.3339572 seconds**. Cause and responsible process are unknown. The second-read/after-close sample and remaining seven subjects were not reached.

**Why it matters.** There is no accepted current-family eight-subject physical measurement. The observed field change is a real qualification obstacle, but its cause must not be attributed to Windows policy, antivirus, an agent or another actor without evidence.

**Work required.** After G01–G05's applicable prerequisites, conduct a genuinely fresh admitted measurement with the unchanged complete Native10 vector, both independent full Python9 vectors, cross-checks, exact timestamp/native identity guards and original one-call/no-retry rules. Save complete comparison vectors and the exact stopping point, including refusals and cleanup.

**Closure criteria.** Adopt an actual accepted finite-eight result or an explicit evidence-backed disposition if the unchanged guard cannot be satisfied. Any proposed guard/design change requires its own explicit controlling decision; silent omission, normalization, warm-up, clock backdating or replay of spent identities is not closure. Read-only consistency checks do not establish physical handle absence or whole-host quiet.

Evidence: [native design](development/native-admission-design/20261015-owner-v2/NATIVE_ADMISSION_DESIGN.md), [saved frontier report with original attempt pins](development/native-admission-design/20261015-owner-v2/NATIVE_ALGORITHM_PARSER_CURRENT_OWNER_DESIGN_FRONTIER_REPORT_001.json).

### G07. The current Native Parser workflow has not been qualified

**Current evidence.** I4 accepts dormant Source changes, not a Parser result. Its current parent/child Sources were not executed or syntax-validated with `ParseFile` during the I4 step. This does not erase syntax checks performed on older versions. The four required current subjects are WRITE-before, SUPERVISE-before, WRITE-after and SUPERVISE-after BOUND Sources.

**Why it matters.** Actual canonical script parsing, complete token/error capture, exact child invocation, process ownership, terminal status and cleanup have not been demonstrated together for the current family.

**Work required.** First provide accepted current Native8 support and reviewed I5/G08 bindings. Then establish the actual owner/purpose route before invocation, preserving later admission checks before directory creation, child launch and parsing. Internal native initialization may occur before some internal admission checks; do not claim a stronger ordering than the Source establishes. Fresh Root prelaunch resource observations must satisfy the original age constraint.

**Closure criteria.** An admitted current run saves all four real `ParseFile` outcomes, complete token/error arrays, both literal proofs, exact argv, the one hidden owned child, and complete terminal/cleanup/reap evidence. Preserve all 47 IO spans, both original mains, and **120 total / 110 wait / 10 cleanup / 5 owned reap** budgets as nested constraints rather than additive time allowances.

Evidence: [I4 Parser report](development/native-parser-implementation/20261015-i4/I4_PARSER_IMPLEMENTATION.md), [native admission design](development/native-admission-design/20261015-owner-v2/NATIVE_ADMISSION_DESIGN.md).

### G08. A reachable version2 Parser saved-result adapter is missing

**Current evidence.** The old schema1 INTENT12, child-result20 and witness20 records remain protected data leaves. The preserved mains terminate with `exit`; appending an emitter after those exits would not produce a usable new result. The owner-context path still needs a reviewed current saved-result envelope and consumer binding.

**Why it matters.** A genuine parse result can still be unusable if its provenance and schema cannot be authenticated by the current downstream consumer. Conversely, renaming an old leaf cannot create current owner authority.

**Work required.** Implement a reachable adapter that preserves the protected leaves and carries exact leaf pins, producer identity, owner/purpose provenance and required current references. Review how it is invoked, how its outputs are saved, and which consumer validates them. Keep the distinction between underlying result data and the envelope's authority explicit.

**Closure criteria.** Review/adopt the Source and its exact contract, then independently review/adopt the saved result from the appropriate admitted path. Do not close this gap with an unreachable post-main emitter or an unverified schema relabel.

Evidence: [I4](development/native-parser-implementation/20261015-i4/I4_PARSER_IMPLEMENTATION.md), [I5](development/native-interface-implementation/20261015-i5/I5_INTERFACE_IMPLEMENTATION.md).

### G09. The phase-peer, strong-binding and checker-configuration chain is held

**Current evidence.** I5 context ports remain unrun with false entry holds and an additional unconditional refusal. Their metadata subsets do not constitute a complete lawful producer/self-Source closure. The original seven-link checks, strong-binding 21-field prerequisites/20-field outputs, and configuration 39-field prerequisites/18-field outputs remain protected. Old selected-peer receipt27 integration is outside current acceptance.

**Why it matters.** Upstream files and a Parser result must be authenticated by the actual downstream consumers before the complete selected family can support runtime claims.

**Work required.** Bind genuinely selected phase Sources to accepted Native8 support, accepted Parser support, current phase-peer results, strong binding and checker configuration. Preserve their exact dependency joins and distinguish metadata admission from the complete consumed record.

**Closure criteria.** Reviewed current consumer successors accept genuine current records in the required order, reject stale/mismatched references, and produce separately reviewed/adopted outcomes. Their held entry flags must follow demonstrated qualification rather than be removed to create an apparently runnable path.

Evidence: [I5 interface report](development/native-interface-implementation/20261015-i5/I5_INTERFACE_IMPLEMENTATION.md), [admission design](development/native-admission-design/20261015-owner-v2/NATIVE_ADMISSION_DESIGN.md).

### G10. Nine Source roles and complete-family coherence remain unfinished

The exact pending roles in the dated 36/45 inventory are:

| Role | Remaining obligation |
| --- | --- |
| `phase_peer` | Genuine current phase peer review and its dependency closure. |
| `binding` | Current strong-binding Source/records compatible with accepted phase evidence. |
| `pipeline_peer` | Genuine current pipeline peer acceptance. |
| `checker_config` | Current configuration Source/records with all required prerequisites. |
| `table` | Current selected table and exact family references. |
| `constructor` | Current constructor Source and later appropriate fixture qualification. |
| `constructor_manifest` | Genuine current constructor manifest and authenticated payload closure. |
| `constructor_review` | Genuine independent review and adoption of the current constructor closure. |
| `selector` | Current selector Source and later appropriate selection/fixture qualification. |

**Why it matters.** The complete 45-role family and ten-tool compound are not ready. Historical completion of an older family is not current completion. The newer accepted `checker_peer` is no longer on this pending list.

**Work required.** For each role, record exact selected Source/record identities, dependencies, review and adoption. Then verify cross-family coherence: namespaces, future ordinals later than 018, nonces, coupling, lease/proof references and consumer prerequisites. Do not invent future selections or translate separate accepted Sources into automatic combined authority.

**Closure criteria.** A reviewed complete selection and dependency closure, followed by the separate required execution qualifications. Keep the finite-eight branch distinct: all nine roles need not be completed before every earlier Native8 activity allowed by the design.

Evidence: [Source continuation report](development/source-continuation/20261015-checker-peer015/SOURCE_CONTINUATION.md), [actual outcome/pending ledger](development/source-continuation/20261015-checker-peer015/evidence/ROOT_CHECKER_PEER015_ACTUAL_SOURCE_OUTCOME_PENDING_SCOPE_LEDGER.json).

### G11. The original complete workflow, current runtime and recovery are unproved

**Current evidence.** Fresh original constructor/selector fixtures, successful C8, actual6, current runtime and scientific recovery remain unentered or unproved. Preserved C8 refusals and older mock/fixture successes do not establish a complete current-family workflow. Actual historical entry005 stopped at a BOUND producer stdout-contract refusal before the copied unit launch; that history must not be promoted to actual6 success.

**Why it matters.** There is still a gap between reviewed tooling and the complete workflow needed to resume the frozen scientific work under its original controls.

**Work required.** Close the applicable producer/consumer/family prerequisites, qualify fresh required fixtures and admission, then save accepted outcomes through the complete necessary runtime chain. Reconcile the incident-specific D-161 recovery requirements with the frozen fitting Source, twins/epoch and permitted retained artifacts before any scientific recovery action.

**Closure criteria.** Exact accepted current outcomes, including process/argv/resource/age evidence and owned cleanup, establish each required stage. Preserve local-only/partial evidence rather than treating unavailable history as permission to retrain it.

The dated standing scientific inventory remains **150 complete fits / 270 models: 149 synced fits and one local-only; 111 untouched cases**. It was not recounted here, and recent I9/I10 work added no scientific fits. Older Week8 totals such as 239 fits/811 models are historical workload calculations, not a current remaining-work estimate or ETA.

Evidence: [HANDOFF](../HANDOFF.md), [CONTINUE](../CONTINUE.md), [PROJECT_STATE](../PROJECT_STATE.md), [DECISIONS D-161 and later controlling entries](../DECISIONS.md), [Week8 readiness audit](week8_readiness_audit.md).

### G12. The test record does not yet cover the complete composition

**Current evidence.** Component evidence is heterogeneous: Source checks, test methods, synthetic cases, extracted AST functions and real owned-file operations. Review check counts are not test cases. None of these alone establishes complete integration or scientific validation.

The failed/unknown history also matters:

- I8's accepted 97-case run was its third scoped suite. Earlier runs included a zero-completion `E_PHASE_ORDINAL` refusal and an 89-completion run ending at an expected-refusal/no-op alias fixture error. Both remain evidence.
- I9 had seven owned launches: four known failed suite entries, two timeouts with unknown suite entry/progress/count/audit, and one accepted complete 98-case run. Five suite entries are known; the aggregate suite-entry count remains unknown. Neither timeout can be counted as zero entries, a successful case, or a known amount of progress.
- I10's 134 cases exercise two extracted functions. They do not supply complete-I2 regression coverage.

**Work required.** Maintain a contract-to-evidence matrix mapping each preserved requirement to its exact positive cases, refusal cases, execution boundary, Source version and adoption. Prioritize integration mismatches and failure preservation: stale authority, changed bytes, partial writes, no-overwrite behavior, wrong consumer pins, process failure and cleanup failure.

**Closure criteria.** Separately admitted fresh scopes exercise the composed routes and real effects they claim, with independent result review. Preserve failed/unknown history and explain what changed. Do not rerun spent fixtures to replace the record or sum unrelated counts into an overall pass percentage. No exclusive cause or general performance conclusion for the I9 timeouts is established.

Evidence: [I8](development/native-publisher-admission/20261015-i8/I8_PREWRITE_OWNER_LEASE_PURPOSE.md), [I9](development/native-m3-prewrite/20261017-i9/I9_RECORDED_M3_SEMANTICS.md), [I10](development/native-producer-qualification/20261017-i10/I10_PHASE_BASENAME_QUALIFICATION.md).

## 5. Scientific and reproducibility gaps

### G13. Real labels do not yet flow through a qualified critic dataset bridge

**Current evidence.** The saved C-007 status explicitly says the final repair-label-to-critic `SplitCandidate` bridge is absent. C-005's splitter exists and was adversarially audited on synthetic inputs; its split seed and numeric targets remain absent and require a Change Record before selection. A synthetic splitter qualification does not establish a real eligible dataset.

There are substantive observed labels already. The later E1 report records **30 completed unit labels in five comparison groups: 29 observed class0, zero class1, zero ambiguous and one undiagnosed**. All 29 decidable E1 labels are class0. This is an **E1-only** result; `min(N0,N1)=0` there is not a whole-design or final test-set adequacy verdict.

**Why it matters.** The planned class balance is not the observed repair-verified class balance. The critic requires authentic labels, eligible examples, comparison-group-preserving partitions and leakage control. Ambiguous/undiagnosed exclusions can change available counts.

**Work required.** Implement the authenticated adapter from actual repair verdicts into critic candidates. Keep intended class distinct from observed diagnosis. Apply the controlled eligibility/exclusion rules, choose split seed/targets through the existing change process, preserve comparison groups across training/validation/test, and enforce the feature whitelist. Qualify the combined path on actual permitted labels before training.

**Closure criteria.** Saved provenance connects every eligible candidate to its source observation and repair verdict. A reviewed split/balance/eligibility report demonstrates actual observed class counts, exclusions, group isolation and feature availability. Do not infer availability from the planned 300 conditions or treat planned 150/150 balance as observed. No Week8 exclusion rate, reserve trigger or replacement/expansion decision was computed in the E1 label report.

Evidence: [PROJECT_STATE C-005/C-007 and correction index](../PROJECT_STATE.md), [README workflow](../README.md), [later E1 repair-label report](week7_repair_label_results.md).

### G14. H1 and H2 remain incomplete scientific claims

**Current evidence.** H1's developmental reliability gate passed, while the full confirmatory H1 interpretation/verdict remains incomplete; H2 remains untested. Confirmatory-seed E1 analyses already exist: D-156's negative-trend component passed five of five configurations, but it is an amended, post-collection/partly exposed operational component. It is not full H1 confirmation, pooled/global inference or pristine preregistration. The README's headline that confirmatory H1 is not yet tested must not be read as saying no confirmatory-seed analysis has occurred.

The later [repair-label report](week7_repair_label_results.md) supersedes the earlier E1 report for label completion. Statements in older reports that all E1 labels are missing must not be reused as current status. Conversely, completing E1 labels does not complete H1/H2 or the other experiment families.

**Why it matters.** Promising developmental behavior and completed label calculations cannot establish broader hypotheses that require different data, repair verification and registered analysis.

**Work required.** Complete the genuinely permitted remaining experiment obligations and apply the controlling analyses. H2 needs its registered per-seed ratio-of-means interpretation and frozen failure mask, with repair-verified cross-class evidence from the relevant experiment families, including E1/E2A/E2B obligations. A secondary Pearson correlation cannot decide primary H2.

Interpret existing results at their actual level. E1 label verdicts use paired seed-mean effects and 95% t intervals, with the specified conjunction of negative effect, negative upper bound and reduction greater than 0.20. Six shape/uniform conditions use 20 seeds, 1000–1019; the other 24 use three, 1000–1002. Do not merge those calculations with the older five-seed H1 component. Reported interval `converged` flags refer to interval formation, not neural optimizer convergence.

**Closure criteria.** Each hypothesis has a provenance-backed result or explicitly justified inconclusive/non-adjudicable outcome under the controlling decisions. Preserve amendments and exposure history, do not recompute verdicts from rounded display numbers, do not add unapproved seeds, and do not present repeated use of an immutable artifact as an independent statistical look.

Evidence: [README research status](../README.md#research-status), [E1 results](week7_experiment_1_results.md), [E1 repair labels](week7_repair_label_results.md), [Week8 audit](week8_readiness_audit.md), [DECISIONS D-156 and relevant controlling entries](../DECISIONS.md).

### G15. The learned critic and held-out H3 comparison are still absent

**Current evidence.** H3, the critic's planned advantage of more than five percentage points, is untested. Critic training/evaluation remains planned. Feature-whitelist or balancing checks on synthetic labels do not establish a trained critic or an evaluation result.

**Why it matters.** The central research objective includes learned diagnosis: distinguishing whether a failure calls for more data or a different hypothesis class. Infrastructure and observed repair labels are necessary inputs, but they do not establish this learned diagnosis advantage.

**Work required.** After G13, establish the permitted training procedure, reproducible seeds/configuration, appropriate baseline, comparison-group-preserving evaluation and final inference. Keep held-out data isolated from fitting, model/threshold selection and exploratory feature changes. Report actual eligible class composition and uncertainty, not only a headline accuracy.

**Closure criteria.** Accepted artifacts connect the observed labels and allowed features to the trained critic, baseline predictions and held-out comparison. H3's interpretation follows G16's validated final inference and known power limits. A negative or inconclusive comparison remains a valid reported outcome; positive H3 support is not guaranteed by completing the software.

Evidence: [README](../README.md#research-status), [PROJECT_STATE](../PROJECT_STATE.md), [methodology chapter](methodology_chapter.md), [controlling decisions](../DECISIONS.md).

### G16. Statistical power is a known accepted limitation; final inference still needs qualification

**Current evidence.** Gate1 **failed the five-percentage-point power/MDE condition**. Compute condition2 is **NOT ADJUDICABLE across hosts**, rather than PASS: local CPU wall-hours cannot be equated with the planned Kaggle T4 GPU-hours. Later controlling entries correct earlier contrary wording.

The accepted disposition already permits continuing the **unchanged 300-unit design with an explicit power limitation**. Direction C, including an inconclusive H3 result around the ±5-point band, is an authorized thesis outcome. This assessment does not impose a new Gate1-PASS prerequisite.

**Why it matters.** Even successful implementation and complete permitted data collection may not resolve the planned five-point comparison with the desired precision. That is a scientific limitation, independent of the current software gaps.

**Work required.** Specify and validate final group-level H3 inference and null calibration before making exact final MDE/power claims. For exact MDE reporting, the simulation must use the same final inference as H3 and validate its null rejection size against nominal **0.05 under Monte Carlo uncertainty**, as D-089/D-098 require. This reporting condition is not a new prerequisite for unrelated Source continuation. Preserve the controlling comparison-group dependence rules; the historical `n_eff=115` quantity is a bound, not a certified effective sample size. Explain the permitted conclusion when uncertainty spans the decision band.

**Closure criteria.** The final analysis records its method, calibration, uncertainty and claim limits, including an honest inconclusive outcome when warranted. A non-significant or unresolved comparison must not be relabelled equivalence. Earlier 18–22-point or 1,500–2,000-unit diagnostics are uncertified and must not become current exact estimates or a mandatory expansion.

**Required disposition.** Continue within the already authorized design and limitations. Do not manufacture Gate1 PASS, change the margin, add seeds, expand the study or use CPU/GPU comparisons to retroactively satisfy the gate. Any future design change needs its own explicit controlling decision; it is not implied by this gap assessment.

Evidence: [DECISIONS correction index and D-089/D-098/D-119/D-120/D-123](../DECISIONS.md), [README research status](../README.md#research-status), [PROJECT_STATE Gate1 section](../PROJECT_STATE.md).

### G17. Full environment reproduction remains unqualified

**Current evidence.** STEP080's clone/restore qualification is real engineering evidence for its dated 35/45 snapshot. It used verification/restore/QA without invoking original/restored project code. The requirements guide explicitly describes the 37-version CPU dependency snapshot as **not a complete hash-locked dependency/build reproduction**. The included PyYAML wheel is pinned; complete acquired-wheel/build provenance is not supplied for all dependencies.

**Why it matters.** Restoring exact Source bytes and installing named versions do not by themselves reproduce the training environment, native process identities, original build provenance or scientific numerical outcomes. This is an assurance limitation, not evidence that ordinary environment setup is broken.

**Work required.** Match each intended reproducibility claim to its required runtime/binary/dependency and acquired-artifact evidence. Preserve platform/host distinctions, actual package provenance, configuration, seeds, model/data artifacts and the authorized scope of any reproduction run. Qualify actual new device/runtime bindings separately from historical byte restoration.

**Closure criteria.** A reproducibility report says exactly what was restored, what was installed, what was run, which outputs were compared and which uncertainties remain. Do not claim a fully reproduced scientific environment merely from clone success, or transfer STEP080's inventory to later Sources without a separate current manifest.

Evidence: [requirements guide](../requirements/README.md), [clone qualification](development/portability/STEP080/GITHUB_CLONE_QUALIFICATION.md), [local qualification](development/portability/STEP080/LOCAL_QUALIFICATION.md).

## 6. Planning and documentation risk

### G18. Current-state clarity and milestone focus need continuous maintenance

**Observed documentation structure.** The project deliberately preserves older documents and dated “next”, “pending” and preparation statements beneath newer additions. Current completion banners and later adoptions resolve several such statements. A reader who treats every historical paragraph as current can reach contradictory conclusions.

**Engineering judgment.** The amount of component review and evidence can obscure the main dependency path. Further isolated checks help only when they close an identified obligation or reduce a concrete uncertainty. There is no measured overhead percentage, time-loss estimate or demonstrated defect rate behind this assessment.

**Work required.** Keep a concise current route from handoff to gap register, exact evidence and next deliverable. Separate “implemented”, “Source-reviewed”, “synthetically tested”, “physically exercised”, “integrated” and “scientifically supported”. Preserve complete historical bytes and identify supersession rather than deleting inconvenient refusals or rewriting old outcomes.

**Closure criteria.** Every milestone update identifies the closed gap, exact scope and evidence, remaining dependencies, and next concrete deliverable. Current summaries must not call 36/45 overall progress, treat review checks as test coverage, claim “all tests passed” from component evidence, or turn a subjective rating into a benchmark.

This document provides a starting map, not a new append-only checkpoint or STEP081. The previous documentation/handoff publication is already complete; retained preparation text below its completion banners is not an unresolved publishing blocker.

Evidence: [HANDOFF](../HANDOFF.md), [CONTINUE](../CONTINUE.md), [PROJECT_STATE](../PROJECT_STATE.md), [DECISIONS correction index](../DECISIONS.md), [actual documentation publication manifest](development/handoffs/20261017-i10-publication/HANDOFF_UPDATE_MANIFEST.json).

### G19. Student prose and external scientific review remain separate obligations

**Current evidence.** The later E1 repair-label report explicitly retains student own-voice prose and external Sol scientific review as separate obligations. The saved PROJECT_STATE also records them as open. The Week8 readiness audit identifies an approximately 500-word missing-feature results section as the student's own-voice work: drafting aids do not establish that the student wrote or understood it.

**Why it matters.** Completing code, experiments and machine-generated reports does not complete a defensible thesis narrative or its outstanding scientific review. The student must understand and defend the results, uncertainty, amendments and limitations in their own words.

**Work required.** Reconcile the outstanding writing and review items against the latest accepted research artifacts. Support the student's rewrite with accurate evidence and clearly labelled scaffolding; record the student's actual completion separately. Prepare an auditable review package when that work is authorized, showing units/groups, seed policies, estimates, interval estimands, exclusions, tests, amendment/exposure history and accepted limitations. Record review findings and their disposition rather than inferring certification from local tests or documentation changes.

**Closure criteria.** The student's final own-voice text is actually completed, and the outstanding external scientific review has an explicit recorded disposition for the submitted scope. Do not imply that all earlier prose was unreviewed: D-131 already certified the cumulative D-126–D-130 prose closeout and its limited specification scope. Later implementation/results require their own applicable review evidence.

These are existing research/reporting obligations, not new prerequisites for Source continuation or renewed Pro3 coordination. External Sol's scientific review role is distinct from Pro3. This document neither contacts a reviewer nor requests permission to do so.

Evidence: [E1 repair-label interpretation limits](week7_repair_label_results.md), [Week8 writing obligation](week8_readiness_audit.md), [saved PROJECT_STATE](../PROJECT_STATE.md), [DECISIONS writing rule and D-131 certification boundary](../DECISIONS.md).

## 7. Proposed dependency order and useful milestones

This is an engineering work map, subject to the existing controlling contracts and action-specific admission. It does not issue new scopes, assign future actual identities or change the authorized research design.

| Milestone | Work and prerequisites | Evidence needed to call it complete |
| --- | --- | --- |
| M1: qualified producer contract | G01; review exact producer and consumer expectations. | Reviewed contract and bounded qualification of routes whose prerequisites already exist, beyond I10's naming kernel. Qualification of dependent actual producer stages continues with M2's staged publication. |
| M2: qualified publication caller | G02/G03, with current applicable G04 authority. | Same-request admission/semantics/IO composition, genuine staged prerequisites, positive and refusal evidence, correct proof chronology. |
| M3: accepted finite-eight support | Appropriate M2 outputs, G05 carrier, G04 admission and G06 physical checks. | Actual complete selected-eight measurement with unchanged vectors/guards and independent result adoption. |
| M4: accepted Parser support | M3, G08 adapter, applicable I5 bindings and fresh Parser admission. | Four actual BOUND parse outcomes, complete saved-result provenance, exact owned child and cleanup evidence. |
| M5: coherent downstream family | G09/G10 and their genuine prerequisites. Source preparation may overlap earlier milestones where allowed. | Current peer/binding/configuration closure, complete selected family and separately qualified required fixtures. |
| M6: accepted original workflow | G11/G12 after all applicable entry conditions. | Required fresh ceremony/runtime/recovery outcomes and owned cleanup, without replay or relaxed guards. |
| M7: qualified research dataset | Permitted research execution/recovery, G13 and relevant G14 obligations. | Authenticated observed labels, eligibility, actual class counts, group-safe splits and leakage checks. |
| M8: final research analysis and reporting | G14/G15/G16/G19 with appropriate G17 evidence. | H1/H2/H3 results or justified limits, final inference/calibration, artifacts, explicit limitations, student prose and disposition of outstanding scientific review. |

M5 is not a prerequisite for every M3 action: the finite-eight branch can advance before all 45 roles exist when the accepted design permits it. Conversely, acceptance of M3 alone does not complete M5 or authorize M6. Documentation, adapter design and some synthetic qualification can proceed in parallel only within their actual accepted scopes.

### The next useful bounded workflow

The immediate next deliverable is **I2 external canonical receipt ABI qualification**, followed by its actual caller integration. A useful bounded publication milestone would then prove:

1. The exact reviewed producer creates valid existing drafts and receipts for an admissible staged subset.
2. The actual caller joins current owner/lease/publication-purpose checks with recorded M3 semantics for the same request and bytes.
3. Owned file operations publish that subset under the unchanged no-overwrite, preservation and resource rules.
4. Saved observations, external witness, review/adoption and reconciliation are created in valid causal order.
5. The intended next consumer accepts the authentic output; mismatched inputs and failed writes are refused with truthful preserved evidence.

That is a bounded engineering milestone. The later complete scientific workflow still needs Native8, Parser, downstream family/runtime and research gates. A synthetic demonstration of the five steps closes only the synthetic scope it actually exercises.

## 8. Constraints that must survive gap closure

The gap list is not permission to simplify away the original controls. Preserve:

- All **75 spent original identities**, with no replay to replace failed or unknown evidence; immutable Unit006.
- **3,600 retained seconds**, **1,200 admission reserve**, **600 context/runtime**, both **90-second ages**, and the original resource bounds of **60-second observations / 1 GiB RAM / 10 GiB free disk**.
- Every applicable Source/output cap, including **65,536-byte phase**, **2 MiB ordinary metadata**, and **131,072-byte model-export** caps where the controlling contracts apply.
- **ACK 510 = Root 450 + after 60**, and one successful-unit-terminal-plus-60 interval shared by all four after phases.
- Parser's nonadditive **120/110/10/5** bounds, complete native/Python vectors, exact argv/path/identity checks, no-overwrite behavior and preserved cleanup outcomes.
- The three-local-agent limit including Root, two reserved overlap slots, five shared agents and the original 60-second publication reserve.
- Frozen STEP080 and its sentinels; older Sources, refusals, reviews, adoptions, twins/epoch, D-161 incident boundaries and the withheld DELTA86 boundary.

These are preserved constraints, not recommended new budgets. Resolve exact applicability from the controlling report before implementation. Current Source-only scheduling cannot replace execution admission. The standing user instruction permits work without renewed Pro3 coordination; report actual resource pauses directly.

## 9. Issues that should not be reopened or overstated

| Topic | Correct interpretation |
| --- | --- |
| I10 phase basename mismatch | Narrow predicate repair is accepted with 134 AST cases; do not list that same predicate as still unfixed. Whole-producer qualification remains open. |
| Earlier I1 expiry-format hypothesis | Disproved for the four pinned raw expiry strings: PowerShell date conversion displayed local offsets, while raw strings already used compatible `+00:00`. No I1 Source defect or repair was observed. |
| Windows file IO | I7 really exercised owned Windows files. The remaining gap is genuine-family/caller qualification, not a claim that all file behavior was simulated. |
| I9 attempts | The accepted 98-case run coexists with four failed suite entries and two unknown-progress timeouts. Preserve all seven launches. |
| Native attempt001 | Unknown failed field; do not borrow attempt002's LastAccess diagnosis. |
| Native attempt002 | Known LastAccess difference; unknown cause. Do not assert a responsible process. |
| E1 labels | Later report completes 30 labels. Earlier “all missing” text is superseded for this claim. |
| Gate1 | Known FAIL with authorized limited-design continuation, not a new prohibition on all progress or permission to manufacture PASS. |
| Existing research results | There are substantive developmental/operational results and completed E1 labels. “No scientific evidence exists” is inaccurate. |
| Previous docs/push | Documentation closeout was completed; retained dated preparation language is history. This new assessment has its own later publication state. |
| Pro3 | Renewed coordination is not required by the standing user instruction. |
| Overall percentage/ETA | No defensible overall completion percentage or time estimate follows from file counts, review volume or component pass counts. |

## 10. Definition of done and update rules

There are three separate completion claims:

- **Engineering readiness:** qualified producer/caller contracts, genuine ordered publication, Native8 and Parser support, coherent required consumers/family, accepted complete-workflow evidence and preserved failure/cleanup behavior.
- **Research completion:** permitted data/recovery obligations, authenticated labels and critic dataset, H1/H2/H3 analysis with appropriate comparisons, valid final inference and reproducible artifacts. Unsupported hypotheses or inconclusive findings are reported honestly.
- **Reporting completion:** current status and handoff cite exact evidence, preserve known failures/unknowns, explain the accepted power limitation and distinguish historical counts from newly validated results. Student own-voice prose and the applicable external scientific review are completed with their actual provenance and disposition.

When closing a gap, add a dated entry stating its ID, exact Source/commit and evidence paths, review/adoption, what actually executed, which inputs/host were used, and remaining limitations. Keep the original dated assessment available. Do not mark a downstream gap closed merely because an upstream component passed or a metadata flag changed.

The strongest next progress claim would be a new accepted dependency milestone with actual consumer evidence. More individual passing checks are useful when they support that milestone, but do not replace it.
