"""Explicit metadata adapters for the owner-authorized Week8 relocation.

Loaded from captured controller bytes after raw authority; never a CLI/bootstrap.
The provenance module is supplied by that verified loader, not imported from the
historical bu package. No Path substitution, digest spoofing or scientific edit.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import sys
from contextlib import contextmanager
from pathlib import Path, PureWindowsPath
from types import FunctionType, ModuleType
from typing import Any, Iterator, Mapping


WORKSPACE = Path('D:/Aenv/pro2')
EXECUTION_WORKTREE = WORKSPACE/'week8-e2a-execution-4515-worktree'
EXECUTION_SOURCE = EXECUTION_WORKTREE/'src'
EXECUTION_COMMIT = '4515d5165756c8d1669d38d2ee854fa1051b1017'
_HEX64 = re.compile(r'[0-9a-f]{64}\Z')
MANIFEST_ROOT = WORKSPACE/'resume-2026-09-05/autonomous-2026-09-19-185105/attestation-002'
RECORD_SHA256 = 'dd3f546bfa05c4df1cef653fc2ea7e3602cb50ad5506775286d50b79b6f6d187'
POLICY_SHA256 = 'a25fa279a5ccce335ac04b31ecba209c38f2fa77a3f67db14356e228348095dc'
LEDGER_SHA256 = '2265cbcece1033ce4d0f3df2e4b093d497c6815d5cb0592a511a6515f9fd7379'
EXPECTED_PAIR_COUNT = 304
EXPECTED_DOCUMENT_COUNT = 629
OLD_ROOT = PureWindowsPath('D:/Aenv/pro/pro')
LEDGER_LOGICAL_PATH = str(OLD_ROOT/'week8-execution-preparation-2026-09-01-attempt-001/exp2a-original/week8_exp2a_source_ledger.json')
PREFLIGHT_SHA256 = '2001b4043c2a38db79db51035cf38b2777474a8f8624b6f5526fd37d554c9a0a'
PREFLIGHT_LOGICAL_PATH = str(OLD_ROOT/'week8-exp2a-2026-09-01-attempt-001-preflight/week8_preflight_report.json')
OLD_LEASE_TOKEN = 'c66ea75437c043ba9a1113e0a31d2f8d'
OLD_CHECKPOINT_SHA256 = 'a8dc8652d4000753a4b7e3731bbecaf09d448f72d56d98bdb15610188c583169'
OLD_CHECKPOINT_DIGEST = '3ec6d54d1bb0434bd7d4a28ee5d4c55fc3d1955f0d20a8577f267537d4f9cee5'
OLD_CONTEXT_DIGEST = 'b73ad26fbc212d629c4734453f76add739a96d00317466c03756badba90ab38e'
RELOCATION_CONTEXT_FILE = 'week8_exp2a_relocation_context.json'
ORPHAN_JOB_ID = '178f4ef3ae1e-s1001'
OLD_EVENT_COUNT = 299
OLD_EVENT_CHAIN_SHA256 = '13207af2f0a1d461cf471acc7dc9eeef03b6113dda3712acd778d5e4bf4dfc45'
OLD_EVENT_TAIL_SHA256 = 'cd49822ee99ddd909596d314a99e4749944580fdb4176a7e76bf43f9ef02b2ac'
PRODUCTION_FOLDERS = {
    'preflight':'week8-exp2a-2026-09-01-attempt-001-preflight',
    'output':'week8-exp2a-2026-09-01-attempt-001-output',
    'staging':'week8-exp2a-2026-09-01-attempt-001-staging',
    'sync':'week8-exp2a-2026-09-01-attempt-001-project-evidence',
}
_AUTHORITY_FIELDS = (
    ('week6_smoke','label'), ('week6_smoke','finalization'),
    ('week7_exp2a','launch_report'), ('week7_exp2a','verification_receipt'),
)


class MetadataRefused(ValueError):
    """A historical/current binding or explicitly installed seam differs."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise MetadataRefused(message)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_registered_access(verifier: Any) -> Any:
    """Only release-pinned twins/policy; callers cannot select a manifest."""
    paths = (MANIFEST_ROOT/'original/relocation.json', MANIFEST_ROOT/'copy/relocation.json')
    policy_path = MANIFEST_ROOT/'policy.json'
    for path in (*paths, policy_path):
        require(path.is_relative_to(WORKSPACE), 'manifest escaped fixed workspace')
        verifier._chain(path.parent)
    original_rows = [verifier._file(path) for path in (*paths,policy_path)]
    raw, twin, policy_raw = (path.read_bytes() for path in (*paths,policy_path))
    require(raw == twin and _sha(raw) == RECORD_SHA256, 'relocation twin bytes differ')
    require(not os.path.samefile(*paths), 'relocation twins alias')
    require(_sha(policy_raw) == POLICY_SHA256, 'relocation policy pin differs')
    policy = json.loads(policy_raw)
    require(type(policy) is dict and set(policy) == {'pairs','documents'} and
            verifier.canonical(policy) == policy_raw, 'relocation policy schema differs')
    require(len(policy['pairs']) == EXPECTED_PAIR_COUNT and
            len(policy['documents']) == EXPECTED_DOCUMENT_COUNT, 'relocation policy count differs')
    pairs = tuple(verifier.Pair(**row) for row in policy['pairs'])
    documents = tuple(verifier.Document(**row) for row in policy['documents'])
    access = verifier.EvidenceAccess(raw, RECORD_SHA256, WORKSPACE, pairs, documents)
    require(original_rows == [verifier._file(path) for path in (*paths,policy_path)],
            'relocation manifests changed during verification')
    return access


class OrphanLeaseReader:
    """Exact archived lease proof bound by the admitted worker's transition.

    The native fit handshake binds the whole child invocation, including this
    transition's file hash. The worker already validated its complete authority,
    liveness and quarantine chain; this reader reopens its fixed immutable twins
    and the archive before every historical lease lookup. It grants no release,
    acquisition, transition or fitting capability.
    """

    def __init__(self, access: Any, launch: Any, transition_binding: dict, *,
                 workspace: Path | None = None, old_pid: int = 48_960,
                 old_lease_sha256: str = 'ac3879395be164ea6b57dc10382e93236eacb7a76b222897bddbda58d2597f70') -> None:
        require(type(transition_binding) is dict and set(transition_binding) == {'record_digest','file_sha256'} and
                all(type(v) is str and _HEX64.fullmatch(v) is not None for v in transition_binding.values()),
                'orphan transition binding schema differs')
        self.access,self.X,self.W = access,launch,launch.W
        self.workspace = WORKSPACE if workspace is None else workspace
        require(self.workspace == self.W.WORKSPACE_ROOT and self.workspace.is_absolute() and
                self.W.COMMON_LEASE_ROOT == self.workspace/'week7-production-control' and
                self.W.COMMON_LEASE_NAME == 'week7-production', 'orphan lease fixed roots differ')
        self.binding = dict(transition_binding)
        self.old_pid,self.old_sha256 = old_pid,old_lease_sha256
        self.active = self.W.COMMON_LEASE_ROOT/'leases/week7-production.lease.json'
        self.archive = self.active.parent/'history'/f'week7-production.{OLD_LEASE_TOKEN}.orphaned-after-liveness-proof.json'
        self.normal = self.active.parent/'history'/f'week7-production.{OLD_LEASE_TOKEN}.released.json'
        self._original = self.X._historical_lease_record
        self._replacement = self.lookup
        self._active = False

    def _canonical(self, value: Any) -> bytes:
        return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')

    def _file(self, path: Path) -> tuple[bytes,tuple]:
        path = self.W._project_path(path,directory=False)
        def stamp() -> tuple:
            info = path.lstat()
            require(info.st_nlink == 1, 'orphan proof file has another hardlink')
            return info.st_dev,info.st_ino,info.st_mode,info.st_size,info.st_mtime_ns,info.st_ctime_ns,getattr(info,'st_birthtime_ns',None)
        before = stamp()
        raw = path.read_bytes()
        require(stamp() == before and path.read_bytes() == raw, 'orphan proof file changed while reading')
        self.W._project_path(path,directory=False)
        return raw,before

    def _transition(self, lease: dict) -> tuple:
        paths = tuple(self.workspace/folder/'transition-completion.json' for folder in (
            'week8-exp2a-recovery-2026-09-02-attempt-001',
            'week8-exp2a-recovery-2026-09-02-attempt-001-project-evidence'))
        observed = tuple(self._file(p) for p in paths)
        raw = observed[0][0]
        require(raw == observed[1][0] and not os.path.samefile(*paths) and _sha(raw) == self.binding['file_sha256'],
                'authorized orphan transition twins/hash differ')
        document = json.loads(raw)
        keys = {'recovery_schema_version','recovery_id','decision_id','record_type',
                'scientific_outcomes_consulted','scientific_values_emitted','status','authorization',
                'transition_intent','orphan_lease_archive','quarantine','record_digest'}
        require(type(document) is dict and set(document) == keys and raw == self._canonical(document)+b'\n',
                'authorized orphan transition schema/canonical bytes differ')
        payload = {k:v for k,v in document.items() if k != 'record_digest'}
        require(type(document['recovery_schema_version']) is int and document['recovery_schema_version'] == 3 and
                document['recovery_id'] == 'week8-exp2a-d161-2026-09-02-attempt-001' and
                document['decision_id'] == 'D-161' and document['record_type'] == 'transition_completion' and
                document['scientific_outcomes_consulted'] is False and document['scientific_values_emitted'] is False and
                document['status'] == 'ownership_transition_complete' and
                document['record_digest'] == self.binding['record_digest'] == _sha(self._canonical(payload)),
                'authorized orphan transition identity/seal differs')
        expected_archive = {'path':str(self.archive.resolve()),'sha256':self.old_sha256,
                            'classification':'orphaned_after_liveness_proof'}
        expected_lease = {'path':str(self.active.resolve()),'sha256':self.old_sha256,'pid':self.old_pid,
                          'token':OLD_LEASE_TOKEN,'timestamp':lease['timestamp'],'timestamp_utc':lease['timestamp_utc']}
        authorization = document['authorization']
        require(document['orphan_lease_archive'] == expected_archive and type(authorization) is dict and
                self._canonical(authorization.get('old_lease')) == self._canonical(expected_lease) and
                authorization.get('automatic_retry_allowed') is False,
                'authorized orphan transition lease/archive differs')
        require(tuple(self._file(p) for p in paths) == observed, 'orphan transition changed during validation')
        return observed

    def _assert_installed(self) -> None:
        require(self._active and self.X._historical_lease_record is self._replacement,
                'orphan history reader scope differs')

    @contextmanager
    def installed(self) -> Iterator['OrphanLeaseReader']:
        require(not self._active and self.X._historical_lease_record is self._original,
                'orphan history seam changed before installation')
        self.X._historical_lease_record = self._replacement
        self._active = True
        failure: BaseException | None = None
        try:
            self._assert_installed()
            yield self
        except BaseException as exc:
            failure = exc
            raise
        finally:
            changed = self.X._historical_lease_record is not self._replacement
            self.X._historical_lease_record = self._original
            self._active = False
            if changed or self.X._historical_lease_record is not self._original:
                raise MetadataRefused('orphan history reader changed or failed restoration') from failure

    def lookup(self, token: str) -> dict:
        self._assert_installed()
        require(type(token) is str, 'historical lease token is not a string')
        if token != OLD_LEASE_TOKEN:return self._original(token)
        require(not os.path.lexists(self.normal), 'orphan token has a forbidden normal release')
        original = self.access.historical_file(str(OLD_ROOT/'week7-production-control/leases/week7-production.lease.json'))
        require(original.sha256 == self.old_sha256, 'orphan original lease pin differs')
        lease = original.document()
        lease_keys = {'schema_version','lease_name','pid','token','timestamp','timestamp_utc'}
        require(type(lease) is dict and set(lease) == lease_keys and type(lease['schema_version']) is int and
                lease['schema_version'] == 2 and type(lease['pid']) is int and lease['pid'] == self.old_pid and
                lease['lease_name'] == 'week7-production' and lease['token'] == OLD_LEASE_TOKEN and
                type(lease['timestamp_utc']) is str and bool(lease['timestamp_utc']), 'orphan original lease identity differs')
        archive = self._file(self.archive)
        require(archive[0] == original.raw, 'orphan archive differs from the preserved original lease')
        transition = self._transition(lease)
        active = None
        if os.path.lexists(self.active):
            active = self._file(self.active)
            current = json.loads(active[0])
            require(type(current) is dict and set(current) == lease_keys and type(current['schema_version']) is int and
                    current['schema_version'] == 2 and current['lease_name'] == 'week7-production' and
                    type(current['pid']) is int and current['pid'] > 0 and type(current['token']) is str and
                    re.fullmatch('[0-9a-f]{32}',current['token']) is not None and current['token'] != OLD_LEASE_TOKEN,
                    'active continuation lease is not distinct from the orphan')
        require(self._file(self.archive) == archive and self._transition(lease) == transition and
                self.access.historical_file(original.logical_path) == original,
                'orphan lease/transition changed during lookup')
        require(not os.path.lexists(self.normal) and
                (self._file(self.active) == active if active is not None else not os.path.lexists(self.active)),
                'active or normal lease history changed during orphan lookup')
        self._assert_installed()
        return {'path':str(self.active.resolve()),'sha256':self.old_sha256,'name':'week7-production',
                'token':OLD_LEASE_TOKEN,'started_at':lease['timestamp_utc']}


class SourceReaders:
    """Adapt only source metadata access; reuse original scientific validators."""

    def __init__(self, access: Any, plan: Any, sources: Any, *,
                 ledger_logical_path: str = LEDGER_LOGICAL_PATH,
                 ledger_sha256: str = LEDGER_SHA256) -> None:
        self.access, self.W, self.S = access, plan, sources
        self.ledger_logical_path = ledger_logical_path
        self.ledger_sha256 = ledger_sha256
        self._original_authority = sources.source_authority
        self._original_pair = sources._source_pair
        self._active = False
        self._bindings: dict[str, Any] = {}
        self._expected: dict[str, Any] = {}
        self._prepare_bindings()

    def _ledger_file(self, path: str | Path | None = None) -> Any:
        if path is None:
            file = self.access.historical_file(self.ledger_logical_path)
        elif PureWindowsPath(str(path)).is_relative_to(OLD_ROOT):
            file = self.access.historical_file(str(path))
        else:
            file = self.access.historical_file_at(Path(path))
        require(file.sha256 == self.ledger_sha256, 'historical ledger file pin differs')
        return file

    @staticmethod
    def _root_for(path: Path, suffix: str) -> Path:
        parts = PureWindowsPath(suffix).parts
        require(bool(parts) and tuple(p.casefold() for p in path.parts[-len(parts):]) ==
                tuple(p.casefold() for p in parts), 'authority filename binding differs')
        return path.parents[len(parts)-1]

    def _prepare_bindings(self) -> None:
        ledger = self._ledger_file().document()
        authority = ledger['authority']
        files = {}
        for family, key in _AUTHORITY_FIELDS:
            row = authority[family][key]
            require(set(row) == {'source_path','copy_path','sha256','independent_files'} and
                    row['independent_files'] is True, 'historical authority row differs')
            left = self.access.historical_file(row['source_path'])
            right = self.access.historical_file(row['copy_path'])
            require(left.sha256 == right.sha256 == row['sha256'] and left.raw == right.raw and
                    not os.path.samefile(left.physical_path,right.physical_path),
                    'historical authority twins differ')
            files[(family,key)] = (left,right)
        S = self.S
        smoke = files[('week6_smoke','label')]
        week7 = files[('week7_exp2a','launch_report')]
        receipt = files[('week7_exp2a','verification_receipt')]
        receipt_relative = S.WEEK7_RECEIPT_ORIGINAL.relative_to(S.WEEK7_RECEIPT_ROOT)
        self._bindings = {
            'SMOKE_OUTPUT_ROOT': self._root_for(smoke[0].physical_path,S.SMOKE_LABEL_FILE),
            'SMOKE_COPY_ROOT': self._root_for(smoke[1].physical_path,S.SMOKE_LABEL_FILE),
            'WEEK7_OUTPUT_ROOT': self._root_for(week7[0].physical_path,S.WEEK7_REPORT_FILE),
            'WEEK7_COPY_ROOT': self._root_for(week7[1].physical_path,S.WEEK7_REPORT_FILE),
            'WEEK7_RECEIPT_ROOT': self._root_for(receipt[0].physical_path,str(receipt_relative)),
            'WEEK7_RECEIPT_ORIGINAL':receipt[0].physical_path,
            'WEEK7_RECEIPT_COPY':receipt[1].physical_path,
            '_metadata_source_ledger': self.metadata_source_ledger,
            'load_exp2a_source_ledger': self.load_source_ledger,
            'reverify_exp2a_source_ledger': self.reverify_source_ledger,
        }
        self._expected = {name:getattr(S,name) for name in self._bindings}

    def _assert_installed(self) -> None:
        require(self._active, 'source readers used outside verified scope')
        for name, value in self._bindings.items():
            require(getattr(self.S,name) is value, 'source adapter or root changed during scope')
        require(self.S.source_authority is self._original_authority and
                self.S._source_pair is self._original_pair,
                'original authority or scientific pair validator changed')

    @contextmanager
    def installed(self) -> Iterator['SourceReaders']:
        require(not self._active, 'nested source adapter installation')
        require(all(getattr(self.S,name) is value for name,value in self._expected.items()),
                'source seams changed before adapter installation')
        before_keys = set(vars(self.S))
        for name,value in self._bindings.items():
            setattr(self.S,name,value)
        self._active = True
        body_error: BaseException | None = None
        try:
            self._assert_installed()
            yield self
        except BaseException as exc:
            body_error = exc
            raise
        finally:
            changed = set(vars(self.S)) != before_keys or any(
                getattr(self.S,name,None) is not value for name,value in self._bindings.items())
            changed = changed or self.S.source_authority is not self._original_authority or self.S._source_pair is not self._original_pair
            for name,value in self._expected.items():
                setattr(self.S,name,value)
            self._active = False
            restored = all(getattr(self.S,name) is value for name,value in self._expected.items())
            if changed or not restored:
                raise MetadataRefused('source adapter changed or failed exact restoration') from body_error

    def _authority(self, document: dict[str, Any]) -> dict[str, tuple[str,str]]:
        self._assert_installed()
        actual, pins = self._original_authority()
        expected = copy.deepcopy(document['authority'])
        for family,key in _AUTHORITY_FIELDS:
            row = expected[family][key]
            for field in ('source_path','copy_path'):
                file = self.access.historical_file(row[field])
                require(file.sha256 == row['sha256'], 'authority file pin differs')
                row[field] = str(file.physical_path)
        require(actual == expected, 'current source authority does not match historical authority')
        self._assert_installed()
        return pins

    def metadata_source_ledger(self, path: str | Path, expected_sha256: str) -> dict[str, Any]:
        self._assert_installed()
        require(expected_sha256 == self.ledger_sha256, 'unexpected historical ledger pin')
        file = self._ledger_file(path)
        document = file.document()
        pins = self._authority(document)
        W,S = self.W,self.S
        jobs = W.existing_exp2a_jobs()
        require(type(document.get('sources')) is list and len(document['sources']) == len(jobs) == 155,
                'historical ledger roster differs')
        fields = {'job','source_kind','source_path','copy_path','expected_git_commit',
                  'execution_digest','sidecar_sha256','source_tree_digest','copy_tree_digest',
                  'copy_evidence_digest','independent_files'}
        expected_rows = []
        for row, job in zip(document['sources'],jobs,strict=True):
            require(type(row) is dict and set(row) == fields, 'historical source row shape differs')
            policy = self.access.registered_pair_policy(row['source_path'],row['copy_path'])
            require(policy.logical_source == row['source_path'] and policy.logical_copy == row['copy_path'] and
                    policy.content_digest == row['source_tree_digest'] == row['copy_tree_digest'] and
                    policy.historical_copy_digest == row['copy_evidence_digest'],
                    'source row differs from its registered historical mapping')
            digests = {name:S.L._lower_sha256(row[name],what=name) for name in (
                'execution_digest','sidecar_sha256','source_tree_digest','copy_tree_digest','copy_evidence_digest')}
            commit, execution_digest = pins[job.job_id]
            require(digests['execution_digest'] == execution_digest, 'independently pinned execution digest differs')
            expected_rows.append({'job':job.as_record(),'source_kind':W.source_kind(job),
                                  'source_path':policy.logical_source,'copy_path':policy.logical_copy,
                                  'expected_git_commit':commit,**digests,'independent_files':True})
        expected = W._seal({
            'exp2a_source_ledger_schema_version':S.SOURCE_LEDGER_SCHEMA_VERSION,
            'purpose':'all_155_existing_exp2a_fits_reverified_not_reexecuted',
            'plan_digest':W.build_exp2a_repair_plan()['plan_digest'],
            'authority':document['authority'],'replacement_training_allowed':False,
            'reused_fit_count':155,'week6_smoke_fit_count':60,'week7_baseline_fit_count':95,
            'newly_executed_fit_count':0,'sources':expected_rows,
        },'ledger_digest')
        require(document == expected, 'historical source ledger metadata or seal differs')
        require(self._ledger_file(path).raw == file.raw, 'historical ledger changed during validation')
        self._assert_installed()
        return document

    def verify_source_row(self, job: Any, row: dict[str, Any]) -> tuple[Any,dict[str,Any]]:
        self._assert_installed()
        observation = self.access.historical_pair(row['source_path'],row['copy_path'])
        verified, actual = self._original_pair(job,observation.source,observation.copy,
                                               commit=row['expected_git_commit'],
                                               expected_execution_digest=row['execution_digest'])
        expected = {**row,'source_path':str(observation.source),'copy_path':str(observation.copy),
                    'copy_evidence_digest':observation.observed_copy_digest}
        require(actual == expected, 'current fit metadata differs from attested historical source')
        after = self.access.historical_pair(row['source_path'],row['copy_path'])
        require(after == observation, 'source changed during scientific evidence validation')
        self._assert_installed()
        return verified, actual

    def reverify_source_ledger(self, document: object) -> dict[str,Any]:
        self._assert_installed()
        original = self.metadata_source_ledger(self.ledger_logical_path,self.ledger_sha256)
        require(type(document) is dict and document == original, 'requested ledger is not the pinned historical document')
        for job,row in zip(self.W.existing_exp2a_jobs(),original['sources'],strict=True):
            self.verify_source_row(job,row)
        require(self.metadata_source_ledger(self.ledger_logical_path,self.ledger_sha256) == original,
                'historical authority changed during full reconciliation')
        return original

    def load_source_ledger(self, path: str | Path) -> dict[str,Any]:
        original = self.metadata_source_ledger(path,self.ledger_sha256)
        return self.reverify_source_ledger(original)


class PreflightReaders:
    """Interpret original preflight metadata without rewriting its bytes/seal."""

    def __init__(self, access: Any, sources: SourceReaders, launch: Any, storage: Any, *,
                 preflight_logical_path: str = PREFLIGHT_LOGICAL_PATH,
                 preflight_sha256: str = PREFLIGHT_SHA256) -> None:
        self.access,self.sources,self.X,self.storage = access,sources,launch,storage
        self.W = sources.W
        self.logical_path,self.sha256 = preflight_logical_path,preflight_sha256
        self.roots = {name:self.W.WORKSPACE_ROOT/folder for name,folder in PRODUCTION_FOLDERS.items()}
        self.logical_roots = {name:str(OLD_ROOT/folder) for name,folder in PRODUCTION_FOLDERS.items()}
        self._active = False
        self._bindings = {'validate_exp2a_repair_preflight':self.validate_preflight,
                          'check_preflight_storage':self.check_storage}
        self._expected = {name:getattr(launch,name) for name in self._bindings}

    def _assert_installed(self) -> None:
        require(self._active and all(getattr(self.X,name) is value for name,value in self._bindings.items()),
                'preflight reader used outside exact installed scope')
        self.sources._assert_installed()

    @contextmanager
    def installed(self) -> Iterator['PreflightReaders']:
        require(not self._active and all(getattr(self.X,name) is value for name,value in self._expected.items()),
                'preflight seams changed before installation')
        before_keys = set(vars(self.X))
        for name,value in self._bindings.items():setattr(self.X,name,value)
        self._active = True
        failure: BaseException | None = None
        try:
            self._assert_installed()
            yield self
        except BaseException as exc:
            failure = exc
            raise
        finally:
            changed = set(vars(self.X)) != before_keys or any(
                getattr(self.X,name,None) is not value for name,value in self._bindings.items())
            for name,value in self._expected.items():setattr(self.X,name,value)
            self._active = False
            if changed or any(getattr(self.X,name) is not value for name,value in self._expected.items()):
                raise MetadataRefused('preflight adapter changed or failed restoration') from failure

    def _report(self, path: str | Path) -> Any:
        self._assert_installed()
        if PureWindowsPath(str(path)).is_relative_to(OLD_ROOT):
            file = self.access.historical_file(str(path))
        else:
            file = self.access.historical_file_at(Path(path))
        require(file.logical_path == self.logical_path and file.sha256 == self.sha256 and
                file.physical_path == self.roots['preflight']/self.X.PREFLIGHT_FILE,
                'preflight identity differs from fixed historical binding')
        return file

    def _storage(self, report: dict[str,Any], roots: dict[str,Path]) -> None:
        S = self.storage
        storage = S._keys(report.get('storage'),{'minimum_free_bytes','roots'},'historical storage')
        minimum = S._minimum(storage['minimum_free_bytes'])
        require(minimum == 8*1024**3, 'registered storage floor differs from8GiB')
        snapshots = S._keys(storage['roots'],set(PRODUCTION_FOLDERS),'historical root snapshots')
        require(set(roots) == set(self.roots) and all(Path(roots[k]) == self.roots[k] for k in self.roots),
                'requested storage roots differ from fixed relocation')
        for name,row in snapshots.items():
            S._keys(row,{'path','writable','free_bytes'},'historical root snapshot')
            require(row['path'] == self.logical_roots[name] and row['writable'] is True and
                    type(row['free_bytes']) is int and row['free_bytes'] >= minimum,
                    'historical storage snapshot differs')
        # The old report is already pinned. Give the unchanged low-level guard
        # the separately verified current roots, not a forged report dictionary.
        S._check_roots({name:str(path) for name,path in self.roots.items()},roots,minimum)

    def check_storage(self, source_path: str | Path, source_sha256: str, *, roots: dict[str,Path]) -> None:
        require(source_sha256 == self.sha256, 'pre-fit storage source pin differs')
        file = self._report(source_path)
        report = file.document()
        require(type(report.get('week8_preflight_schema_version')) is int and
                report['week8_preflight_schema_version'] == 1 and report.get('status') == 'ready' and
                report.get('launch_performed') is False, 'pre-fit storage source schema differs')
        self._storage(report,roots)
        require(self._report(source_path).raw == file.raw, 'preflight changed during storage check')

    def _canary(self, report: dict[str,Any]) -> None:
        X = self.X
        canary = X.L._strict_keys(report['sync_canary'],{'source_path','destination_path','sha256','size_bytes'},what='historical sync canary')
        receipt = X.L._strict_keys(report['sync_receipt'],{'schema_version','destination_identity','destination_path','sha256','size_bytes'},what='historical sync receipt')
        require(type(receipt['schema_version']) is int and receipt['schema_version'] == X.P.SYNC_RECEIPT_SCHEMA_VERSION,
                'sync receipt schema differs')
        identity = X.P._validate_destination_identity(receipt['destination_identity'])
        expected_paths = {'source_path':str(OLD_ROOT/PRODUCTION_FOLDERS['preflight']/X.P.SYNC_CANARY_FILE),
                          'destination_path':str(OLD_ROOT/PRODUCTION_FOLDERS['sync']/X.P.SYNC_CANARY_FILE)}
        require(all(canary[k] == value for k,value in expected_paths.items()),'historical canary paths differ')
        left,right = (self.access.historical_file(canary[k]) for k in ('source_path','destination_path'))
        require(left.raw == right.raw and not os.path.samefile(left.physical_path,right.physical_path),
                'canary twins are not independent matching bytes')
        require(type(canary['size_bytes']) is int and canary['size_bytes'] >= 0 and
                len(left.raw) == canary['size_bytes'] == receipt['size_bytes'] and
                left.sha256 == right.sha256 == canary['sha256'] == receipt['sha256'] and
                receipt['destination_path'] == canary['destination_path'], 'canary receipt binding differs')
        require(left.document() == {'canary_schema_version':1,'destination_identity':identity,
                                   'plan_sha256':report['binding_sha256']},'canary source binding differs')

    def validate_preflight(self, path: str | Path, *, output_root: str | Path,
                           sync_root: str | Path, expected_git_commit: str) -> Any:
        file = self._report(path)
        X,W = self.X,self.W
        report = X.L._strict_keys(file.document(),{
            'week8_preflight_schema_version','exp2a_repair_preflight_schema_version','status',
            'launch_performed','inputs','budget','plan_digest','binding_sha256','environment',
            'storage','attempt_timeout_seconds','common_control_root','sync_canary','sync_receipt',
        },what='relocated historical E2A preflight')
        require(file.raw == X.L._pretty_json_bytes(report),'historical preflight is not canonical')
        require(type(report['week8_preflight_schema_version']) is int and report['week8_preflight_schema_version'] == 1 and
                type(report['exp2a_repair_preflight_schema_version']) is int and report['exp2a_repair_preflight_schema_version'] == 1 and
                report['status'] == 'ready' and report['launch_performed'] is False,'historical preflight readiness differs')
        inputs = X.L._strict_keys(report['inputs'],{'plan','source_ledger'},what='historical preflight inputs')
        files = {}
        for name,row in inputs.items():
            X.L._strict_keys(row,{'path','sha256'},what='historical input pin')
            files[name] = self.access.historical_file(row['path'])
            require(files[name].sha256 == row['sha256'],'historical input SHA differs')
        plan = W.load_exp2a_repair_plan(files['plan'].physical_path)
        ledger = self.sources.load_source_ledger(files['source_ledger'].physical_path)
        budget = {'new_physical_fits':plan['counts']['new_physical_fits'],
                  'new_member_models':plan['counts']['new_member_model_trainings'],
                  'new_baseline_fits':plan['counts']['new_baseline_fits'],
                  'new_repair_fits':plan['counts']['new_repair_fits'],
                  'historical_sources_reopened':ledger['reused_fit_count'],
                  'interpretation':'exact inventory counts; not a runtime or GPU-hour estimate'}
        require(report['budget'] == budget and report['attempt_timeout_seconds'] == 3600,
                'historical fit budget or timeout differs')
        timeout = X.L._positive_number(report['attempt_timeout_seconds'],what='historical attempt timeout')
        binding = W._seal({'inputs':inputs,'plan_digest':plan['plan_digest'],
                           'attempt_timeout_seconds':timeout},'binding_sha256')['binding_sha256']
        require(report['plan_digest'] == plan['plan_digest'] and report['binding_sha256'] == binding,
                'historical preflight seal differs')
        require(report['environment'] == X._environment(expected_git_commit), 'historical execution environment differs')
        require(report['common_control_root'] == str(OLD_ROOT/'week7-production-control'),
                'historical common lease root differs')
        require(W._project_path(output_root,directory=True) == self.roots['output'] and
                W._project_path(sync_root,directory=True) == self.roots['sync'],
                'requested launch roots differ')
        roots = {name:W._project_path(path,directory=True) for name,path in self.roots.items()}
        X._protect(roots,{name:{'path':str(file.physical_path),'sha256':file.sha256} for name,file in files.items()})
        self._storage(report,roots)
        self._canary(report)
        for name,source in files.items():
            for role in ('preflight','sync'):
                destination = self.access.historical_file_at(roots[role]/f'exp2a_input_{name}.json')
                require(destination.raw == source.raw and
                        not os.path.samefile(destination.physical_path,source.physical_path),
                        'historical input independent copy differs')
        report_copy = self.access.historical_file_at(roots['sync']/X.PREFLIGHT_FILE)
        require(report_copy.raw == file.raw and not os.path.samefile(file.physical_path,report_copy.physical_path),
                'historical preflight twin differs')
        require(self._report(path).raw == file.raw,'preflight changed during full validation')
        self._assert_installed()
        return X.ValidatedExp2APreflight(file.physical_path,file.sha256,report,roots,expected_git_commit)


class CheckpointReaders:
    """Bridge exactly the preserved epoch and one explicitly relocated epoch.

    Old documents remain unchanged; new records carry actual physical paths and
    an explicit relocation binding. Original lease validators retain authority.
    """

    def __init__(self, access: Any, preflight: PreflightReaders, *,
                 old_token: str = OLD_LEASE_TOKEN,
                 old_sha256: str = OLD_CHECKPOINT_SHA256,
                 old_checkpoint_digest: str = OLD_CHECKPOINT_DIGEST,
                 old_context_digest: str = OLD_CONTEXT_DIGEST,
                 policy_sha256: str = POLICY_SHA256) -> None:
        self.access,self.preflight = access,preflight
        self.sources,self.W,self.X = preflight.sources,preflight.W,preflight.X
        self.old_token,self.old_sha256 = old_token,old_sha256
        self.old_checkpoint_digest,self.old_context_digest = old_checkpoint_digest,old_context_digest
        self.policy_sha256 = policy_sha256
        self.roots = {k:preflight.roots[k] for k in ('output','staging','sync')}
        self._active = False
        self._bindings = {'_read_start':self.read_start,
                          'write_exp2a_repair_start_checkpoint':self.write_start,
                          '_verify_prior_start':self.verify_prior_start}
        self._expected = {name:getattr(self.X,name) for name in self._bindings}

    def _assert_installed(self) -> None:
        require(self._active and all(getattr(self.X,k) is v for k,v in self._bindings.items()),
                'checkpoint reader used outside exact installed scope')
        self.preflight._assert_installed()

    @contextmanager
    def installed(self) -> Iterator['CheckpointReaders']:
        require(not self._active and all(getattr(self.X,k) is v for k,v in self._expected.items()),
                'checkpoint seam changed before installation')
        before_keys = set(vars(self.X))
        for k,v in self._bindings.items():setattr(self.X,k,v)
        self._active = True
        failure: BaseException | None = None
        try:
            self._assert_installed()
            yield self
        except BaseException as exc:
            failure = exc
            raise
        finally:
            changed = set(vars(self.X)) != before_keys or any(
                getattr(self.X,k,None) is not v for k,v in self._bindings.items())
            for k,v in self._expected.items():setattr(self.X,k,v)
            self._active = False
            if changed or any(getattr(self.X,k) is not v for k,v in self._expected.items()):
                raise MetadataRefused('checkpoint adapter changed or failed restoration') from failure

    def _old_twins(self, relative: Path) -> tuple[Any,Any]:
        left,right = (self.access.historical_file_at(self.roots[role]/relative)
                      for role in ('output','sync'))
        require(left.raw == right.raw and not os.path.samefile(left.physical_path,right.physical_path),
                'historical checkpoint/context twins differ')
        return left,right

    def historical_start(self, path: str | Path, *, expected_sha256: str,
                         expected_git_commit: str, lease_mode: str) -> tuple[dict,dict,dict]:
        self._assert_installed()
        require(lease_mode in ('active','historical'), 'unknown checkpoint lease verification mode')
        X,W = self.X,self.W
        relative = Path(W.START_DIRECTORY)/f'{self.old_token}.json'
        require(Path(path) == self.roots['output']/relative,
                'old checkpoint must use its prescribed current local path')
        require(expected_sha256 == self.old_sha256, 'old checkpoint dispatch pin differs')
        file,twin = self._old_twins(relative)
        require(file.sha256 == self.old_sha256, 'original checkpoint file pin differs')
        document = file.document()
        require(file.raw == X.L._pretty_json_bytes(document), 'original checkpoint bytes not canonical')
        report_file = self.preflight._report(self.preflight.logical_path)
        report = report_file.document()
        ledger_file = self.sources._ledger_file()
        ledger = self.sources.metadata_source_ledger(ledger_file.physical_path,self.sources.ledger_sha256)
        expected_roots = {k:self.preflight.logical_roots[k] for k in self.roots}
        lease_path = str(OLD_ROOT/'week7-production-control/leases'/f'{W.COMMON_LEASE_NAME}.lease.json')
        original_lease_file = self.access.historical_file(lease_path)
        original_lease = original_lease_file.document()
        require(original_lease['token'] == self.old_token and
                original_lease['lease_name'] == W.COMMON_LEASE_NAME,
                'original lease identity differs')
        current_lease = (X._lease_record(self.old_token) if lease_mode == 'active'
                         else X._historical_lease_record(self.old_token))
        lease = {'path':lease_path,'sha256':original_lease_file.sha256,
                 'name':W.COMMON_LEASE_NAME,'token':self.old_token,
                 'started_at':original_lease['timestamp_utc']}
        physical_lease_path = W.COMMON_LEASE_ROOT/'leases'/f'{W.COMMON_LEASE_NAME}.lease.json'
        require(current_lease == {**lease,'path':str(physical_lease_path)},
                'current lease proof differs from preserved lease')
        inputs = report['inputs']
        physical_inputs = {}
        for name,row in inputs.items():
            source = self.access.historical_file(row['path'])
            require(source.sha256 == row['sha256'], 'checkpoint preflight input pin differs')
            physical_inputs[name] = {'path':str(source.physical_path),'sha256':source.sha256}
        require(inputs['source_ledger'] == {'path':ledger_file.logical_path,'sha256':ledger_file.sha256},
                'checkpoint preflight ledger binding differs')
        roots = {k:W._project_path(v,directory=True) for k,v in self.roots.items()}
        X._protect({'preflight':report_file.physical_path.parent,**roots},physical_inputs)
        environment = (X._environment(expected_git_commit) if lease_mode == 'active'
                       else X._released_environment(expected_git_commit))
        payload = {
            'exp2a_repair_start_schema_version':1,
            'purpose':'source_verified_week8_exp2a_repair_start',
            'plan_digest':W.build_exp2a_repair_plan()['plan_digest'],
            'preflight':{'path':report_file.logical_path,'sha256':report_file.sha256,
                         'binding_sha256':report['binding_sha256']},
            'source_ledger':{'path':ledger_file.logical_path,'sha256':ledger_file.sha256,
                             'ledger_digest':ledger['ledger_digest']},
            'environment':environment,'roots':expected_roots,'attempt_timeout_seconds':3600.0,
            'lease':lease,'fixed_worker':'bu.experiments.week8_exp2a_repair_launch._fit_worker',
            'supervisor_required':'bu.experiments.supervisor.run_isolated_attempt',
            'automatic_retry_allowed':False,
        }
        context = X._execution_context(payload)
        expected = W._seal({**payload,'execution_context_digest':context['execution_context_digest']},
                           'checkpoint_digest')
        require(document == expected and document['checkpoint_digest'] == self.old_checkpoint_digest and
                context['execution_context_digest'] == self.old_context_digest,
                'original checkpoint/context seal or scientific settings differ')
        context_file,context_twin = self._old_twins(Path(W.CONTEXT_FILE))
        require(context_file.document() == context and context_file.raw == X.L._pretty_json_bytes(context),
                'original execution context differs from preserved checkpoint')
        require(self._old_twins(relative) == (file,twin) and
                self._old_twins(Path(W.CONTEXT_FILE)) == (context_file,context_twin),
                'original checkpoint/context changed during verification')
        require(self.preflight._report(self.preflight.logical_path).raw == report_file.raw and
                self.sources._ledger_file().raw == ledger_file.raw and
                self.access.historical_file(lease_path).raw == original_lease_file.raw,
                'historical checkpoint dependencies changed during verification')
        after_lease = (X._lease_record(self.old_token) if lease_mode == 'active'
                       else X._historical_lease_record(self.old_token))
        require(after_lease == current_lease, 'lease proof changed during historical checkpoint verification')
        self._assert_installed()
        return document,ledger,roots

    def relocation_binding(self) -> dict[str,Any]:
        self._assert_installed()
        return {'relocation_schema_version':1,
                'attestation_sha256':self.access.attestation_sha256,
                'policy_sha256':self.policy_sha256,
                'original_lease_token':self.old_token,
                'original_checkpoint_sha256':self.old_sha256,
                'original_checkpoint_digest':self.old_checkpoint_digest,
                'original_execution_context_digest':self.old_context_digest,
                'context_file':RELOCATION_CONTEXT_FILE}

    def _checkpoint_inventory(self, names: set[str]) -> None:
        for role in ('output','sync'):
            folder = self.W._project_path(self.roots[role]/self.W.START_DIRECTORY,directory=True)
            paths = list(folder.iterdir())
            require({p.name for p in paths} == names,
                    'checkpoint inventory contains another epoch or incomplete publication')
            for path in paths:self.W._project_path(path,directory=False)

    def _current_twins(self, relative: Path) -> tuple[dict[str,Any],bytes]:
        paths = tuple(self.W._project_path(self.roots[role]/relative,directory=False)
                      for role in ('output','sync'))
        def stamp(path: Path) -> tuple:
            info = path.lstat()
            require(info.st_nlink == 1, 'current checkpoint/context has another hardlink')
            return (info.st_dev,info.st_ino,info.st_mode,info.st_size,info.st_mtime_ns,
                    info.st_ctime_ns,getattr(info,'st_birthtime_ns',None))
        before = tuple(stamp(p) for p in paths)
        self.X._same_file_copy(*paths)
        raw,twin = (p.read_bytes() for p in paths)
        document = self.X.read_json(paths[0])
        require(type(document) is dict and raw == twin == self.X.L._pretty_json_bytes(document),
                'current checkpoint/context twins are not exact canonical objects')
        require(before == tuple(stamp(p) for p in paths) and
                all(p.read_bytes() == raw for p in paths),
                'current checkpoint/context moved during read')
        for path in paths:self.W._project_path(path,directory=False)
        return document,raw

    def _old_for_new(self, commit: str) -> tuple[dict,dict,dict]:
        return self.historical_start(self.roots['output']/self.W.START_DIRECTORY/f'{self.old_token}.json',
                                     expected_sha256=self.old_sha256,expected_git_commit=commit,
                                     lease_mode='historical')

    def _new_document(self, original: dict[str,Any], lease: dict[str,Any]) -> tuple[dict,dict]:
        X,W = self.X,self.W
        ledger_file = self.sources._ledger_file()
        report_file = self.preflight._report(self.preflight.logical_path)
        payload = {k:copy.deepcopy(v) for k,v in original.items()
                   if k not in {'checkpoint_digest','execution_context_digest'}}
        payload.update({'exp2a_repair_start_schema_version':2,
                        'preflight':{**payload['preflight'],'path':str(report_file.physical_path)},
                        'source_ledger':{**payload['source_ledger'],'path':str(ledger_file.physical_path)},
                        'roots':{k:str(v) for k,v in self.roots.items()},
                        'lease':dict(lease),'relocation':self.relocation_binding()})
        context = X._execution_context(payload)
        require(context['execution_context_digest'] != self.old_context_digest,
                'relocated context unexpectedly reproduces the historical digest')
        document = W._seal({**payload,'execution_context_digest':context['execution_context_digest']},
                           'checkpoint_digest')
        return document,context

    def write_start(self, *, source_ledger_path: str | Path, expected_git_commit: str,
                    output_root: str | Path, staging_root: str | Path, sync_root: str | Path,
                    attempt_timeout_seconds: float, lease: Any, preflight_report: str | Path) -> Path:
        self._assert_installed()
        X,W = self.X,self.W
        require(type(lease) is X.BatchLease and not lease._released,
                'relocated start requires an exact active BatchLease')
        active = W.COMMON_LEASE_ROOT/'leases'/f'{W.COMMON_LEASE_NAME}.lease.json'
        require(lease.name == W.COMMON_LEASE_NAME and lease.path.resolve() == active.resolve() and
                lease.history_dir.resolve() == (active.parent/'history').resolve() and
                lease.token != self.old_token and re.fullmatch('[0-9a-f]{32}',lease.token) is not None,
                'relocated start must use a new shared production lease')
        self._checkpoint_inventory({f'{self.old_token}.json'})
        require(all(not os.path.lexists(self.roots[role]/RELOCATION_CONTEXT_FILE) for role in ('output','sync')),
                'relocated context already exists; replay or healing forbidden')
        ready = self.preflight.validate_preflight(preflight_report,output_root=output_root,
                                                  sync_root=sync_root,expected_git_commit=expected_git_commit)
        timeout = X.L._positive_number(attempt_timeout_seconds,what='relocated attempt timeout')
        ledger_file = self.sources._ledger_file(source_ledger_path)
        require(ledger_file.logical_path == self.sources.ledger_logical_path and
                ready.report['inputs']['source_ledger'] == {'path':ledger_file.logical_path,'sha256':ledger_file.sha256} and
                W._project_path(staging_root,directory=True) == self.roots['staging'] and
                timeout == ready.report['attempt_timeout_seconds'] == 3600.0,
                'relocated start inputs/timeout/staging differ from original preflight')
        original,_,_ = self._old_for_new(expected_git_commit)
        lease_row = X._lease_record(lease.token)
        require(X.read_json(active)['pid'] == os.getpid(), 'relocated lease belongs to another launcher')
        document,context = self._new_document(original,lease_row)
        require(X._environment(expected_git_commit) == original['environment'],
                'relocated scientific environment differs from original epoch')
        self._checkpoint_inventory({f'{self.old_token}.json'})
        require(X._lease_record(lease.token) == lease_row,
                'new lease changed before checkpoint publication')
        for role in ('sync','output'):
            require(not os.path.lexists(self.roots[role]/RELOCATION_CONTEXT_FILE),
                    'relocated context appeared before publication')
            X.atomic_write_json(self.roots[role]/RELOCATION_CONTEXT_FILE,context)
        relative = Path(W.START_DIRECTORY)/f'{lease.token}.json'
        for role in ('sync','output'):
            X.atomic_write_json(self.roots[role]/relative,document)
        path = self.roots['output']/relative
        observed,_,_ = self._new_start(path,expected_sha256=_sha(X.L._pretty_json_bytes(document)),
                                     expected_git_commit=expected_git_commit,lease_mode='active')
        require(observed == document, 'published relocated checkpoint differs')
        return path

    def _new_start(self, path: str | Path, *, expected_sha256: str,
                   expected_git_commit: str, lease_mode: str) -> tuple[dict,dict,dict]:
        self._assert_installed()
        require(lease_mode in ('active','historical'), 'unknown relocated lease verification mode')
        X,W = self.X,self.W
        path = Path(path)
        token = path.stem
        require(re.fullmatch('[0-9a-f]{32}',token) is not None and token != self.old_token and
                path == self.roots['output']/W.START_DIRECTORY/f'{token}.json',
                'relocated checkpoint must use its current canonical local path')
        names = {f'{self.old_token}.json',f'{token}.json'}
        self._checkpoint_inventory(names)
        relative = Path(W.START_DIRECTORY)/path.name
        document,raw = self._current_twins(relative)
        require(_sha(raw) == X.L._lower_sha256(expected_sha256,what='relocated checkpoint SHA'),
                'relocated checkpoint changed after dispatch')
        original,ledger,roots = self._old_for_new(expected_git_commit)
        lease = X._lease_record(token) if lease_mode == 'active' else X._historical_lease_record(token)
        expected,context = self._new_document(original,lease)
        environment = X._environment(expected_git_commit) if lease_mode == 'active' else X._released_environment(expected_git_commit)
        require(environment == original['environment'], 'new epoch scientific environment changed')
        require(raw == X.L._pretty_json_bytes(expected), 'relocated checkpoint schema/seal/original binding differs')
        context_doc,context_raw = self._current_twins(Path(RELOCATION_CONTEXT_FILE))
        require(context_raw == X.L._pretty_json_bytes(context), 'relocated context differs from checkpoint')
        require(self._current_twins(relative) == (document,raw) and
                self._current_twins(Path(RELOCATION_CONTEXT_FILE)) == (context_doc,context_raw),
                'relocated checkpoint/context changed across verification')
        after = X._lease_record(token) if lease_mode == 'active' else X._historical_lease_record(token)
        require(after == lease, 'new lease proof changed during checkpoint verification')
        self._checkpoint_inventory(names)
        self._assert_installed()
        return document,ledger,roots

    def verify_prior_start(self, checkpoint_digest: str, current: dict[str,Any], roots: dict[str,Path]) -> None:
        self._assert_installed()
        X,W = self.X,self.W
        X.L._lower_sha256(checkpoint_digest,what='prior checkpoint digest')
        require(set(roots) in (set(self.roots),set(self.preflight.roots)) and
                all(roots[k] == self.preflight.roots[k] for k in roots),
                'prior checkpoint roots differ from fixed relocation')
        token = current['lease']['token']
        require(type(token) is str and re.fullmatch('[0-9a-f]{32}',token) is not None,
                'prior checkpoint token is not canonical')
        commit = current['environment']['git_commit']
        if token == self.old_token:
            self._checkpoint_inventory({f'{self.old_token}.json'})
            verified,_,_ = self.historical_start(self.roots['output']/W.START_DIRECTORY/f'{token}.json',
                                                expected_sha256=self.old_sha256,expected_git_commit=commit,
                                                lease_mode='active')
        else:
            relative = Path(W.START_DIRECTORY)/f'{token}.json'
            _,raw = self._current_twins(relative)
            verified,_,_ = self._new_start(self.roots['output']/relative,expected_sha256=_sha(raw),
                                         expected_git_commit=commit,lease_mode='historical')
        require(current == verified and checkpoint_digest in {self.old_checkpoint_digest,verified['checkpoint_digest']},
                'prior checkpoint is not the exact preserved or sole relocated epoch')
        self._assert_installed()

    def read_start(self, path: str | Path, *, expected_sha256: str,
                   expected_git_commit: str, released: bool):
        self._assert_installed()
        require(type(released) is bool, 'checkpoint release flag is not boolean')
        if released:self.X._no_active_lease()
        reader = self.historical_start if Path(path).stem == self.old_token else self._new_start
        return reader(path,expected_sha256=expected_sha256,expected_git_commit=expected_git_commit,
                      lease_mode='historical' if released else 'active')


class CompletedJobReaders:
    """Validate old/new job metadata with original fit and pairing validators."""

    def __init__(self, access: Any, checkpoints: CheckpointReaders) -> None:
        self.access,self.checkpoints = access,checkpoints
        self.sources,self.X,self.W = checkpoints.sources,checkpoints.X,checkpoints.W
        self.S = self.sources.S
        self._active = False
        self._bindings = {'_baseline':self.baseline,'_local_completed':self.local_completed}
        self._expected = {k:getattr(self.X,k) for k in self._bindings}
        self._pair_validator = self.S._source_pair
        self._science_pair = self.X._assert_baseline_pair
        self._worker = self.X._fit_worker

    def _assert_installed(self) -> None:
        require(self._active and all(getattr(self.X,k) is v for k,v in self._bindings.items()),
                'completed-job readers used outside exact installed scope')
        require(self.S._source_pair is self._pair_validator and
                self.X._assert_baseline_pair is self._science_pair and self.X._fit_worker is self._worker,
                'original scientific validator or worker changed')
        self.checkpoints._assert_installed()

    @contextmanager
    def installed(self) -> Iterator['CompletedJobReaders']:
        require(not self._active and all(getattr(self.X,k) is v for k,v in self._expected.items()),
                'completed-job seams changed before installation')
        before_keys = set(vars(self.X))
        for k,v in self._bindings.items():setattr(self.X,k,v)
        self._active = True
        failure: BaseException | None = None
        try:
            self._assert_installed()
            yield self
        except BaseException as exc:
            failure = exc
            raise
        finally:
            changed = set(vars(self.X)) != before_keys or any(
                getattr(self.X,k,None) is not v for k,v in self._bindings.items())
            changed = changed or self.S._source_pair is not self._pair_validator or self.X._assert_baseline_pair is not self._science_pair or self.X._fit_worker is not self._worker
            for k,v in self._expected.items():setattr(self.X,k,v)
            self._active = False
            if changed or any(getattr(self.X,k) is not v for k,v in self._expected.items()):
                raise MetadataRefused('completed-job adapter changed or failed restoration') from failure

    def _arguments(self, job: Any, ledger: dict, roots: dict, commit: str, current: dict) -> None:
        self._assert_installed()
        require(job.as_record() == self.X._new_job(job.job_id).as_record(), 'unregistered completed/repair job')
        require(set(roots) in (set(self.checkpoints.roots),set(self.checkpoints.preflight.roots)) and
                all(roots[k] == self.checkpoints.preflight.roots[k] for k in roots),
                'completed-job roots differ from fixed relocation')
        require(commit == current['environment']['git_commit'], 'completed-job execution commit differs')
        require(ledger == self.sources.metadata_source_ledger(self.sources.ledger_logical_path,
                                                              self.sources.ledger_sha256),
                'completed-job historical ledger differs')

    def _epoch(self, result: dict, current: dict) -> tuple[bool,str]:
        digest = result.get('checkpoint_digest')
        if digest == self.checkpoints.old_checkpoint_digest:
            return True,self.checkpoints.old_context_digest
        require(current.get('exp2a_repair_start_schema_version') == 2 and
                digest == current.get('checkpoint_digest'), 'job belongs to an unregistered checkpoint epoch')
        return False,current['execution_context_digest']

    def _baseline_material(self, job: Any, ledger: dict, roots: dict, commit: str,
                           current: dict) -> tuple[Any,dict,dict | None]:
        X,W,S = self.X,self.W,self.S
        baseline = next(candidate for candidate in W.registered_exp2a_jobs()
                        if candidate.unit == job.unit and candidate.seed == job.seed and candidate.arm == 'baseline')
        historical = None
        if W.source_kind(baseline) is not None:
            historical = next(row for row in ledger['sources'] if row['job']['job_id'] == baseline.job_id)
            verified,actual = self.sources.verify_source_row(baseline,historical)
            origin = {'kind':'historical_source_ledger','ledger_sha256':self.sources.ledger_sha256,
                      'source':copy.deepcopy(historical)}
        else:
            local,remote = (roots[role]/'jobs'/baseline.job_id for role in ('output','sync'))
            result_path = W._project_path(local/'job_result.json',directory=False)
            result = X.read_json(result_path)
            require(type(result) is dict, 'baseline result is not an object')
            preserved = self.access.has_historical_file(result_path)
            if preserved:
                require(self.access.historical_file_at(result_path).document() == result,
                        'preserved baseline metadata differs')
            old,context = self._epoch(result,current)
            require(old == preserved, 'baseline epoch differs from its preserved inventory membership')
            observation = None
            if old:
                # All preserved baselines were durably synced; the sole orphan
                # is a feature repair. No missing-pair discovery/fallback exists.
                observation = self.access.historical_pair_at(local,remote)
                require(self.access.historical_file_at(result_path).document() == result,
                        'preserved baseline metadata differs')
            verified,actual = self._pair_validator(baseline,local,remote,commit=commit)
            self.checkpoints.verify_prior_start(result['checkpoint_digest'],current,roots)
            expected_result = X._result_record(baseline,verified,commit=commit,
                    checkpoint_digest=result['checkpoint_digest'],binding=None,execution_context_digest=context)
            require(X.L._pretty_json_bytes(result) == X.L._pretty_json_bytes(expected_result),
                    'baseline result does not bind its actual checkpoint/context')
            if old:
                require(actual['source_tree_digest'] == actual['copy_tree_digest'] == observation.policy.content_digest and
                        actual['copy_evidence_digest'] == observation.observed_copy_digest and
                        self.access.historical_pair_at(local,remote) == observation,
                        'preserved baseline changed during scientific verification')
                historical = {**actual,'source_path':observation.policy.logical_source,
                              'copy_path':observation.policy.logical_copy,
                              'copy_evidence_digest':observation.historical_copy_digest}
                origin = {'kind':'preserved_epoch001_baseline','checkpoint_digest':result['checkpoint_digest'],
                          'execution_context_digest':context,'source':historical}
            else:
                origin = {'kind':'relocated_epoch_baseline','checkpoint_digest':result['checkpoint_digest'],
                          'execution_context_digest':context}
        binding = {'baseline_binding_schema_version':2,'source':actual,'origin':origin,
                   'relocation':self.checkpoints.relocation_binding()}
        self._assert_installed()
        return verified,binding,historical

    def baseline(self, job: Any, ledger: dict, roots: dict, commit: str, current: dict) -> tuple[Any,dict]:
        self._arguments(job,ledger,roots,commit,current)
        require(job.arm != 'baseline', 'baseline lookup requires a repair job')
        verified,binding,_ = self._baseline_material(job,ledger,roots,commit,current)
        return verified,binding

    def local_completed(self, job: Any, start: dict, ledger: dict, roots: dict,
                        expected_git_commit: str) -> dict:
        self._arguments(job,ledger,roots,expected_git_commit,start)
        X,W,S = self.X,self.W,self.S
        local = W._project_path(roots['output']/'jobs'/job.job_id,directory=True)
        S._plain_tree(local)
        before = X.B._job_tree_digest(local)
        result_path = W._project_path(local/'job_result.json',directory=False)
        result = X.L._strict_keys(X.read_json(result_path),{
            'exp2a_repair_result_schema_version','job','expected_git_commit','checkpoint_digest',
            'execution_context_digest','fit_evidence_digest','baseline_source'},what='relocated completed result')
        preserved = self.access.has_historical_file(result_path)
        old_file = self.access.historical_file_at(result_path) if preserved else None
        if old_file is not None:
            require(old_file.document() == result, 'preserved job result differs from its attestation')
        old,context = self._epoch(result,start)
        require(old == (preserved or job.job_id == ORPHAN_JOB_ID),
                'job epoch differs from the attested roster and sole orphan')
        if old and job.job_id == ORPHAN_JOB_ID:
            require(job.arm == 'feature_repair', 'registered unpaired orphan arm differs')
        verified = X.F.load_fit_evidence(local,expected_git_commit=expected_git_commit)
        S._match_fit(verified,job)
        binding = None
        if job.arm != 'baseline':
            baseline,current_binding,historical_binding = self._baseline_material(job,ledger,roots,expected_git_commit,start)
            self._science_pair(job,verified,baseline,what='recovered repair pairing')
            if old:
                require(historical_binding is not None, 'old repair cannot bind a later baseline')
                binding = historical_binding
            else:binding = current_binding
        self.checkpoints.verify_prior_start(result['checkpoint_digest'],start,roots)
        expected_result = X._result_record(job,verified,commit=expected_git_commit,
                    checkpoint_digest=result['checkpoint_digest'],binding=binding,execution_context_digest=context)
        require(X.L._pretty_json_bytes(result) == X.L._pretty_json_bytes(expected_result),
                'completed job result differs from its exact epoch and baseline provenance')
        after = X.B._job_tree_digest(local)
        require(before == after and X.read_json(result_path) == result,
                'completed local tree changed during verification')
        if old_file is not None:
            require(self.access.historical_file_at(result_path) == old_file,
                    'preserved local result changed during verification')
        self._assert_installed()
        return {'result':result,'source_tree_digest':after,'execution_digest':verified.execution_digest}


class EventReaders:
    """One exact original prefix and one new-context tail; never heal copies."""

    def __init__(self, access: Any, checkpoints: CheckpointReaders, *,
                 old_count: int = OLD_EVENT_COUNT, old_started: int = 150,
                 old_synced: int = 149, old_chain_sha256: str = OLD_EVENT_CHAIN_SHA256,
                 old_tail_sha256: str = OLD_EVENT_TAIL_SHA256) -> None:
        self.access,self.checkpoints = access,checkpoints
        self.X,self.W = checkpoints.X,checkpoints.W
        self.old_count,self.old_started,self.old_synced = old_count,old_started,old_synced
        self.old_chain_sha256,self.old_tail_sha256 = old_chain_sha256,old_tail_sha256
        require(all(type(n) is int and n > 0 for n in (old_count,old_started,old_synced)) and
                old_count == old_started+old_synced and old_started == old_synced+1,
                'original event counts differ from one unsynced complete orphan')
        self._original_validate = self.X._validate_event
        self._original_append = self.X._append_event
        self._bindings = {'_validate_event':self.validate_event,'_load_events':self.load_events}
        self._expected = {k:getattr(self.X,k) for k in self._bindings}
        self._active = False
        self._old_raw: tuple[bytes,...] = ()
        self._old_starts: dict[str,int] = {}
        self._old_syncs: dict[str,int] = {}
        self._admitted_start: bytes | None = None
        self._new_context: tuple[str,bytes] | None = None
        self._new_checkpoint_digest: str | None = None

    def _assert_installed(self) -> None:
        require(self._active and all(getattr(self.X,k) is v for k,v in self._bindings.items()) and
                self.X._append_event is self._original_append,
                'event readers used outside exact installed scope')
        self.checkpoints._assert_installed()

    @contextmanager
    def installed(self) -> Iterator['EventReaders']:
        require(not self._active and all(getattr(self.X,k) is v for k,v in self._expected.items()),
                'event seams changed before installation')
        before_keys = set(vars(self.X))
        for k,v in self._bindings.items():setattr(self.X,k,v)
        self._active = True
        failure: BaseException | None = None
        try:
            self._load_prefix()
            yield self
        except BaseException as exc:
            failure = exc
            raise
        finally:
            changed = set(vars(self.X)) != before_keys or any(
                getattr(self.X,k,None) is not v for k,v in self._bindings.items())
            changed = changed or self.X._append_event is not self._original_append
            for k,v in self._expected.items():setattr(self.X,k,v)
            self._active = False
            self._admitted_start = self._new_context = self._new_checkpoint_digest = None
            if changed or any(getattr(self.X,k) is not v for k,v in self._expected.items()):
                raise MetadataRefused('event adapter changed or failed restoration') from failure

    def _old_file(self, index: int) -> Any:
        require(type(index) is int and 0 <= index < self.old_count, 'invalid original event index')
        file,_ = self.checkpoints._old_twins(Path(self.X.EVENT_DIRECTORY)/f'{index:06d}.json')
        return file

    def historical_event(self, index: int) -> dict:
        self._assert_installed()
        file = self._old_file(index)
        require(len(self._old_raw) == self.old_count and file.raw == self._old_raw[index],
                'original event changed after prefix verification')
        return file.document()

    def _load_prefix(self) -> None:
        self._assert_installed()
        rows,raw = [],[]
        previous = None
        for index in range(self.old_count):
            file = self._old_file(index)
            row = file.document()
            self._original_validate(row,index=index,previous=previous,
                                    context_digest=self.checkpoints.old_context_digest)
            require(row['kind'] in ('attempt_started','job_synced') and
                    file.raw == self.X.L._pretty_json_bytes(row), 'original event kind/canonical bytes differ')
            rows.append(row)
            raw.append(file.raw)
            previous = row['event_digest']
        chain = json.dumps([r['event_digest'] for r in rows],sort_keys=True,separators=(',',':'),
                           ensure_ascii=True,allow_nan=False).encode('ascii')
        require(_sha(chain) == self.old_chain_sha256 and _sha(raw[-1]) == self.old_tail_sha256,
                'original event aggregate or tail file pin differs')
        started,synced,_ = self._state(rows)
        require(len(started) == self.old_started and len(synced) == self.old_synced and
                started-synced == {ORPHAN_JOB_ID}, 'original event roster differs from sole orphan')
        self._old_raw = tuple(raw)
        self._old_starts = {r['job_id']:r['sequence'] for r in rows if r['kind'] == 'attempt_started'}
        self._old_syncs = {r['job_id']:r['sequence'] for r in rows if r['kind'] == 'job_synced'}

    def admit_start(self, roots: dict, start: dict) -> None:
        self._assert_installed()
        self.checkpoints.verify_prior_start(start['checkpoint_digest'],start,roots)
        raw = self.X.L._pretty_json_bytes(start)
        require(self._admitted_start is None or self._admitted_start == raw,
                'event scope cannot switch checkpoint epochs')
        self._admitted_start = raw
        if start['exp2a_repair_start_schema_version'] == 2:
            context,context_raw = self.checkpoints._current_twins(Path(RELOCATION_CONTEXT_FILE))
            require(context_raw == self.X.L._pretty_json_bytes(self.X._execution_context(start)),
                    'event context differs from admitted checkpoint')
            value = context['execution_context_digest'],context_raw
            require(self._new_context is None or self._new_context == value, 'admitted event context changed')
            self._new_context = value
            self._new_checkpoint_digest = start['checkpoint_digest']
        else:
            require(start['execution_context_digest'] == self.checkpoints.old_context_digest,
                    'original event caller context differs')

    def validate_event(self, row: dict, *, index: int, previous: str | None, context_digest: str) -> None:
        self._assert_installed()
        require(type(index) is int and index >= 0, 'event index must be exact nonnegative integer')
        if index < self.old_count:
            allowed = {self.checkpoints.old_context_digest}
            if self._new_context is not None:allowed.add(self._new_context[0])
            require(context_digest in allowed, 'unadmitted context requested original event validation')
            file = self._old_file(index)
            require(self.X.L._pretty_json_bytes(row) == file.raw, 'original event bytes were rewritten')
            expected_context = self.checkpoints.old_context_digest
        else:
            require(self._new_context is not None and context_digest == self._new_context[0],
                    'new event requires the admitted relocated context')
            _,current_raw = self.checkpoints._current_twins(Path(RELOCATION_CONTEXT_FILE))
            require(current_raw == self._new_context[1], 'relocated event context changed')
            expected_context = self._new_context[0]
        self._original_validate(row,index=index,previous=previous,context_digest=expected_context)
        if row['kind'] == 'attempt_started':
            expected_checkpoint = (self.checkpoints.old_checkpoint_digest if index < self.old_count
                                   else self._new_checkpoint_digest)
            require(row['data']['checkpoint_digest'] == expected_checkpoint,
                    'attempt event binds the wrong checkpoint epoch')

    def _state(self, rows: list[dict]) -> tuple[set[str],set[str],bool]:
        started,synced = set(),set()
        terminal = False
        all_jobs = {j.job_id for j in self.W.new_exp2a_jobs()}
        for index,row in enumerate(rows):
            require(not terminal, 'event exists after terminal completion/failure')
            kind,job_id = row['kind'],row['job_id']
            if kind == 'attempt_started':
                require(job_id in all_jobs and job_id not in started, 'duplicate or unknown attempt; retry forbidden')
                expected = self.checkpoints.old_checkpoint_digest if index < self.old_count else self._new_checkpoint_digest
                require(row['data']['checkpoint_digest'] == expected, 'event attempt checkpoint differs')
                started.add(job_id)
            elif kind == 'job_synced':
                require(job_id in started and job_id not in synced, 'duplicate sync or missing attempt start')
                synced.add(job_id)
            elif kind in ('attempt_failed','sync_pending'):
                require(job_id in started and job_id not in synced, 'failure has no unresolved attempt')
                terminal = True
            elif kind == 'complete':
                require(synced == all_jobs, 'completion lacks exact261synced jobs')
                terminal = True
            else:raise MetadataRefused('unknown event kind')
        return started,synced,terminal

    def _inventory(self) -> tuple[str,...]:
        inventories = []
        for role in ('output','sync'):
            folder = self.W._project_path(self.checkpoints.roots[role]/self.X.EVENT_DIRECTORY,directory=True)
            names = []
            for path in folder.iterdir():
                require(re.fullmatch('[0-9]{6}\\.json',path.name) is not None,
                        'unknown/temp file in event inventory; preserved as stop evidence')
                self.W._project_path(path,directory=False)
                names.append(path.name)
            inventories.append(tuple(sorted(names)))
        names = inventories[0]
        require(names == inventories[1], 'event twin inventories differ; healing forbidden')
        require(self.old_count <= len(names) <= 2*len(self.W.new_exp2a_jobs())+1 and
                names == tuple(f'{i:06d}.json' for i in range(len(names))), 'event inventory gap/count differs')
        return names

    def load_events(self, roots: dict, start: dict) -> list[dict]:
        self.admit_start(roots,start)
        names = self._inventory()
        rows,raw = [],[]
        previous = None
        for index,name in enumerate(names):
            if index < self.old_count:
                file = self._old_file(index)
                row,value = file.document(),file.raw
            else:
                row,value = self.checkpoints._current_twins(Path(self.X.EVENT_DIRECTORY)/name)
            self.validate_event(row,index=index,previous=previous,context_digest=start['execution_context_digest'])
            rows.append(row)
            raw.append(value)
            previous = row['event_digest']
        self._state(rows)
        require(self._inventory() == names, 'event inventory changed during verification')
        for index,name in enumerate(names):
            observed = (self._old_file(index).raw if index < self.old_count else
                        self.checkpoints._current_twins(Path(self.X.EVENT_DIRECTORY)/name)[1])
            require(observed == raw[index], 'event changed during stream verification')
        self.admit_start(roots,start)
        return rows


class ReuseReader:
    """Reuse the149attested synced fits; retain original orphan/new-job path."""

    def __init__(self, access: Any, completed: CompletedJobReaders, events: EventReaders) -> None:
        self.access,self.completed,self.events = access,completed,events
        self.X,self.W,self.checkpoints = completed.X,completed.W,completed.checkpoints
        self._original = self.X._run_one_job
        self._replacement = self.run_one
        self._active = False

    def _assert_installed(self) -> None:
        require(self._active and self.X._run_one_job is self._replacement, 'reuse reader scope differs')
        self.completed._assert_installed()
        self.events._assert_installed()

    @contextmanager
    def installed(self) -> Iterator['ReuseReader']:
        require(not self._active and self.X._run_one_job is self._original, 'reuse seam changed before installation')
        self.X._run_one_job = self._replacement
        self._active = True
        failure: BaseException | None = None
        try:
            self._assert_installed()
            yield self
        except BaseException as exc:
            failure = exc
            raise
        finally:
            changed = self.X._run_one_job is not self._replacement
            self.X._run_one_job = self._original
            self._active = False
            if changed or self.X._run_one_job is not self._original:
                raise MetadataRefused('reuse adapter changed or failed restoration') from failure

    def run_one(self, job: Any, *, validated: Any, checkpoint_path: Path,
                start: dict, events: list[dict]) -> str:
        self._assert_installed()
        require(start.get('exp2a_repair_start_schema_version') == 2 and
                self.X.L._pretty_json_bytes(start) == self.events._admitted_start,
                'reuse requires the admitted new checkpoint')
        require(job.as_record() == self.X._new_job(job.job_id).as_record(), 'reuse job differs from registered roster')
        if job.job_id not in self.events._old_syncs:
            return self._original(job,validated=validated,checkpoint_path=checkpoint_path,start=start,events=events)
        roots = self.checkpoints.preflight.roots
        require(type(validated) is self.X.ValidatedExp2APreflight and validated.roots == roots and
                validated.report_sha256 == self.checkpoints.preflight.sha256 and
                validated.git_commit == start['environment']['git_commit'], 'reuse preflight differs')
        require(Path(checkpoint_path) == roots['output']/self.W.START_DIRECTORY/f"{start['lease']['token']}.json",
                'reuse checkpoint path differs')
        expected_history = [self.events.historical_event(self.events._old_starts[job.job_id]),
                            self.events.historical_event(self.events._old_syncs[job.job_id])]
        history = [row for row in events if row.get('job_id') == job.job_id]
        require(self.X.L._pretty_json_bytes(history) == self.X.L._pretty_json_bytes(expected_history),
                'preserved reuse history differs or duplicates an attempt/sync')
        local,remote = (roots[role]/'jobs'/job.job_id for role in ('output','sync'))
        observation = self.access.historical_pair_at(local,remote)
        actual = self.X.reconcile_completed_exp2a_job(job.job_id,checkpoint_path=checkpoint_path,
                    checkpoint_sha256=self.X.sha256_file(checkpoint_path),expected_git_commit=validated.git_commit)
        require(type(actual) is dict and actual['source_tree_digest'] == actual['copy_tree_digest'] == observation.policy.content_digest and
                actual['copy_evidence_digest'] == observation.observed_copy_digest,
                'current reused pair differs from the relocation attestation')
        require(expected_history[1]['data'] == {'execution_digest':actual['execution_digest'],
                'source_tree_digest':actual['source_tree_digest'],'copy_evidence_digest':observation.historical_copy_digest},
                'historical reuse event differs from its original pair identity')
        require(self.access.historical_pair_at(local,remote) == observation, 'reused pair changed during reconciliation')
        self._assert_installed()
        return 'resumed'


class ControlReaders:
    """Exact original control receipts and outcome-blind incident metadata."""

    PHASE_PINS = {
        'prepare':'53605da944ff9bd80752fd254d960deed19064c42b07e75bce51acaedb7ebfbc',
        'preflight':'dd9ee61ff31078a85e02a3cb7a455b7cb374568a5094f0084bf7ed90d65f90a6',
        'launch-control':'28baf2f3e13a33d6a1c2f64b2d34f17d8bd3dbd48d0a60d1b6105252388e10be',
    }

    def __init__(self, access: Any, production: Any, events: EventReaders, *,
                 phase_pins: dict[str,str] | None = None) -> None:
        self.access,self.P,self.events = access,production,events
        self.checkpoints = events.checkpoints
        self.preflight = self.checkpoints.preflight
        self.sources,self.W,self.X = self.preflight.sources,self.checkpoints.W,self.checkpoints.X
        self.phase_pins = dict(self.PHASE_PINS if phase_pins is None else phase_pins)
        require(set(self.phase_pins) == set(self.PHASE_PINS), 'historical control phase roster differs')
        self._original_receipt = production._load_receipt
        self._original_layout = production._validate_fixed_layout
        self._original_roots = production._fixed_roots
        self._bindings = {'_load_receipt':self.load_receipt,'_load_prepare':self.load_prepare,
            '_load_preflight':self.load_preflight,'_load_control':self.load_control,
            '_checkpoint_material':self.checkpoint_material,'_events_material':self.events_material,
            '_REGISTERED_WORKSPACE_ROOT':self.W.WORKSPACE_ROOT}
        self._expected = {k:getattr(production,k) for k in self._bindings}
        self._active = False

    def _assert_installed(self) -> None:
        require(self._active and all(getattr(self.P,k) is v for k,v in self._bindings.items()) and
                self.P._validate_fixed_layout is self._original_layout and self.P._fixed_roots is self._original_roots,
                'control reader scope differs')
        self.events._assert_installed()
        require(self.P.WORKSPACE_ROOT == self.W.WORKSPACE_ROOT and
                self.P.Plan is self.W and self.P.Launch is self.X and self.P.Sources is self.sources.S,
                'control modules/workspace differ')
        self.P._validate_fixed_layout()

    @contextmanager
    def installed(self) -> Iterator['ControlReaders']:
        require(not self._active and all(getattr(self.P,k) is v for k,v in self._expected.items()),
                'control seams changed before installation')
        before_keys = set(vars(self.P))
        for k,v in self._bindings.items():setattr(self.P,k,v)
        self._active = True
        failure: BaseException | None = None
        try:
            self._assert_installed()
            yield self
        except BaseException as exc:
            failure = exc
            raise
        finally:
            changed = set(vars(self.P)) != before_keys or any(
                getattr(self.P,k,None) is not v for k,v in self._bindings.items())
            changed = changed or self.P._validate_fixed_layout is not self._original_layout or self.P._fixed_roots is not self._original_roots
            for k,v in self._expected.items():setattr(self.P,k,v)
            self._active = False
            if changed or any(getattr(self.P,k) is not v for k,v in self._expected.items()):
                raise MetadataRefused('control reader changed or failed restoration') from failure

    def _logical(self, physical: Path) -> str:
        path = Path(physical)
        require(path.is_absolute() and path.is_relative_to(self.W.WORKSPACE_ROOT),
                'control path escaped fixed workspace')
        return str(OLD_ROOT/path.relative_to(self.W.WORKSPACE_ROOT).as_posix())

    def _twins(self, left: Path, right: Path) -> tuple[Any,Any]:
        files = tuple(self.access.historical_file_at(path) for path in (left,right))
        require(all(file.logical_path == self._logical(path) for file,path in zip(files,(left,right),strict=True)),
                'control file historical mapping differs')
        require(files[0].raw == files[1].raw and not os.path.samefile(left,right),
                'historical control twins differ')
        return files

    def _pin(self, left: Path, right: Path) -> dict:
        file,_ = self._twins(left,right)
        return {'path':self._logical(left),'copy_path':self._logical(right),
                'sha256':file.sha256,'independent_copy':True}

    def _exact(self, actual: Any, expected: Any, what: str) -> None:
        require(self.X.L._pretty_json_bytes(actual) == self.X.L._pretty_json_bytes(expected),what)

    def load_receipt(self, phase: str) -> dict:
        self._assert_installed()
        if phase not in self.phase_pins:return self._original_receipt(phase)
        left,right = self.P._receipt_paths(phase)
        file,twin = self._twins(left,right)
        require(file.sha256 == self.phase_pins[phase], 'historical receipt file pin differs')
        document = self.P._expect_keys(file.document(),{
            'week8_exp2a_production_schema_version','phase','purpose','status',
            'receipt_paths','payload','receipt_digest'},what='historical production receipt')
        require(type(document['week8_exp2a_production_schema_version']) is int and
                document['week8_exp2a_production_schema_version'] == self.P.PRODUCTION_SCHEMA_VERSION and
                document['phase'] == phase and type(document['purpose']) is str and
                type(document['status']) is str and type(document['payload']) is dict and
                document['receipt_paths'] == {'original':self._logical(left),'copy':self._logical(right)},
                'historical receipt identity/schema differs')
        expected = self.W._seal({k:v for k,v in document.items() if k != 'receipt_digest'},'receipt_digest')
        self._exact(document,expected,'historical receipt seal differs')
        require(file.raw == self.X.L._pretty_json_bytes(document), 'historical receipt bytes not canonical')
        require(self._twins(left,right) == (file,twin), 'historical receipt changed during read')
        return {**document,'_file_sha256':file.sha256}

    def _commit(self, receipt: dict, requested: str | None) -> str:
        commit = self.P._commit(receipt['payload'].get('expected_git_commit'))
        require(requested is None or commit == self.P._commit(requested), 'requested control commit differs')
        return commit

    def load_prepare(self, expected_commit: str | None = None) -> dict:
        receipt = self.load_receipt('prepare')
        commit = self._commit(receipt,expected_commit)
        P = self.P
        plan_pin = self._pin(P.PREPARATION_ORIGINAL_ROOT/self.W.PLAN_FILE,P.PREPARATION_COPY_ROOT/self.W.PLAN_FILE)
        ledger_pin = self._pin(P.PREPARATION_ORIGINAL_ROOT/self.sources.S.SOURCE_LEDGER_FILE,
                               P.PREPARATION_COPY_ROOT/self.sources.S.SOURCE_LEDGER_FILE)
        plan_file = self.access.historical_file(plan_pin['path'])
        plan = plan_file.document()
        self.W.validate_exp2a_repair_plan(plan)
        require(ledger_pin['sha256'] == self.sources.ledger_sha256 and
                ledger_pin['path'] == self.sources.ledger_logical_path,
                'preparation ledger differs from admitted source metadata')
        expected = {'expected_git_commit':commit,
            'route':{'device':'cpu','num_threads':4,'num_interop_threads':4,'gpu_used':False},
            'plan':plan_pin,'source_ledger':ledger_pin,'plan_digest':plan['plan_digest'],
            'fixed_paths':{k:self._logical(v) for k,v in P._fixed_roots().items()},
            'execution_authorized':False}
        self._exact(receipt['payload'],expected,'historical prepare payload differs')
        return receipt

    def _preflight_receipt(self, expected_commit: str | None, *, full: bool) -> dict:
        prepared = self.load_prepare(expected_commit)
        receipt = self.load_receipt('preflight')
        commit = self._commit(receipt,prepared['payload']['expected_git_commit'])
        P = self.P
        pin = self._pin(P.PREFLIGHT_ROOT/self.X.PREFLIGHT_FILE,P.SYNC_ROOT/self.X.PREFLIGHT_FILE)
        require(pin['sha256'] == self.preflight.sha256 and pin['path'] == self.preflight.logical_path,
                'control preflight differs from admitted metadata')
        expected = {'expected_git_commit':commit,'prepare_receipt_sha256':prepared['_file_sha256'],
            'preflight':pin,'roots':self.preflight.logical_roots,'attempt_timeout_seconds':3600.0,
            'minimum_free_bytes':8_589_934_592,'sync_destination_identity':P.SYNC_DESTINATION_IDENTITY,
            'shared_lease':{'root':self._logical(self.W.COMMON_LEASE_ROOT),'name':self.W.COMMON_LEASE_NAME}}
        self._exact(receipt['payload'],expected,'historical preflight handoff differs')
        if full:self.X.validate_exp2a_repair_preflight(P.PREFLIGHT_ROOT/self.X.PREFLIGHT_FILE,
            output_root=P.OUTPUT_ROOT,sync_root=P.SYNC_ROOT,expected_git_commit=commit)
        return receipt

    def load_preflight(self, expected_commit: str | None = None) -> dict:
        return self._preflight_receipt(expected_commit,full=True)

    def load_control(self, expected_commit: str | None = None, *, monitor_only: bool = False) -> dict:
        require(type(monitor_only) is bool, 'monitor-only selector must be exact boolean')
        receipt = self.load_receipt('launch-control')
        require(receipt['status'] == 'armed_before_blocking_launch', 'control is not the original armed receipt')
        commit = self._commit(receipt,expected_commit)
        prepared = self.load_prepare(commit)
        preflight = self._preflight_receipt(commit,full=not monitor_only)
        P = self.P
        expected = {'expected_git_commit':commit,'preflight_receipt_sha256':preflight['_file_sha256'],
            'preflight':preflight['payload']['preflight'],'plan_digest':prepared['payload']['plan_digest'],
            'source_ledger':prepared['payload']['source_ledger'],
            'shared_lease':{'root':self._logical(self.W.COMMON_LEASE_ROOT),'name':self.W.COMMON_LEASE_NAME},
            'checkpoint_identity':{'local_directory':self._logical(P.OUTPUT_ROOT/self.W.START_DIRECTORY),
                'copy_directory':self._logical(P.SYNC_ROOT/self.W.START_DIRECTORY),'filename_rule':'single_32hex_lease_token_json'},
            'event_identity':{'local_directory':self._logical(P.OUTPUT_ROOT/self.X.EVENT_DIRECTORY),
                'copy_directory':self._logical(P.SYNC_ROOT/self.X.EVENT_DIRECTORY),'filename_rule':'contiguous_six_digit_json'},
            'launch_report_identity':{'local_directory':self._logical(P.OUTPUT_ROOT/self.X.REPORT_DIRECTORY),
                'copy_directory':self._logical(P.SYNC_ROOT/self.X.REPORT_DIRECTORY),'filename_rule':'matching_lease_token_json'},
            'roots':{k:self.preflight.logical_roots[k] for k in ('output','staging','sync')},
            'attempt_timeout_seconds':3600.0,'expected_physical_fits':261,'expected_member_models':441,
            'automatic_retry_allowed':False,'scientific_files_permitted_for_monitor':False}
        self._exact(receipt['payload'],expected,'historical launch control differs')
        return receipt

    def _original_control(self, control: Any) -> dict:
        expected = self.load_control(monitor_only=True)
        self._exact(control,expected,'monitor control is not the exact original receipt')
        return expected

    def checkpoint_material(self, control: Any) -> tuple[dict,str]:
        self._original_control(control)
        C,W,X = self.checkpoints,self.W,self.X
        name = f'{C.old_token}.json'
        for role in ('output','sync'):
            folder = W._project_path(C.roots[role]/W.START_DIRECTORY,directory=True)
            require(sorted(p.name for p in folder.iterdir()) == [name],
                    'pre-recovery monitor requires exactly the old checkpoint')
        return self.historical_checkpoint_material(control)

    def historical_checkpoint_material(self, control: Any) -> tuple[dict,str]:
        """Original metadata proof, also usable beside the sole new epoch."""
        self._original_control(control)
        C,W,X = self.checkpoints,self.W,self.X
        name = f'{C.old_token}.json'
        file,twin = C._old_twins(Path(W.START_DIRECTORY)/name)
        require(file.sha256 == C.old_sha256, 'monitor old checkpoint pin differs')
        document = self.P._expect_keys(file.document(),{
            'exp2a_repair_start_schema_version','purpose','plan_digest','preflight','source_ledger',
            'environment','roots','attempt_timeout_seconds','lease','fixed_worker','supervisor_required',
            'automatic_retry_allowed','execution_context_digest','checkpoint_digest'},what='historical monitor checkpoint')
        report = self.preflight._report(self.preflight.logical_path).document()
        ledger_file = self.sources._ledger_file()
        ledger = ledger_file.document()
        old_lease = self.access.historical_file(str(OLD_ROOT/'week7-production-control/leases'/f'{W.COMMON_LEASE_NAME}.lease.json'))
        lease = old_lease.document()
        require(lease['token'] == C.old_token and lease['lease_name'] == W.COMMON_LEASE_NAME,
                'monitor original lease identity differs')
        environment = document['environment']
        require(type(environment) is dict and environment.get('git_commit') == control['payload']['expected_git_commit'],
                'monitor checkpoint execution commit differs')
        self.P._route_payload(environment)
        expected = W._seal({'exp2a_repair_start_schema_version':1,
            'purpose':'source_verified_week8_exp2a_repair_start','plan_digest':control['payload']['plan_digest'],
            'preflight':{'path':self.preflight.logical_path,'sha256':self.preflight.sha256,'binding_sha256':report['binding_sha256']},
            'source_ledger':{'path':ledger_file.logical_path,'sha256':ledger_file.sha256,'ledger_digest':ledger['ledger_digest']},
            'environment':environment,'roots':control['payload']['roots'],'attempt_timeout_seconds':3600.0,
            'lease':{'path':old_lease.logical_path,'sha256':old_lease.sha256,'name':W.COMMON_LEASE_NAME,
                     'token':C.old_token,'started_at':lease['timestamp_utc']},
            'fixed_worker':'bu.experiments.week8_exp2a_repair_launch._fit_worker',
            'supervisor_required':'bu.experiments.supervisor.run_isolated_attempt','automatic_retry_allowed':False,
            'execution_context_digest':C.old_context_digest},'checkpoint_digest')
        self._exact(document,expected,'monitor original checkpoint metadata differs')
        require(document['checkpoint_digest'] == C.old_checkpoint_digest and
                file.raw == X.L._pretty_json_bytes(document), 'monitor checkpoint digest/canonical bytes differ')
        context,context_twin = C._old_twins(Path(W.CONTEXT_FILE))
        require(context.raw == X.L._pretty_json_bytes(X._execution_context(document)), 'monitor original context differs')
        require(C._old_twins(Path(W.START_DIRECTORY)/name) == (file,twin) and
                C._old_twins(Path(W.CONTEXT_FILE)) == (context,context_twin), 'monitor checkpoint changed during read')
        return document,file.sha256

    def events_material(self, control: Any, checkpoint: Any) -> tuple[list[dict],list[dict]]:
        expected,_ = self.checkpoint_material(control)
        self._exact(checkpoint,expected,'monitor checkpoint argument differs')
        names = self.events._inventory()
        require(len(names) == self.events.old_count, 'pre-recovery monitor event prefix count differs')
        rows = [self.events.historical_event(i) for i in range(len(names))]
        previous = None
        for index,row in enumerate(rows):
            self.X._validate_event(row,index=index,previous=previous,context_digest=self.checkpoints.old_context_digest)
            previous = row['event_digest']
        started,synced,terminal = self.events._state(rows)
        require(not terminal and len(started) == self.events.old_started and len(synced) == self.events.old_synced,
                'monitor original event state differs')
        require(self.events._inventory() == names and
                all(self.events.historical_event(i) == row for i,row in enumerate(rows)),
                'monitor events changed during read')
        return rows,[]


class ReleasedInventoryReader:
    """Current released source rows with separately retained original provenance."""

    def __init__(self, access: Any, completed: CompletedJobReaders) -> None:
        self.access,self.completed = access,completed
        self.checkpoints,self.X,self.W = completed.checkpoints,completed.X,completed.W
        self.sources = self.checkpoints.sources
        self._original = self.X.load_released_exp2a_source_inventory
        self._replacement = self.load_inventory
        self._active = False

    def _assert_installed(self) -> None:
        require(self._active and self.X.load_released_exp2a_source_inventory is self._replacement,
                'released inventory reader scope differs')
        self.completed._assert_installed()

    @contextmanager
    def installed(self) -> Iterator['ReleasedInventoryReader']:
        require(not self._active and self.X.load_released_exp2a_source_inventory is self._original,
                'released inventory seam changed before installation')
        self.X.load_released_exp2a_source_inventory = self._replacement
        self._active = True
        failure: BaseException | None = None
        try:
            self._assert_installed()
            yield self
        except BaseException as exc:
            failure = exc
            raise
        finally:
            changed = self.X.load_released_exp2a_source_inventory is not self._replacement
            self.X.load_released_exp2a_source_inventory = self._original
            self._active = False
            if changed or self.X.load_released_exp2a_source_inventory is not self._original:
                raise MetadataRefused('released inventory reader changed or failed restoration') from failure

    def load_inventory(self, *, checkpoint_path: str | Path, checkpoint_sha256: str,
                       expected_execution_commit: str) -> dict:
        self._assert_installed()
        X,W = self.X,self.W
        start,ledger,roots = X._read_start(checkpoint_path,expected_sha256=checkpoint_sha256,
                                         expected_git_commit=expected_execution_commit,released=True)
        require(start['exp2a_repair_start_schema_version'] == 2,
                'relocated released inventory requires the new checkpoint')
        original = self.sources.metadata_source_ledger(start['source_ledger']['path'],self.sources.ledger_sha256)
        require(X.L._pretty_json_bytes(original) == X.L._pretty_json_bytes(ledger),
                'released inventory historical ledger differs')
        sources,provenance,pending = [],[],[]
        for job,row in zip(W.existing_exp2a_jobs(),ledger['sources'],strict=True):
            _,actual = self.sources.verify_source_row(job,row)
            sources.append(actual)
            provenance.append({'job_id':job.job_id,'origin':{
                'kind':'historical_source_ledger','ledger_sha256':self.sources.ledger_sha256,'source':row}})
        for job in W.new_exp2a_jobs():
            actual = X._completed_source_pair(job,start,ledger,roots,expected_execution_commit)
            if actual is None:
                pending.append(job.job_id)
                continue
            local,remote = (roots[role]/'jobs'/job.job_id for role in ('output','sync'))
            result_path = local/'job_result.json'
            preserved = self.access.has_historical_file(result_path)
            original_file = self.access.historical_file_at(result_path) if preserved else None
            result = original_file.document() if original_file is not None else X.read_json(result_path)
            old,context = self.completed._epoch(result,start)
            if preserved:
                require(old, 'preserved released fit changed its original epoch')
                observation = self.access.historical_pair_at(local,remote)
                require(actual['copy_evidence_digest'] == observation.observed_copy_digest and
                        actual['source_tree_digest'] == actual['copy_tree_digest'] == observation.policy.content_digest,
                        'released preserved pair differs from relocation evidence')
                historical = {**actual,'source_path':observation.policy.logical_source,
                    'copy_path':observation.policy.logical_copy,'copy_evidence_digest':observation.historical_copy_digest}
                origin = {'kind':'preserved_epoch001_pair','checkpoint_digest':result['checkpoint_digest'],
                          'execution_context_digest':context,'source':historical}
            elif old:
                require(job.job_id == ORPHAN_JOB_ID, 'released unpaired old fit is not the sole orphan')
                origin = {'kind':'preserved_epoch001_orphan_new_copy','checkpoint_digest':result['checkpoint_digest'],
                          'execution_context_digest':context}
            else:
                origin = {'kind':'relocated_epoch_fit','checkpoint_digest':result['checkpoint_digest'],
                          'execution_context_digest':context}
            require(X.read_json(result_path) == result, 'released result changed during provenance read')
            sources.append(actual)
            provenance.append({'job_id':job.job_id,'origin':origin})
        after,after_ledger,after_roots = X._read_start(checkpoint_path,expected_sha256=checkpoint_sha256,
                                                     expected_git_commit=expected_execution_commit,released=True)
        require(X.L._pretty_json_bytes(after) == X.L._pretty_json_bytes(start) and
                X.L._pretty_json_bytes(after_ledger) == X.L._pretty_json_bytes(ledger) and after_roots == roots,
                'released checkpoint/ledger changed during inventory')
        # Reopen all original pairs a second time, as the original public loader
        # does, and compare current rows too; historical IDs stay separate.
        by_id = {row['job']['job_id']:row for row in sources}
        for job,row in zip(W.existing_exp2a_jobs(),ledger['sources'],strict=True):
            _,actual = self.sources.verify_source_row(job,row)
            require(X.L._pretty_json_bytes(actual) == X.L._pretty_json_bytes(by_id[job.job_id]),
                    'released historical pair changed during inventory')
        self._assert_installed()
        return {'start':start,'ledger':ledger,'roots':roots,
                'sources':sorted(sources,key=lambda row:row['job']['job_id']),
                'pending_new_fit_ids':sorted(pending),
                'relocation':self.checkpoints.relocation_binding(),
                'source_provenance':sorted(provenance,key=lambda row:row['job_id'])}


def _historical_execution_git_row(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Return the raw-authority-proven frozen Git identity, or fail closed."""

    if type(raw) is not dict:
        raise MetadataRefused("historical Git adapter lacks raw authority")
    execution = raw.get("execution")
    if type(execution) is not dict:
        raise MetadataRefused("historical Git adapter lacks execution authority")
    if (
        execution.get("path") != str(EXECUTION_WORKTREE.resolve(strict=True))
        or execution.get("git_commit") != EXECUTION_COMMIT
        or execution.get("branch") != "HEAD"
        or execution.get("detached") is not True
        or type(execution.get("worktree_inventory_digest")) is not str
        or _HEX64.fullmatch(execution["worktree_inventory_digest"]) is None
        or type(execution.get("stability_observations")) is not int
        or execution["stability_observations"] < 2
    ):
        raise MetadataRefused("historical Git execution authority differs")
    return execution


def _historical_git_bindings(
    original: FunctionType, *, allow_incomplete: bool
) -> list[ModuleType]:
    """Find every already-imported exact alias of runrecord.git_state."""

    bindings: list[ModuleType] = []
    for name, module in sorted(tuple(sys.modules.items())):
        if name != "bu" and not name.startswith("bu."):
            continue
        if type(module) is not ModuleType:
            raise MetadataRefused(f"historical Git module {name} is not exact")
        namespace = vars(module)
        if "git_state" not in namespace:
            continue
        if namespace["git_state"] is original:
            bindings.append(module)
    required = {
        "bu.runrecord",
        "bu.experiments.confirmatory",
        "bu.experiments.fit_evidence",
        "bu.experiments.preflight",
    }
    if (
        not allow_incomplete
        and not required.issubset({module.__name__ for module in bindings})
    ):
        raise MetadataRefused("historical Git binding inventory is incomplete")
    return bindings


@contextmanager
def verified_historical_git_state(
    raw: Mapping[str, Any], *, allow_imports: bool = False
):
    """Temporarily replace every frozen bare-Git call with sealed authority.

    The historical tree remains byte-for-byte unchanged. During this one scope,
    each imported alias receives the same exact adapter, which returns the
    clean detached execution identity already proven by raw authority.  No Git
    process, repository config, hook, or fsmonitor helper is consulted.
    """

    execution = _historical_execution_git_row(raw)
    runrecord = sys.modules.get("bu.runrecord")
    if type(runrecord) is not ModuleType:
        raise MetadataRefused("historical runrecord module is unavailable")
    expected_source = (EXECUTION_SOURCE / "bu" / "runrecord.py").resolve(strict=True)
    loader = getattr(getattr(runrecord, "__spec__", None), "loader", None)
    original = getattr(runrecord, "git_state", None)
    git_state_type = getattr(runrecord, "GitState", None)
    project_root = getattr(runrecord, "PROJECT_ROOT", None)
    if (
        type(original) is not FunctionType
        or original.__module__ != "bu.runrecord"
        or original.__name__ != "git_state"
        or original.__qualname__ != "git_state"
        or original.__defaults__ != (None,)
        or original.__kwdefaults__ is not None
        or original.__closure__ is not None
        or original.__code__.co_argcount != 1
        or original.__code__.co_posonlyargcount != 0
        or original.__code__.co_kwonlyargcount != 0
        or Path(original.__code__.co_filename).resolve() != expected_source
        or type(git_state_type) is not type
        or git_state_type.__module__ != "bu.runrecord"
        or git_state_type.__name__ != "GitState"
        or not isinstance(project_root, Path)
        or project_root.resolve() != EXECUTION_WORKTREE.resolve(strict=True)
        or getattr(loader, "binding_marker", None)
        != "week8_d161_verified_source_v2"
        or getattr(loader, "tree_kind", None) != "execution"
    ):
        raise MetadataRefused("historical git_state identity or shape differs")
    preexisting_git_states: dict[ModuleType, object] = {}
    for name, module in sorted(tuple(sys.modules.items())):
        if name != "bu" and not name.startswith("bu."):
            continue
        if type(module) is not ModuleType:
            raise MetadataRefused(f"historical Git module {name} is not exact")
        if "git_state" in vars(module):
            preexisting_git_states[module] = vars(module)["git_state"]
    unseen_binding = object()
    bindings = _historical_git_bindings(original, allow_incomplete=allow_imports)

    def verified_git_state(repo: str | Path | None = None) -> Any:
        if repo is not None:
            if type(repo) is not str and not isinstance(repo, Path):
                raise MetadataRefused("historical git_state repository type differs")
            try:
                repository = Path(repo).resolve(strict=True)
            except (OSError, RuntimeError) as exc:
                raise MetadataRefused(
                    "historical git_state repository is unavailable"
                ) from exc
            if repository != EXECUTION_WORKTREE.resolve(strict=True):
                raise MetadataRefused("historical git_state requested another repository")
        current = _historical_execution_git_row(raw)
        for module in bindings:
            if vars(module).get("git_state") is not verified_git_state:
                raise MetadataRefused("historical Git adapter changed during fit")
        if vars(runrecord).get("GitState") is not git_state_type:
            raise MetadataRefused("historical GitState type changed during fit")
        state = git_state_type(
            commit=current["git_commit"], dirty=False, branch=current["branch"]
        )
        if type(state) is not git_state_type:
            raise MetadataRefused("historical Git adapter returned another type")
        return state

    for module in bindings:
        module.git_state = verified_git_state
    if any(vars(module).get("git_state") is not verified_git_state for module in bindings):
        for module in bindings:
            module.git_state = original
        raise MetadataRefused("historical Git adapter could not be installed exactly")
    body_error: BaseException | None = None
    try:
        yield verified_git_state
    except BaseException as exc:
        body_error = exc
        raise
    finally:
        restore_error: BaseException | None = None
        try:
            if any(
                vars(module).get("git_state") is not verified_git_state
                for module in bindings
            ):
                raise MetadataRefused(
                    "historical Git adapter changed before restoration"
                )
            current_bindings: list[ModuleType] = []
            for name, module in sorted(tuple(sys.modules.items())):
                if name != "bu" and not name.startswith("bu."):
                    continue
                if type(module) is not ModuleType:
                    raise MetadataRefused(
                        f"historical Git module {name} changed during fit"
                    )
                namespace = vars(module)
                if "git_state" not in namespace:
                    continue
                current_value = namespace["git_state"]
                prior_value = preexisting_git_states.get(module, unseen_binding)
                if prior_value is original or prior_value is unseen_binding:
                    if current_value is not verified_git_state:
                        raise MetadataRefused(
                            "historical Git binding changed after import"
                        )
                    current_bindings.append(module)
                elif current_value is not prior_value:
                    raise MetadataRefused(
                        "unrelated historical Git binding changed during fit"
                    )
            required = {
                "bu.runrecord",
                "bu.experiments.confirmatory",
                "bu.experiments.fit_evidence",
                "bu.experiments.preflight",
            }
            if not required.issubset(
                {module.__name__ for module in current_bindings}
            ):
                raise MetadataRefused(
                    "historical Git binding inventory is incomplete after import"
                )
            for module in current_bindings:
                module.git_state = original
            if any(vars(module).get("git_state") is not original for module in bindings):
                raise MetadataRefused("historical Git adapter was not restored exactly")
        except BaseException as exc:
            restore_error = exc
            for module in bindings:
                try:
                    module.git_state = original
                except BaseException:
                    pass
            for name, module in tuple(sys.modules.items()):
                if (
                    (name == "bu" or name.startswith("bu."))
                    and type(module) is ModuleType
                    and vars(module).get("git_state") is verified_git_state
                ):
                    try:
                        module.git_state = original
                    except BaseException:
                        pass
        if restore_error is not None:
            if body_error is not None:
                raise MetadataRefused(
                    "historical Git adapter restoration failed after fit refusal"
                ) from restore_error
            raise MetadataRefused(
                "historical Git adapter restoration failed"
            ) from restore_error
