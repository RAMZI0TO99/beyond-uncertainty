"""Relocated synthetic history; original science validators still run."""
import copy
import hashlib
import importlib.util
import json
import os
import sys
from dataclasses import asdict, replace
from pathlib import Path, PureWindowsPath

import pytest

from test_week8_exp2a_sources import authority, source_trees  # pytest fixtures
from bu.durable import atomic_write_json, sha256_file
from bu.experiments import week8_exp2a_repairs as W
from bu.experiments import week8_exp2a_sources as S
from bu.experiments import week8_exp2a_repair_launch as X
from bu.experiments import prefit_storage as Storage
from bu.experiments.supervisor import acquire_batch_lease
from bu.runrecord import GitState, TRACKED_PACKAGES

COMMIT = 'b'*40
ROOT = Path(__file__).resolve().parents[1]

# The same tests run with genuine frozen bu imports. The new provenance helper
# therefore uses its own non-bu module name, as required by the production design.
provenance_spec = importlib.util.spec_from_file_location(
    'tested_relocation_provenance',ROOT/'src/bu/experiments/week8_relocation_provenance.py')
R = importlib.util.module_from_spec(provenance_spec)
sys.modules[provenance_spec.name] = R
provenance_spec.loader.exec_module(R)

script = Path(__file__).resolve().parents[1]/'scripts/week8_relocation_metadata.py'
spec = importlib.util.spec_from_file_location('tested_relocation_metadata',script)
M = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = M
spec.loader.exec_module(M)


@pytest.fixture
def environment(monkeypatch):
    pins = {name:f'synthetic-{index}' for index,name in enumerate(TRACKED_PACKAGES)}
    monkeypatch.setattr(X.P,'_verify_environment',lambda:(GitState(COMMIT,False,'synthetic'),dict(pins),dict(pins)))
    monkeypatch.setattr(X.P,'_verify_device',lambda route:{
        'frozen_route':'cpu','requested_route':route,'available':route == 'cpu'})


@pytest.fixture(autouse=True)
def frozen_import_boundary(request):
    expected = os.environ.get('W8_FROZEN_QA_SOURCE_ROOT')
    def verify():
        if expected is None:return
        root = Path(expected).resolve()
        modules = {}
        for name,module in sorted(tuple(sys.modules.items())):
            if name != 'bu' and not name.startswith('bu.'):continue
            path = Path(module.__file__).resolve()
            assert path.is_relative_to(root), f'{name} escaped frozen source tree: {path}'
            modules[name] = {'path':str(path),'sha256':sha256_file(path)}
        assert 'bu.experiments.week8_exp2a_repair_launch' in modules
        assert 'bu.experiments.week8_relocation_provenance' not in modules
        return modules
    verify()
    yield
    modules = verify()
    if expected is not None:
        with Path(os.environ['W8_FROZEN_QA_IMPORT_RECEIPT']).open('a',encoding='utf-8') as handle:
            handle.write(json.dumps({'test':request.node.nodeid,'modules':modules},sort_keys=True)+'\n')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture
def relocated(source_trees):
    root, store = source_trees
    original = S.build_exp2a_source_ledger()
    old = PureWindowsPath('D:/Aenv/pro/pro')
    archive = root/'project 2(ongoing)'
    copies = {}
    def copied(path):
        path = Path(path)
        if path in copies:
            return copies[path]
        target = archive/path.relative_to(root)
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(path.read_bytes())
        copies[path] = target
        return target
    def logical(path):
        return str(old/Path(path).relative_to(root).as_posix())
    document = copy.deepcopy(original)
    pairs, documents = [], []
    for index,(before,after) in enumerate(zip(original['sources'],document['sources'],strict=True)):
        physical = []
        for key in ('source_path','copy_path'):
            folder = Path(before[key])
            target = copied(folder/S.F.FIT_EVIDENCE_FILE).parent
            commit, verified = store.entries[folder]
            store.entries[target.resolve()] = commit,replace(verified,fit_dir=target.resolve())
            after[key] = logical(folder)
            physical.append(target.relative_to(root).as_posix())
        pairs.append(R.Pair(f'source-{index:03d}',after['source_path'],after['copy_path'],
                            physical[0],physical[1],after['source_tree_digest'],after['copy_evidence_digest']))
    for family,key in M._AUTHORITY_FIELDS:
        row = document['authority'][family][key]
        for field in ('source_path','copy_path'):
            path = Path(row[field])
            target = copied(path)
            documents.append(R.Document(target.relative_to(root).as_posix(),sha256_file(target)))
            row[field] = logical(path)
    document = W._seal({k:v for k,v in document.items() if k!='ledger_digest'},'ledger_digest')
    ledger_path = atomic_write_json(root/'ledger.json',document)
    ledger_sha = sha256_file(ledger_path)
    documents.append(R.Document('ledger.json',ledger_sha))
    pairs,documents = tuple(pairs),tuple(documents)
    raw = R.build_record(root,pairs,documents)
    access = R.EvidenceAccess(raw,sha(raw),root,pairs,documents)
    readers = M.SourceReaders(access,W,S,ledger_logical_path=str(old/'ledger.json'),ledger_sha256=ledger_sha)
    store.loads.clear()
    return root,store,document,access,readers,raw,pairs,documents


def test_metadata_reader_verifies_all_historical_rows_without_reopening_fit_arrays(relocated):
    root,store,document,_,readers,*_ = relocated
    before = (root/'ledger.json').read_bytes()
    with readers.installed():
        result = S._metadata_source_ledger(root/'ledger.json',sha(before))
        assert result == document
        assert store.loads == []
    assert (root/'ledger.json').read_bytes() == before


def test_full_loader_uses_original_scientific_validator_for_all_310_copies(relocated):
    root,store,document,_,readers,*_ = relocated
    original_loader = S.load_exp2a_source_ledger
    original_roots = S.SMOKE_OUTPUT_ROOT,S.WEEK7_OUTPUT_ROOT
    with readers.installed():
        assert S.load_exp2a_source_ledger(root/'ledger.json') == document
        assert len(store.loads) == 310
        assert all((root/'project 2(ongoing)') in path.parents for path,commit in store.loads)
    assert S.load_exp2a_source_ledger is original_loader
    assert (S.SMOKE_OUTPUT_ROOT,S.WEEK7_OUTPUT_ROOT) == original_roots


def test_actual_source_row_keeps_current_identity_separate_from_historical_row(relocated):
    _,_,document,access,readers,*_ = relocated
    job = W.existing_exp2a_jobs()[0]
    old = document['sources'][0]
    observation = access.historical_pair(old['source_path'],old['copy_path'])
    assert observation.historical_copy_digest != observation.observed_copy_digest
    with readers.installed():
        verified,actual = readers.verify_source_row(job,old)
        assert actual['copy_evidence_digest'] == observation.observed_copy_digest
        assert actual['source_path'] == str(observation.source)
        assert old['copy_evidence_digest'] == observation.historical_copy_digest
        assert verified.fit_id == job.job_id


def test_source_changed_after_metadata_check_refuses_full_loader(relocated):
    root,store,document,access,readers,*_ = relocated
    with readers.installed():
        S._metadata_source_ledger(root/'ledger.json',readers.ledger_sha256)
        row = document['sources'][0]
        pair = access.historical_pair(row['source_path'],row['copy_path'])
        (pair.source/S.F.FIT_EVIDENCE_FILE).write_bytes(b'corrupted source')
        with pytest.raises(R.RelocationRefused):
            S.load_exp2a_source_ledger(root/'ledger.json')
    assert store.loads == []


def test_authority_changed_after_installation_refuses_metadata(relocated):
    root,_,_,_,readers,*_ = relocated
    with readers.installed():
        (S.SMOKE_OUTPUT_ROOT/S.SMOKE_LABEL_FILE).write_bytes(b'changed authority')
        with pytest.raises(ValueError):
            S._metadata_source_ledger(root/'ledger.json',readers.ledger_sha256)


def test_changed_or_wrong_pin_ledger_is_not_accepted(relocated):
    root,_,document,_,readers,*_ = relocated
    with readers.installed():
        with pytest.raises(M.MetadataRefused,match='unexpected historical ledger pin'):
            S._metadata_source_ledger(root/'ledger.json','a'*64)
        forged = copy.deepcopy(document)
        forged['sources'][0]['expected_git_commit'] = 'f'*40
        with pytest.raises(M.MetadataRefused,match='pinned historical document'):
            S.reverify_exp2a_source_ledger(forged)


def test_scoped_installation_restores_on_exception_and_rejects_nesting(relocated):
    _,_,_,_,readers,*_ = relocated
    before = {name:getattr(S,name) for name in readers._bindings}
    with pytest.raises(RuntimeError,match='synthetic lower refusal'):
        with readers.installed():
            with pytest.raises(M.MetadataRefused,match='nested'):
                with readers.installed():
                    pass
            raise RuntimeError('synthetic lower refusal')
    assert all(getattr(S,name) is value for name,value in before.items())
    with pytest.raises(M.MetadataRefused,match='outside verified scope'):
        readers.load_source_ledger('D:/Aenv/pro/pro/ledger.json')


def test_scoped_installation_detects_tampering_and_restores_owned_seams(relocated):
    _,_,_,_,readers,*_ = relocated
    original = S.load_exp2a_source_ledger
    with pytest.raises(M.MetadataRefused,match='restoration'):
        with readers.installed():
            S.load_exp2a_source_ledger = lambda path: {}
    assert S.load_exp2a_source_ledger is original


def test_fixed_loader_requires_independent_exact_pinned_twins(relocated,monkeypatch):
    root,_,_,_,_,raw,pairs,documents = relocated
    manifest = root/'manifest'
    for side in ('original','copy'):
        (manifest/side).mkdir(parents=True)
        (manifest/side/'relocation.json').write_bytes(raw)
    policy_raw = R.canonical({'pairs':[asdict(p) for p in pairs],'documents':[asdict(d) for d in documents]})
    (manifest/'policy.json').write_bytes(policy_raw)
    for key,value in {'WORKSPACE':root,'MANIFEST_ROOT':manifest,'RECORD_SHA256':sha(raw),
                      'POLICY_SHA256':sha(policy_raw),'EXPECTED_PAIR_COUNT':155,'EXPECTED_DOCUMENT_COUNT':9}.items():
        monkeypatch.setattr(M,key,value)
    access = M.load_registered_access(R)
    assert access.attestation_sha256 == sha(raw)
    (manifest/'copy/relocation.json').write_bytes(raw+b'\n')
    with pytest.raises(M.MetadataRefused,match='twin bytes'):
        M.load_registered_access(R)


@pytest.fixture
def relocated_preflight(relocated,environment):
    root,store,ledger,_,_,_,pairs,old_documents = relocated
    roots = {name:root/folder for name,folder in M.PRODUCTION_FOLDERS.items()}
    for folder in roots.values():folder.mkdir()
    logical_roots = {name:str(M.OLD_ROOT/folder) for name,folder in M.PRODUCTION_FOLDERS.items()}
    plan = W.build_exp2a_repair_plan()
    plan_file = atomic_write_json(root/'plan.json',plan)
    ledger_file = root/'ledger.json'
    documents = list(old_documents)+[R.Document('plan.json',sha256_file(plan_file))]
    def register(path):
        documents.append(R.Document(path.relative_to(root).as_posix(),sha256_file(path)))
    inputs = {}
    for name,path in [('plan',plan_file),('source_ledger',ledger_file)]:
        inputs[name] = {'path':str(M.OLD_ROOT/path.name),'sha256':sha256_file(path)}
        for role in ('preflight','sync'):
            destination = roots[role]/f'exp2a_input_{name}.json'
            destination.write_bytes(path.read_bytes())
            register(destination)
    binding = W._seal({'inputs':inputs,'plan_digest':plan['plan_digest'],
                       'attempt_timeout_seconds':3600.0},'binding_sha256')['binding_sha256']
    canary_doc = {'canary_schema_version':1,'destination_identity':'synthetic-independent-copy',
                  'plan_sha256':binding}
    for role in ('preflight','sync'):
        path = atomic_write_json(roots[role]/X.P.SYNC_CANARY_FILE,canary_doc)
        register(path)
    canary_sha = sha256_file(path)
    canary_size = path.stat().st_size
    canary = {'source_path':str(PureWindowsPath(logical_roots['preflight'])/X.P.SYNC_CANARY_FILE),
              'destination_path':str(PureWindowsPath(logical_roots['sync'])/X.P.SYNC_CANARY_FILE),
              'sha256':canary_sha,'size_bytes':canary_size}
    receipt = {'schema_version':1,'destination_identity':'synthetic-independent-copy',
               'destination_path':canary['destination_path'],'sha256':canary_sha,'size_bytes':canary_size}
    report = {'week8_preflight_schema_version':1,'exp2a_repair_preflight_schema_version':1,
              'status':'ready','launch_performed':False,'inputs':inputs,
              'budget':{'new_physical_fits':plan['counts']['new_physical_fits'],
                        'new_member_models':plan['counts']['new_member_model_trainings'],
                        'new_baseline_fits':plan['counts']['new_baseline_fits'],
                        'new_repair_fits':plan['counts']['new_repair_fits'],
                        'historical_sources_reopened':155,
                        'interpretation':'exact inventory counts; not a runtime or GPU-hour estimate'},
              'plan_digest':plan['plan_digest'],'binding_sha256':binding,
              'environment':X._environment(COMMIT),
              'storage':{'minimum_free_bytes':8*1024**3,'roots':{
                  name:{'path':path,'writable':True,'free_bytes':9*1024**3} for name,path in logical_roots.items()}},
              'attempt_timeout_seconds':3600.0,'common_control_root':str(M.OLD_ROOT/'week7-production-control'),
              'sync_canary':canary,'sync_receipt':receipt}
    for role in ('preflight','sync'):
        path = atomic_write_json(roots[role]/X.PREFLIGHT_FILE,report)
        register(path)
    report_sha = sha256_file(path)
    raw = R.build_record(root,pairs,tuple(documents))
    access = R.EvidenceAccess(raw,sha(raw),root,pairs,tuple(documents))
    readers = M.SourceReaders(access,W,S,ledger_logical_path=str(M.OLD_ROOT/'ledger.json'),ledger_sha256=sha256_file(ledger_file))
    preflight = M.PreflightReaders(access,readers,X,Storage,preflight_sha256=report_sha)
    store.loads.clear()
    return roots,report,readers,preflight,store


def test_preflight_keeps_original_report_and_validates_current_locations(relocated_preflight):
    roots,original,sources,preflight,store = relocated_preflight
    report = roots['preflight']/X.PREFLIGHT_FILE
    before = report.read_bytes()
    with sources.installed(),preflight.installed():
        validated = X.validate_exp2a_repair_preflight(report,output_root=roots['output'],
                                                     sync_root=roots['sync'],expected_git_commit=COMMIT)
        assert validated.report == original
        assert validated.report_path == report and validated.roots == roots
        assert len(store.loads) == 310
    assert report.read_bytes() == before


def test_storage_reopens_original_pin_and_uses_current_capacity(relocated_preflight,monkeypatch):
    roots,_,sources,preflight,_ = relocated_preflight
    from types import SimpleNamespace
    checked = []
    def capacity(path):
        checked.append(path)
        return SimpleNamespace(free=8*1024**3)
    monkeypatch.setattr(Storage.shutil,'disk_usage',capacity)
    with sources.installed(),preflight.installed():
        X.check_preflight_storage(roots['preflight']/X.PREFLIGHT_FILE,preflight.sha256,roots=roots)
        assert set(checked) == set(roots.values())
        monkeypatch.setattr(Storage.shutil,'disk_usage',lambda path:SimpleNamespace(free=8*1024**3-1))
        with pytest.raises(ValueError,match='below required'):
            X.check_preflight_storage(roots['preflight']/X.PREFLIGHT_FILE,preflight.sha256,roots=roots)


@pytest.mark.parametrize('which',['pin','roots','content'])
def test_storage_refuses_mismatched_source_and_locations(relocated_preflight,which):
    roots,_,sources,preflight,_ = relocated_preflight
    requested = dict(roots)
    digest = preflight.sha256
    if which == 'pin':digest = '0'*64
    elif which == 'roots':requested['output'] = roots['staging']
    else:(roots['preflight']/X.PREFLIGHT_FILE).write_bytes(b'changed preflight')
    with sources.installed(),preflight.installed():
        with pytest.raises(ValueError):
            X.check_preflight_storage(roots['preflight']/X.PREFLIGHT_FILE,digest,roots=requested)


def test_preflight_refuses_wrong_commit_and_restores_hooks(relocated_preflight):
    roots,_,sources,preflight,_ = relocated_preflight
    original = X.validate_exp2a_repair_preflight
    with sources.installed(),preflight.installed():
        with pytest.raises(ValueError):
            X.validate_exp2a_repair_preflight(roots['preflight']/X.PREFLIGHT_FILE,
                                            output_root=roots['output'],sync_root=roots['sync'],
                                            expected_git_commit='f'*40)
    assert X.validate_exp2a_repair_preflight is original


@pytest.fixture
def relocated_checkpoint(relocated_preflight):
    roots,report,prior_sources,prior_preflight,store = relocated_preflight
    root = W.WORKSPACE_ROOT
    token = M.OLD_LEASE_TOKEN
    lease_relative = Path('week7-production-control/leases')/f'{W.COMMON_LEASE_NAME}.lease.json'
    lease_doc = {'schema_version':X.SUPERVISOR_SCHEMA_VERSION,'lease_name':W.COMMON_LEASE_NAME,'pid':os.getpid(),
                 'token':token,'timestamp':1788294507.533758,'timestamp_utc':'2026-09-01T20:28:27.533758Z'}
    archived = atomic_write_json(root/'project 2(ongoing)'/lease_relative,lease_doc)
    active = atomic_write_json(root/lease_relative,lease_doc)
    (active.parent/'history').mkdir(exist_ok=True)
    ledger_path = root/'ledger.json'
    ledger = json.loads(ledger_path.read_bytes())
    lease = {'path':str(M.OLD_ROOT/lease_relative.as_posix()),'sha256':sha256_file(archived),
             'name':W.COMMON_LEASE_NAME,'token':token,'started_at':lease_doc['timestamp_utc']}
    payload = {'exp2a_repair_start_schema_version':1,
               'purpose':'source_verified_week8_exp2a_repair_start',
               'plan_digest':W.build_exp2a_repair_plan()['plan_digest'],
               'preflight':{'path':prior_preflight.logical_path,'sha256':prior_preflight.sha256,
                            'binding_sha256':report['binding_sha256']},
               'source_ledger':{'path':str(M.OLD_ROOT/'ledger.json'),'sha256':sha256_file(ledger_path),
                                'ledger_digest':ledger['ledger_digest']},
               'environment':X._environment(COMMIT),
               'roots':{k:prior_preflight.logical_roots[k] for k in ('output','staging','sync')},
               'attempt_timeout_seconds':3600.0,'lease':lease,
               'fixed_worker':'bu.experiments.week8_exp2a_repair_launch._fit_worker',
               'supervisor_required':'bu.experiments.supervisor.run_isolated_attempt',
               'automatic_retry_allowed':False}
    context = X._execution_context(payload)
    document = W._seal({**payload,'execution_context_digest':context['execution_context_digest']},'checkpoint_digest')
    documents = list(prior_sources.access._documents)
    documents.append(R.Document(archived.relative_to(root).as_posix(),sha256_file(archived)))
    for role in ('output','sync'):
        for relative,record in [(Path(W.START_DIRECTORY)/f'{token}.json',document),(Path(W.CONTEXT_FILE),context)]:
            file = atomic_write_json(roots[role]/relative,record)
            documents.append(R.Document(file.relative_to(root).as_posix(),sha256_file(file)))
    pairs = prior_sources.access._pairs
    raw = R.build_record(root,pairs,tuple(documents))
    access = R.EvidenceAccess(raw,sha(raw),root,pairs,tuple(documents))
    sources = M.SourceReaders(access,W,S,ledger_logical_path=prior_sources.ledger_logical_path,
                              ledger_sha256=prior_sources.ledger_sha256)
    preflight = M.PreflightReaders(access,sources,X,Storage,preflight_sha256=prior_preflight.sha256)
    path = roots['output']/W.START_DIRECTORY/f'{token}.json'
    checkpoints = M.CheckpointReaders(access,preflight,old_sha256=sha256_file(path),
                                      old_checkpoint_digest=document['checkpoint_digest'],
                                      old_context_digest=context['execution_context_digest'])
    store.loads.clear()
    return roots,sources,preflight,checkpoints,path,document,active,store


def test_historical_checkpoint_returns_exact_original_bytes_and_current_roots(relocated_checkpoint):
    roots,sources,preflight,checkpoints,path,original,active,store = relocated_checkpoint
    before = path.read_bytes()
    original_reader = X._read_start
    with sources.installed(),preflight.installed(),checkpoints.installed():
        start,ledger,current = X._load_start(path,expected_sha256=sha(before),expected_git_commit=COMMIT)
        assert start == original
        assert current == {k:roots[k] for k in ('output','staging','sync')}
        assert start['lease']['path'] != str(active)
        assert start['execution_context_digest'] == checkpoints.old_context_digest
        assert store.loads == []
    assert X._read_start is original_reader and path.read_bytes() == before


@pytest.mark.parametrize('which',['pin','local-path','context','twin','active-lease','commit'])
def test_historical_checkpoint_refuses_drift(relocated_checkpoint,which):
    roots,sources,preflight,checkpoints,path,original,active,_ = relocated_checkpoint
    expected_sha = checkpoints.old_sha256
    commit = COMMIT
    if which == 'pin':expected_sha = '0'*64
    elif which == 'local-path':path = roots['sync']/W.START_DIRECTORY/path.name
    elif which == 'context':(roots['sync']/W.CONTEXT_FILE).write_bytes(b'changed context')
    elif which == 'twin':(roots['sync']/W.START_DIRECTORY/path.name).write_bytes(b'changed checkpoint')
    elif which == 'active-lease':
        lease = json.loads(active.read_bytes())
        lease['timestamp_utc'] = '2026-09-02T20:28:27.533758Z'
        active.write_bytes(X.L._pretty_json_bytes(lease))
    else:commit = 'f'*40
    with sources.installed(),preflight.installed(),checkpoints.installed():
        with pytest.raises(ValueError):
            X._load_start(path,expected_sha256=expected_sha,expected_git_commit=commit)


def test_released_checkpoint_requires_absent_active_lease_and_original_orphan_guard(relocated_checkpoint,monkeypatch):
    _,sources,preflight,checkpoints,path,_,active,_ = relocated_checkpoint
    calls = []
    def orphan_guard(token):
        calls.append(token)
        raise ValueError('synthetic orphan transition not proved')
    monkeypatch.setattr(X,'_historical_lease_record',orphan_guard)
    with sources.installed(),preflight.installed(),checkpoints.installed():
        with pytest.raises(ValueError,match='no active shared lease'):
            X._read_start(path,expected_sha256=checkpoints.old_sha256,expected_git_commit=COMMIT,released=True)
        assert calls == []
        active.unlink()
        with pytest.raises(ValueError,match='orphan transition not proved'):
            X._read_start(path,expected_sha256=checkpoints.old_sha256,expected_git_commit=COMMIT,released=True)
        assert calls == [checkpoints.old_token]


def test_historical_checkpoint_proves_orphan_history_without_releasing_current_lease(relocated_checkpoint,monkeypatch):
    _,sources,preflight,checkpoints,path,original,active,_ = relocated_checkpoint
    proof = X._lease_record(checkpoints.old_token)
    calls = []
    monkeypatch.setattr(X,'_historical_lease_record',lambda token:calls.append(token) or proof)
    before = active.read_bytes()
    with sources.installed(),preflight.installed(),checkpoints.installed():
        start,_,_ = checkpoints.historical_start(path,expected_sha256=checkpoints.old_sha256,
                                                 expected_git_commit=COMMIT,lease_mode='historical')
        assert start == original and calls == [checkpoints.old_token,checkpoints.old_token]
    assert active.read_bytes() == before


def test_checkpoint_scope_detects_tampering_and_restores(relocated_checkpoint):
    _,sources,preflight,checkpoints,_,_,_,_ = relocated_checkpoint
    original = X._read_start
    with sources.installed(),preflight.installed():
        with pytest.raises(M.MetadataRefused,match='restoration'):
            with checkpoints.installed():
                X._read_start = lambda *a,**k:None
        assert X._read_start is original


@pytest.fixture
def relocation_epoch(relocated_checkpoint,monkeypatch):
    roots,sources,preflight,checkpoints,path,original,active,store = relocated_checkpoint
    old_proof = X._lease_record(checkpoints.old_token)
    historical = X._historical_lease_record
    # Synthetic stand-in for the independently tested D-161 orphan transition.
    # Never create a normal released-history file for the original token.
    active.unlink()
    monkeypatch.setattr(X,'_historical_lease_record',lambda token:
                        old_proof if token == checkpoints.old_token else historical(token))
    with acquire_batch_lease(W.COMMON_LEASE_ROOT,lease_name=W.COMMON_LEASE_NAME) as lease:
        arguments = {'source_ledger_path':sources.ledger_logical_path,'expected_git_commit':COMMIT,
                     'output_root':roots['output'],'staging_root':roots['staging'],'sync_root':roots['sync'],
                     'attempt_timeout_seconds':3600.0,'lease':lease,
                     'preflight_report':roots['preflight']/X.PREFLIGHT_FILE}
        yield roots,sources,preflight,checkpoints,path,original,lease,arguments


@pytest.fixture
def relocated_new_start(relocation_epoch):
    roots,sources,preflight,checkpoints,old_path,original,lease,arguments = relocation_epoch
    with sources.installed(),preflight.installed(),checkpoints.installed():
        new_path = X.write_exp2a_repair_start_checkpoint(**arguments)
        yield relocation_epoch,new_path


def test_new_checkpoint_uses_current_paths_and_preserves_old_epoch(relocation_epoch):
    roots,sources,preflight,checkpoints,old_path,original,lease,arguments = relocation_epoch
    preserved = {roots[role]/relative:(roots[role]/relative).read_bytes()
                 for role in ('output','sync')
                 for relative in (Path(W.START_DIRECTORY)/old_path.name,Path(W.CONTEXT_FILE))}
    science = X._fit_worker
    with sources.installed(),preflight.installed(),checkpoints.installed():
        path = X.write_exp2a_repair_start_checkpoint(**arguments)
        start,_,actual = X._load_start(path,expected_sha256=sha256_file(path),expected_git_commit=COMMIT)
        assert start['exp2a_repair_start_schema_version'] == 2
        assert start['execution_context_digest'] != original['execution_context_digest']
        assert start['relocation'] == checkpoints.relocation_binding()
        assert start['lease']['path'] == str(lease.path)
        assert start['preflight']['path'] == str(roots['preflight']/X.PREFLIGHT_FILE)
        assert start['source_ledger']['path'] == str(W.WORKSPACE_ROOT/'ledger.json')
        assert start['roots'] == {k:str(v) for k,v in actual.items()}
        for key in ('environment','attempt_timeout_seconds','plan_digest','fixed_worker',
                    'supervisor_required','automatic_retry_allowed'):
            assert start[key] == original[key]
        context = json.loads((roots['output']/M.RELOCATION_CONTEXT_FILE).read_bytes())
        assert context == X._execution_context(start)
        assert (roots['sync']/M.RELOCATION_CONTEXT_FILE).read_bytes() == X.L._pretty_json_bytes(context)
        assert len(list((roots['output']/W.START_DIRECTORY).iterdir())) == 2
        assert X._fit_worker is science
    assert all(path.read_bytes() == raw for path,raw in preserved.items())


def test_new_checkpoint_refuses_replay_without_changing_either_epoch(relocated_new_start):
    epoch,path = relocated_new_start
    roots,_,_,_,_,_,_,arguments = epoch
    before = {p:p.read_bytes() for role in ('output','sync') for p in (
        roots[role]/M.RELOCATION_CONTEXT_FILE,roots[role]/W.START_DIRECTORY/path.name)}
    with pytest.raises(M.MetadataRefused,match='checkpoint inventory'):
        X.write_exp2a_repair_start_checkpoint(**arguments)
    assert all(p.read_bytes() == raw for p,raw in before.items())


def test_partial_context_publication_remains_stop_evidence(relocation_epoch,monkeypatch):
    roots,sources,preflight,checkpoints,_,_,_,arguments = relocation_epoch
    original_write = X.atomic_write_json
    def interrupt(path,value):
        if Path(path) == roots['output']/M.RELOCATION_CONTEXT_FILE:
            raise OSError('synthetic interruption after first context copy')
        return original_write(path,value)
    monkeypatch.setattr(X,'atomic_write_json',interrupt)
    with sources.installed(),preflight.installed(),checkpoints.installed():
        with pytest.raises(OSError,match='synthetic interruption'):
            X.write_exp2a_repair_start_checkpoint(**arguments)
        partial = roots['sync']/M.RELOCATION_CONTEXT_FILE
        before = partial.read_bytes()
        assert not (roots['output']/M.RELOCATION_CONTEXT_FILE).exists()
        assert len(list((roots['output']/W.START_DIRECTORY).iterdir())) == 1
        with pytest.raises(M.MetadataRefused,match='replay or healing forbidden'):
            X.write_exp2a_repair_start_checkpoint(**arguments)
        assert partial.read_bytes() == before
        assert not (roots['output']/M.RELOCATION_CONTEXT_FILE).exists()


@pytest.mark.parametrize('which',['orphan-proof','lease-owner'])
def test_new_writer_requires_orphan_proof_and_own_lease(relocation_epoch,monkeypatch,which):
    roots,sources,preflight,checkpoints,_,_,lease,arguments = relocation_epoch
    if which == 'orphan-proof':
        def refuse(token):raise ValueError('synthetic orphan transition refused')
        monkeypatch.setattr(X,'_historical_lease_record',refuse)
    else:
        row = json.loads(lease.path.read_bytes())
        row['pid'] += 1
        lease.path.write_bytes(X.L._pretty_json_bytes(row))
    with sources.installed(),preflight.installed(),checkpoints.installed():
        with pytest.raises(ValueError):X.write_exp2a_repair_start_checkpoint(**arguments)
        assert all(not (roots[role]/M.RELOCATION_CONTEXT_FILE).exists() for role in ('output','sync'))
        assert len(list((roots['output']/W.START_DIRECTORY).iterdir())) == 1


@pytest.mark.parametrize('which',['attestation','threads','old-path','version-type','old-context'])
def test_new_reader_rejects_resealed_semantic_drift(relocated_new_start,which):
    epoch,path = relocated_new_start
    roots,_,_,checkpoints,_,_,_,_ = epoch
    document = json.loads(path.read_bytes())
    if which == 'attestation':document['relocation']['attestation_sha256'] = 'f'*64
    elif which == 'threads':document['environment']['num_threads'] = 3
    elif which == 'old-path':document['source_ledger']['path'] = str(M.OLD_ROOT/'ledger.json')
    elif which == 'version-type':document['exp2a_repair_start_schema_version'] = 2.0
    context = X._execution_context(document)
    document['execution_context_digest'] = context['execution_context_digest']
    if which == 'old-context':document['execution_context_digest'] = checkpoints.old_context_digest
    document = W._seal({k:v for k,v in document.items() if k != 'checkpoint_digest'},'checkpoint_digest')
    for role in ('output','sync'):
        (roots[role]/W.START_DIRECTORY/path.name).write_bytes(X.L._pretty_json_bytes(document))
        (roots[role]/M.RELOCATION_CONTEXT_FILE).write_bytes(X.L._pretty_json_bytes(context))
    with pytest.raises(M.MetadataRefused,match='schema/seal/original binding'):
        X._load_start(path,expected_sha256=sha256_file(path),expected_git_commit=COMMIT)


def test_new_reader_never_heals_missing_context_twin(relocated_new_start):
    epoch,path = relocated_new_start
    roots = epoch[0]
    twin = roots['sync']/M.RELOCATION_CONTEXT_FILE
    twin.unlink()
    with pytest.raises(ValueError):
        X._load_start(path,expected_sha256=sha256_file(path),expected_git_commit=COMMIT)
    assert not twin.exists()


def test_new_reader_refuses_a_third_checkpoint(relocated_new_start):
    epoch,path = relocated_new_start
    roots = epoch[0]
    for role in ('output','sync'):
        atomic_write_json(roots[role]/W.START_DIRECTORY/('f'*32+'.json'),{'unexpected':'third epoch'})
    with pytest.raises(M.MetadataRefused,match='another epoch'):
        X._load_start(path,expected_sha256=sha256_file(path),expected_git_commit=COMMIT)


def test_prior_start_bridge_accepts_only_the_two_verified_epochs(relocated_new_start):
    epoch,path = relocated_new_start
    roots,_,_,checkpoints,_,old,_,_ = epoch
    current = json.loads(path.read_bytes())
    for digest in (old['checkpoint_digest'],current['checkpoint_digest']):
        X._verify_prior_start(digest,current,roots)
    with pytest.raises(M.MetadataRefused,match='sole relocated epoch'):
        X._verify_prior_start('f'*64,current,roots)
    current['environment']['num_threads'] = 3
    with pytest.raises(M.MetadataRefused,match='sole relocated epoch'):
        X._verify_prior_start(old['checkpoint_digest'],current,roots)


def test_new_checkpoint_released_read_uses_real_released_lease_history(relocated_new_start):
    epoch,path = relocated_new_start
    _,_,_,_,_,_,lease,_ = epoch
    expected_sha = sha256_file(path)
    with pytest.raises(ValueError,match='no active shared lease'):
        X._read_start(path,expected_sha256=expected_sha,expected_git_commit=COMMIT,released=True)
    history = lease.release()
    start,_,_ = X._read_start(path,expected_sha256=expected_sha,expected_git_commit=COMMIT,released=True)
    assert start['lease']['sha256'] == sha256_file(history)
    assert not lease.path.exists()
    with pytest.raises(ValueError):
        X._load_start(path,expected_sha256=expected_sha,expected_git_commit=COMMIT)


def test_historical_lease_change_during_read_is_refused(relocated_checkpoint,monkeypatch):
    _,sources,preflight,checkpoints,path,_,_,_ = relocated_checkpoint
    proof = X._lease_record(checkpoints.old_token)
    calls = []
    def changing(token):
        calls.append(token)
        return proof if len(calls) == 1 else {**proof,'sha256':'f'*64}
    monkeypatch.setattr(X,'_historical_lease_record',changing)
    with sources.installed(),preflight.installed(),checkpoints.installed():
        with pytest.raises(M.MetadataRefused,match='lease proof changed during'):
            checkpoints.historical_start(path,expected_sha256=checkpoints.old_sha256,
                                          expected_git_commit=COMMIT,lease_mode='historical')


def test_prior_start_rejects_invalid_token_before_file_access(relocated_checkpoint,monkeypatch):
    roots,sources,preflight,checkpoints,_,original,_,_ = relocated_checkpoint
    def unexpected_read(relative):pytest.fail('invalid token reached current file access')
    monkeypatch.setattr(checkpoints,'_current_twins',unexpected_read)
    with sources.installed(),preflight.installed(),checkpoints.installed():
        for token in ('../../unrelated',None,123,'F'*32):
            current = copy.deepcopy(original)
            current['lease']['token'] = token
            with pytest.raises(M.MetadataRefused,match='token is not canonical'):
                X._verify_prior_start(original['checkpoint_digest'],current,roots)


def baseline_for(job):
    return next(j for j in W.registered_exp2a_jobs()
                if j.arm == 'baseline' and j.unit == job.unit and j.seed == job.seed)


def copy_synthetic_fit(store,source,destination):
    destination.mkdir(parents=True,exist_ok=True)
    for path in source.iterdir():
        assert path.is_file()
        (destination/path.name).write_bytes(path.read_bytes())
    commit,verified = store.entries[source.resolve()]
    store.entries[destination.resolve()] = commit,replace(verified,fit_dir=destination.resolve())


@pytest.fixture
def completed_history(relocated_checkpoint):
    roots,prior_sources,prior_preflight,prior_checkpoints,old_path,old,active,store = relocated_checkpoint
    root = W.WORKSPACE_ROOT
    jobs = W.new_exp2a_jobs()
    new_baseline = next(j for j in jobs if j.arm == 'baseline' and
                        any(r.arm == 'data_repair' and r.unit == j.unit and r.seed == j.seed for r in jobs))
    new_baseline_repair = next(j for j in jobs if j.arm == 'data_repair' and
                              j.unit == new_baseline.unit and j.seed == new_baseline.seed)
    historical_repair = next(j for j in jobs if j.arm == 'data_repair' and W.source_kind(baseline_for(j)) is not None)
    orphan = next(j for j in jobs if j.job_id == M.ORPHAN_JOB_ID)
    ledger = json.loads((root/'ledger.json').read_bytes())
    historical_rows = {row['job']['job_id']:row for row in ledger['sources']}
    pairs = list(prior_sources.access._pairs)
    completed = {}
    def preserve(job,binding=None,*,paired=True):
        source = root/'before-move-output'/'jobs'/job.job_id
        destination = root/'before-move-sync'/'jobs'/job.job_id
        verified = store.persist(source,job,COMMIT,sha(('old:'+job.job_id).encode()))
        atomic_write_json(source/'job_result.json',X._result_record(
            job,verified,commit=COMMIT,checkpoint_digest=old['checkpoint_digest'],
            binding=binding,execution_context_digest=old['execution_context_digest']))
        logical_source = str(M.OLD_ROOT/M.PRODUCTION_FOLDERS['output']/'jobs'/job.job_id)
        logical_copy = str(M.OLD_ROOT/M.PRODUCTION_FOLDERS['sync']/'jobs'/job.job_id)
        legacy = None
        if paired:
            copy_synthetic_fit(store,source,destination)
            _,row = S._source_pair(job,source,destination,commit=COMMIT)
            legacy = {**row,'source_path':logical_source,'copy_path':logical_copy}
        current = roots['output']/'jobs'/job.job_id
        copy_synthetic_fit(store,source,current)
        if paired:
            remote = roots['sync']/'jobs'/job.job_id
            copy_synthetic_fit(store,destination,remote)
            pairs.append(R.Pair('epoch001-'+job.job_id,logical_source,logical_copy,
                current.relative_to(root).as_posix(),remote.relative_to(root).as_posix(),
                legacy['source_tree_digest'],legacy['copy_evidence_digest']))
        completed[job.job_id] = job
        return legacy
    needed_baselines = {new_baseline.job_id:new_baseline}
    orphan_baseline = baseline_for(orphan)
    if W.source_kind(orphan_baseline) is None:needed_baselines[orphan_baseline.job_id] = orphan_baseline
    legacy_rows = {key:preserve(job) for key,job in needed_baselines.items()}
    preserve(new_baseline_repair,legacy_rows[new_baseline.job_id])
    preserve(historical_repair,historical_rows[baseline_for(historical_repair).job_id])
    orphan_binding = (historical_rows.get(orphan_baseline.job_id) or legacy_rows[orphan_baseline.job_id])
    preserve(orphan,orphan_binding,paired=False)
    documents = prior_sources.access._documents
    raw = R.build_record(root,tuple(pairs),documents)
    access = R.EvidenceAccess(raw,sha(raw),root,tuple(pairs),documents)
    sources = M.SourceReaders(access,W,S,ledger_logical_path=prior_sources.ledger_logical_path,
                              ledger_sha256=prior_sources.ledger_sha256)
    preflight = M.PreflightReaders(access,sources,X,Storage,preflight_sha256=prior_preflight.sha256)
    checkpoints = M.CheckpointReaders(access,preflight,old_sha256=prior_checkpoints.old_sha256,
        old_checkpoint_digest=prior_checkpoints.old_checkpoint_digest,old_context_digest=prior_checkpoints.old_context_digest)
    readers = M.CompletedJobReaders(access,checkpoints)
    store.loads.clear()
    return {'roots':roots,'sources':sources,'preflight':preflight,'checkpoints':checkpoints,'readers':readers,
            'old_path':old_path,'old':old,'active':active,'store':store,'ledger':ledger,'access':access,
            'new_baseline':new_baseline,'new_baseline_repair':new_baseline_repair,
            'historical_repair':historical_repair,'orphan':orphan,'completed':completed,'legacy_rows':legacy_rows}


@pytest.fixture
def completed_epoch(completed_history,monkeypatch):
    data = completed_history
    roots,checkpoints = data['roots'],data['checkpoints']
    proof = X._lease_record(checkpoints.old_token)
    historical = X._historical_lease_record
    data['active'].unlink()
    monkeypatch.setattr(X,'_historical_lease_record',lambda token:
                        proof if token == checkpoints.old_token else historical(token))
    with acquire_batch_lease(W.COMMON_LEASE_ROOT,lease_name=W.COMMON_LEASE_NAME) as lease:
        with data['sources'].installed(),data['preflight'].installed(),checkpoints.installed(),data['readers'].installed():
            path = X.write_exp2a_repair_start_checkpoint(
                source_ledger_path=data['sources'].ledger_logical_path,expected_git_commit=COMMIT,
                output_root=roots['output'],staging_root=roots['staging'],sync_root=roots['sync'],
                attempt_timeout_seconds=3600,lease=lease,preflight_report=roots['preflight']/X.PREFLIGHT_FILE)
            yield {**data,'new_path':path,'new':json.loads(path.read_bytes()),'lease':lease}


def test_completed_old_fits_keep_original_results_and_scientific_pairing(completed_history,monkeypatch):
    d = completed_history
    def no_training(*a,**k):pytest.fail('metadata verification attempted training')
    monkeypatch.setattr(X.F,'run_confirmatory_fit',no_training)
    before = {j:d['roots']['output']/'jobs'/j/'job_result.json' for j in d['completed']}
    raw = {j:path.read_bytes() for j,path in before.items()}
    with d['sources'].installed(),d['preflight'].installed(),d['checkpoints'].installed(),d['readers'].installed():
        for job in d['completed'].values():
            result = X._local_completed(job,d['old'],d['ledger'],d['roots'],COMMIT)
            assert result['result'] == json.loads(raw[job.job_id])
            assert result['execution_digest'] == result['result']['fit_evidence_digest']
    assert all(path.read_bytes() == raw[j] for j,path in before.items())
    assert d['store'].loads


def test_new_baseline_binding_separates_historical_and_current_observations(completed_history):
    d = completed_history
    with d['sources'].installed(),d['preflight'].installed(),d['checkpoints'].installed(),d['readers'].installed():
        for key,kind in [('historical_repair','historical_source_ledger'),('new_baseline_repair','preserved_epoch001_baseline')]:
            _,binding = X._baseline(d[key],d['ledger'],d['roots'],COMMIT,d['old'])
            assert binding['baseline_binding_schema_version'] == 2
            assert binding['origin']['kind'] == kind
            assert Path(binding['source']['source_path']).exists()
            assert binding['source']['copy_evidence_digest'] != binding['origin']['source']['copy_evidence_digest']
            assert binding['relocation']['attestation_sha256'] == d['access'].attestation_sha256


def test_old_fits_validate_under_new_context_without_rewriting_results(completed_epoch):
    d = completed_epoch
    for key in ('new_baseline_repair','historical_repair','orphan'):
        job = d[key]
        result = X._local_completed(job,d['new'],d['ledger'],d['roots'],COMMIT)['result']
        assert result['checkpoint_digest'] == d['old']['checkpoint_digest']
        assert result['execution_context_digest'] == d['old']['execution_context_digest']
        assert 'baseline_binding_schema_version' not in result['baseline_source']


def persist_new_repair(d):
    baseline = d['new_baseline']
    job = next(j for j in W.new_exp2a_jobs() if j.arm == 'feature_repair' and
               j.unit == baseline.unit and j.seed == baseline.seed and j.job_id not in d['completed'])
    _,binding = X._baseline(job,d['ledger'],d['roots'],COMMIT,d['new'])
    local = d['roots']['output']/'jobs'/job.job_id
    verified = d['store'].persist(local,job,COMMIT,sha(('new:'+job.job_id).encode()))
    result = X._result_record(job,verified,commit=COMMIT,checkpoint_digest=d['new']['checkpoint_digest'],
                             binding=binding,execution_context_digest=d['new']['execution_context_digest'])
    path = atomic_write_json(local/'job_result.json',result)
    return job,path,result


def test_new_repair_result_requires_current_baseline_provenance(completed_epoch):
    d = completed_epoch
    job,path,result = persist_new_repair(d)
    assert X._local_completed(job,d['new'],d['ledger'],d['roots'],COMMIT)['result'] == result
    result['baseline_source'] = result['baseline_source']['origin']['source']
    path.write_bytes(X.L._pretty_json_bytes(result))
    with pytest.raises(M.MetadataRefused,match='exact epoch and baseline provenance'):
        X._local_completed(job,d['new'],d['ledger'],d['roots'],COMMIT)


def test_changed_preserved_result_is_rejected_before_scientific_load(completed_history):
    d = completed_history
    job = d['new_baseline_repair']
    path = d['roots']['output']/'jobs'/job.job_id/'job_result.json'
    path.write_bytes(path.read_bytes()+b'\n')
    with d['sources'].installed(),d['preflight'].installed(),d['checkpoints'].installed(),d['readers'].installed():
        with pytest.raises(R.RelocationRefused):X._local_completed(job,d['old'],d['ledger'],d['roots'],COMMIT)
    assert d['store'].loads == []


def test_original_scientific_pairing_still_rejects_wrong_encoded_pool(completed_history):
    d = completed_history
    job = d['new_baseline_repair']
    path = (d['roots']['output']/'jobs'/job.job_id).resolve()
    commit,verified = d['store'].entries[path]
    d['store'].entries[path] = commit,replace(verified,evaluation_pool_digest='f'*64)
    with d['sources'].installed(),d['preflight'].installed(),d['checkpoints'].installed(),d['readers'].installed():
        with pytest.raises(ValueError,match='encoded evaluation pool'):
            X._local_completed(job,d['old'],d['ledger'],d['roots'],COMMIT)


def test_new_epoch_baseline_is_not_misclassified_as_historical(completed_epoch):
    d = completed_epoch
    baseline = next(j for j in W.new_exp2a_jobs() if j.arm == 'baseline' and j.job_id not in d['completed'])
    job = next(j for j in W.new_exp2a_jobs() if j.arm == 'data_repair' and
               j.unit == baseline.unit and j.seed == baseline.seed)
    local = d['roots']['output']/'jobs'/baseline.job_id
    verified = d['store'].persist(local,baseline,COMMIT,sha(('new:'+baseline.job_id).encode()))
    atomic_write_json(local/'job_result.json',X._result_record(baseline,verified,commit=COMMIT,
        checkpoint_digest=d['new']['checkpoint_digest'],binding=None,
        execution_context_digest=d['new']['execution_context_digest']))
    copy_synthetic_fit(d['store'],local,d['roots']['sync']/'jobs'/baseline.job_id)
    _,binding = X._baseline(job,d['ledger'],d['roots'],COMMIT,d['new'])
    assert binding['origin'] == {'kind':'relocated_epoch_baseline',
        'checkpoint_digest':d['new']['checkpoint_digest'],'execution_context_digest':d['new']['execution_context_digest']}
    assert binding['source']['copy_evidence_digest'] == X.B._copy_evidence_digest(
        local,d['roots']['sync']/'jobs'/baseline.job_id)


def test_unpaired_orphan_validates_locally_then_reconciles_only_after_copy(completed_epoch):
    d = completed_epoch
    orphan = d['orphan']
    local = d['roots']['output']/'jobs'/orphan.job_id
    destination = d['roots']['sync']/'jobs'/orphan.job_id
    before = (local/'job_result.json').read_bytes()
    X._local_completed(orphan,d['new'],d['ledger'],d['roots'],COMMIT)
    with pytest.raises(ValueError,match='partial local/durable'):
        X._completed_source_pair(orphan,d['new'],d['ledger'],d['roots'],COMMIT)
    assert not destination.exists()
    copy_synthetic_fit(d['store'],local,destination)
    actual = X._completed_source_pair(orphan,d['new'],d['ledger'],d['roots'],COMMIT)
    assert actual['copy_evidence_digest'] == X.B._copy_evidence_digest(local,destination)
    assert (local/'job_result.json').read_bytes() == before


def test_completed_adapter_restores_its_owned_seams_after_error(completed_history):
    d = completed_history
    before = X._baseline,X._local_completed
    with d['sources'].installed(),d['preflight'].installed(),d['checkpoints'].installed():
        with pytest.raises(RuntimeError,match='synthetic failure'):
            with d['readers'].installed():raise RuntimeError('synthetic failure')
        assert (X._baseline,X._local_completed) == before


@pytest.mark.parametrize('target',['repair','baseline','orphan'])
def test_preserved_job_cannot_relabel_itself_as_a_new_epoch(completed_epoch,target):
    d = completed_epoch
    job = d['new_baseline'] if target == 'baseline' else d['orphan'] if target == 'orphan' else d['new_baseline_repair']
    path = d['roots']['output']/'jobs'/job.job_id/'job_result.json'
    result = json.loads(path.read_bytes())
    result['checkpoint_digest'] = d['new']['checkpoint_digest']
    result['execution_context_digest'] = d['new']['execution_context_digest']
    if job.arm != 'baseline':
        _,result['baseline_source'] = X._baseline(job,d['ledger'],d['roots'],COMMIT,d['new'])
    path.write_bytes(X.L._pretty_json_bytes(result))
    with pytest.raises((R.RelocationRefused,M.MetadataRefused)):
        X._local_completed(job,d['new'],d['ledger'],d['roots'],COMMIT)
    if target == 'baseline':
        with pytest.raises(R.RelocationRefused):
            X._baseline(d['new_baseline_repair'],d['ledger'],d['roots'],COMMIT,d['new'])


@pytest.mark.parametrize('target',['result-schema','binding-schema'])
def test_new_repair_requires_exact_numeric_schema_types(completed_epoch,target):
    d = completed_epoch
    job,path,result = persist_new_repair(d)
    if target == 'result-schema':result['exp2a_repair_result_schema_version'] = 1.0
    else:result['baseline_source']['baseline_binding_schema_version'] = 2.0
    path.write_bytes(X.L._pretty_json_bytes(result))
    with pytest.raises(M.MetadataRefused,match='exact epoch and baseline provenance'):
        X._local_completed(job,d['new'],d['ledger'],d['roots'],COMMIT)


def test_new_baseline_requires_exact_result_schema_type(completed_epoch):
    d = completed_epoch
    baseline = next(j for j in W.new_exp2a_jobs() if j.arm == 'baseline' and j.job_id not in d['completed'])
    job = next(j for j in W.new_exp2a_jobs() if j.arm == 'data_repair' and
               j.unit == baseline.unit and j.seed == baseline.seed)
    local = d['roots']['output']/'jobs'/baseline.job_id
    verified = d['store'].persist(local,baseline,COMMIT,sha(('new:'+baseline.job_id).encode()))
    result = X._result_record(baseline,verified,commit=COMMIT,checkpoint_digest=d['new']['checkpoint_digest'],
                             binding=None,execution_context_digest=d['new']['execution_context_digest'])
    result['exp2a_repair_result_schema_version'] = 1.0
    atomic_write_json(local/'job_result.json',result)
    copy_synthetic_fit(d['store'],local,d['roots']['sync']/'jobs'/baseline.job_id)
    with pytest.raises(M.MetadataRefused,match='baseline result does not bind'):
        X._baseline(job,d['ledger'],d['roots'],COMMIT,d['new'])


def sealed_event(rows,start,kind,job_id,data):
    return W._seal({'event_schema_version':1,'sequence':len(rows),
        'previous_digest':rows[-1]['event_digest'] if rows else None,
        'execution_context_digest':start['execution_context_digest'],
        'kind':kind,'job_id':job_id,'data':data},'event_digest')


@pytest.fixture
def event_history(completed_history):
    d = completed_history
    rows = []
    documents = list(d['access']._documents)
    for job in d['completed'].values():
        rows.append(sealed_event(rows,d['old'],'attempt_started',job.job_id,
                                {'checkpoint_digest':d['old']['checkpoint_digest']}))
        if job.job_id != M.ORPHAN_JOB_ID:
            local,remote = (d['roots'][role]/'jobs'/job.job_id for role in ('output','sync'))
            observation = d['access'].historical_pair_at(local,remote)
            verified = d['store'].entries[local.resolve()][1]
            rows.append(sealed_event(rows,d['old'],'job_synced',job.job_id,{
                'execution_digest':verified.execution_digest,
                'source_tree_digest':observation.policy.content_digest,
                'copy_evidence_digest':observation.historical_copy_digest}))
    for row in rows:
        for role in ('output','sync'):
            path = atomic_write_json(d['roots'][role]/X.EVENT_DIRECTORY/f"{row['sequence']:06d}.json",row)
            documents.append(R.Document(path.relative_to(W.WORKSPACE_ROOT).as_posix(),sha256_file(path)))
    pairs = d['access']._pairs
    raw = R.build_record(W.WORKSPACE_ROOT,pairs,tuple(documents))
    access = R.EvidenceAccess(raw,sha(raw),W.WORKSPACE_ROOT,pairs,tuple(documents))
    sources = M.SourceReaders(access,W,S,ledger_logical_path=d['sources'].ledger_logical_path,
                              ledger_sha256=d['sources'].ledger_sha256)
    preflight = M.PreflightReaders(access,sources,X,Storage,preflight_sha256=d['preflight'].sha256)
    prior = d['checkpoints']
    checkpoints = M.CheckpointReaders(access,preflight,old_sha256=prior.old_sha256,
        old_checkpoint_digest=prior.old_checkpoint_digest,old_context_digest=prior.old_context_digest)
    completed = M.CompletedJobReaders(access,checkpoints)
    events = M.EventReaders(access,checkpoints,old_count=len(rows),old_started=len(d['completed']),
        old_synced=len(d['completed'])-1,
        old_chain_sha256=sha(json.dumps([r['event_digest'] for r in rows],sort_keys=True,
                              separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')),
        old_tail_sha256=sha(X.L._pretty_json_bytes(rows[-1])))
    return {**d,'access':access,'sources':sources,'preflight':preflight,'checkpoints':checkpoints,
            'readers':completed,'event_readers':events,'reuse':M.ReuseReader(access,completed,events),
            'original_events':rows}


@pytest.fixture
def event_epoch(event_history,monkeypatch):
    d = event_history
    roots,checkpoints = d['roots'],d['checkpoints']
    proof = X._lease_record(checkpoints.old_token)
    historical = X._historical_lease_record
    d['active'].unlink()
    monkeypatch.setattr(X,'_historical_lease_record',lambda token:
                        proof if token == checkpoints.old_token else historical(token))
    with acquire_batch_lease(W.COMMON_LEASE_ROOT,lease_name=W.COMMON_LEASE_NAME) as lease:
        with d['sources'].installed(),d['preflight'].installed(),checkpoints.installed(),d['readers'].installed():
            path = X.write_exp2a_repair_start_checkpoint(
                source_ledger_path=d['sources'].ledger_logical_path,expected_git_commit=COMMIT,
                output_root=roots['output'],staging_root=roots['staging'],sync_root=roots['sync'],
                attempt_timeout_seconds=3600,lease=lease,preflight_report=roots['preflight']/X.PREFLIGHT_FILE)
            with d['event_readers'].installed(),d['reuse'].installed():
                start = json.loads(path.read_bytes())
                events = X._load_events(roots,start)
                validated = X.validate_exp2a_repair_preflight(roots['preflight']/X.PREFLIGHT_FILE,
                    output_root=roots['output'],sync_root=roots['sync'],expected_git_commit=COMMIT)
                yield {**d,'new_path':path,'new':start,'events':events,'validated':validated}


def append_test_event(d,kind,job_id,data):
    X._append_event(d['roots'],d['new'],d['events'],kind=kind,job_id=job_id,data=data)


def test_event_reuse_keeps_original_bytes_and_current_pair_identity(event_epoch,monkeypatch):
    d = event_epoch
    def no_publish(*a,**k):pytest.fail('already synced fit was copied again')
    def no_training(*a,**k):pytest.fail('preserved fit was retrained')
    monkeypatch.setattr(X.B,'_publish_job_tree',no_publish)
    monkeypatch.setattr(X,'run_isolated_attempt',no_training)
    before = copy.deepcopy(d['events'])
    for job in d['completed'].values():
        if job.job_id == M.ORPHAN_JOB_ID:continue
        assert X._run_one_job(job,validated=d['validated'],checkpoint_path=d['new_path'],
                             start=d['new'],events=d['events']) == 'resumed'
    assert d['events'] == before == d['original_events']
    assert X._load_events(d['roots'],d['new']) == before
    assert all(r['execution_context_digest'] == d['old']['execution_context_digest'] for r in before)


def test_event_orphan_uses_original_sync_without_another_attempt(event_epoch,monkeypatch):
    d = event_epoch
    publish = X.B._publish_job_tree
    calls = []
    def copy_and_register(source,destination):
        calls.append((source,destination))
        publish(source,destination)
        commit,verified = d['store'].entries[source.resolve()]
        d['store'].entries[destination.resolve()] = commit,replace(verified,fit_dir=destination.resolve())
    monkeypatch.setattr(X.B,'_publish_job_tree',copy_and_register)
    monkeypatch.setattr(X,'run_isolated_attempt',lambda *a,**k:pytest.fail('orphan retraining'))
    assert X._run_one_job(d['orphan'],validated=d['validated'],checkpoint_path=d['new_path'],
                         start=d['new'],events=d['events']) == 'resumed'
    assert len(calls) == 1
    assert d['events'][:-1] == d['original_events']
    tail = d['events'][-1]
    assert tail['kind'] == 'job_synced' and tail['job_id'] == M.ORPHAN_JOB_ID
    assert tail['execution_context_digest'] == d['new']['execution_context_digest']
    assert tail['previous_digest'] == d['original_events'][-1]['event_digest']
    assert tail['data']['copy_evidence_digest'] == X.B._copy_evidence_digest(*calls[0])
    assert X._load_events(d['roots'],d['new']) == d['events']


@pytest.mark.parametrize('damage',['old-missing','new-missing','temporary','gap','old-rewritten','new-context'])
def test_event_loader_refuses_damaged_evidence_without_healing(event_epoch,damage):
    d = event_epoch
    folder = d['roots']['sync']/X.EVENT_DIRECTORY
    if damage in ('new-missing','gap','new-context'):
        append_test_event(d,'sync_pending',M.ORPHAN_JOB_ID,{'type':'Synthetic','message':'stop'})
    index = 0 if damage in ('old-missing','old-rewritten') else len(d['original_events'])
    target = folder/f'{index:06d}.json'
    if damage in ('old-missing','new-missing'):target.unlink()
    elif damage == 'temporary':(folder/'.interrupted.tmp').write_bytes(b'preserve')
    elif damage == 'gap':target.rename(folder/f'{index+1:06d}.json')
    elif damage == 'old-rewritten':target.write_bytes(target.read_bytes()+b'\n')
    else:
        row = json.loads(target.read_bytes())
        row['execution_context_digest'] = d['old']['execution_context_digest']
        row = W._seal({k:v for k,v in row.items() if k != 'event_digest'},'event_digest')
        for role in ('output','sync'):
            (d['roots'][role]/X.EVENT_DIRECTORY/target.name).write_bytes(X.L._pretty_json_bytes(row))
    before = {str(p):p.read_bytes() for role in ('output','sync')
              for p in (d['roots'][role]/X.EVENT_DIRECTORY).iterdir()}
    with pytest.raises((M.MetadataRefused,R.RelocationRefused,ValueError)):
        X._load_events(d['roots'],d['new'])
    after = {str(p):p.read_bytes() for role in ('output','sync')
             for p in (d['roots'][role]/X.EVENT_DIRECTORY).iterdir()}
    assert before == after


@pytest.mark.parametrize('damage',['duplicate-start','duplicate-sync','sync-without-start','after-failure','early-complete'])
def test_event_loader_refuses_retries_and_invalid_terminal_sequences(event_epoch,damage):
    d = event_epoch
    if damage == 'duplicate-start':
        append_test_event(d,'attempt_started',M.ORPHAN_JOB_ID,{'checkpoint_digest':d['new']['checkpoint_digest']})
    elif damage == 'duplicate-sync':
        row = next(r for r in d['events'] if r['kind'] == 'job_synced')
        append_test_event(d,'job_synced',row['job_id'],row['data'])
    elif damage == 'sync-without-start':
        job = next(j for j in W.new_exp2a_jobs() if j.job_id not in d['completed'])
        append_test_event(d,'job_synced',job.job_id,dict.fromkeys(
            ('execution_digest','source_tree_digest','copy_evidence_digest'),'f'*64))
    elif damage == 'after-failure':
        append_test_event(d,'sync_pending',M.ORPHAN_JOB_ID,{'type':'Synthetic','message':'stop'})
        append_test_event(d,'sync_pending',M.ORPHAN_JOB_ID,{'type':'Synthetic','message':'again'})
    else:append_test_event(d,'complete',None,{'synced_physical_fits':261,'historical_sources_reverified':155})
    with pytest.raises(M.MetadataRefused):X._load_events(d['roots'],d['new'])


def test_event_new_start_cannot_bind_original_checkpoint(event_epoch):
    d = event_epoch
    job = next(j for j in W.new_exp2a_jobs() if j.job_id not in d['completed'])
    with pytest.raises(M.MetadataRefused,match='wrong checkpoint epoch'):
        append_test_event(d,'attempt_started',job.job_id,{'checkpoint_digest':d['old']['checkpoint_digest']})
    assert d['events'] == d['original_events']


def test_event_original_prefix_and_scope_pins(event_history):
    d = event_history
    before = X._validate_event,X._load_events,X._run_one_job
    with d['sources'].installed(),d['preflight'].installed(),d['checkpoints'].installed(),d['readers'].installed():
        with d['event_readers'].installed(),d['reuse'].installed():
            assert X._load_events(d['roots'],d['old']) == d['original_events']
            with pytest.raises(M.MetadataRefused,match='unadmitted context'):
                X._validate_event(d['original_events'][0],index=0,previous=None,context_digest='f'*64)
        assert (X._validate_event,X._load_events,X._run_one_job) == before
        d['event_readers'].old_chain_sha256 = 'f'*64
        with pytest.raises(M.MetadataRefused,match='aggregate or tail'):
            with d['event_readers'].installed():pytest.fail('invalid prefix admitted')
        assert (X._validate_event,X._load_events,X._run_one_job) == before


@pytest.mark.parametrize('mode',['success','failure'])
def test_event_untouched_job_keeps_original_supervisor_route(event_epoch,monkeypatch,mode):
    d = event_epoch
    job = next(j for j in W.new_exp2a_jobs() if j.arm == 'baseline' and j.job_id not in d['completed'])
    calls = []
    fixed_worker = X._fit_worker
    def isolated(callback,*,root,staging_root,job_id,payload,timeout_seconds):
        assert callback is fixed_worker
        assert root == d['roots']['output'] and staging_root == d['roots']['staging']
        assert timeout_seconds == 3600
        assert payload == {'checkpoint_path':str(d['new_path']),
            'checkpoint_sha256':sha256_file(d['new_path']),'expected_git_commit':COMMIT,'job':job.as_record()}
        calls.append(job_id)
        if mode == 'failure':raise RuntimeError('synthetic attempt failure')
        local = root/'jobs'/job_id
        verified = d['store'].persist(local,job,COMMIT,sha(('fresh:'+job_id).encode()))
        atomic_write_json(local/'job_result.json',X._result_record(job,verified,commit=COMMIT,
            checkpoint_digest=d['new']['checkpoint_digest'],binding=None,
            execution_context_digest=d['new']['execution_context_digest']))
        return X.AttemptOutcome(job_id,'c'*32,'success',local,local,0,published=True)
    publish = X.B._publish_job_tree
    def copy_and_register(source,destination):
        publish(source,destination)
        commit,verified = d['store'].entries[source.resolve()]
        d['store'].entries[destination.resolve()] = commit,replace(verified,fit_dir=destination.resolve())
    monkeypatch.setattr(X,'run_isolated_attempt',isolated)
    monkeypatch.setattr(X.B,'_publish_job_tree',copy_and_register)
    arguments = dict(validated=d['validated'],checkpoint_path=d['new_path'],start=d['new'],events=d['events'])
    if mode == 'success':assert X._run_one_job(job,**arguments) == 'executed'
    else:
        with pytest.raises(RuntimeError,match='synthetic attempt failure'):X._run_one_job(job,**arguments)
        with pytest.raises(ValueError,match='no automatic retry'):X._run_one_job(job,**arguments)
    assert calls == [job.job_id]
    assert d['events'][:-2] == d['original_events']
    tail = d['events'][-2:]
    assert [row['kind'] for row in tail] == ['attempt_started','job_synced' if mode == 'success' else 'attempt_failed']
    assert tail[0]['data']['checkpoint_digest'] == d['new']['checkpoint_digest']
    assert all(row['execution_context_digest'] == d['new']['execution_context_digest'] for row in tail)
    assert X._load_events(d['roots'],d['new']) == d['events']


def test_event_reuse_rejects_forged_or_duplicate_history(event_epoch):
    d = event_epoch
    job = d['new_baseline']
    arguments = dict(validated=d['validated'],checkpoint_path=d['new_path'],start=d['new'])
    for mode in ('duplicate','numeric-type'):
        history = copy.deepcopy(d['events'])
        row = next(row for row in history if row['job_id'] == job.job_id)
        if mode == 'duplicate':history.append(row)
        else:row['event_schema_version'] = 1.0
        with pytest.raises(M.MetadataRefused,match='preserved reuse history differs'):
            X._run_one_job(job,events=history,**arguments)


@pytest.fixture
def control_history(relocated_checkpoint,monkeypatch):
    from bu.experiments import week8_exp2a_production as P
    roots,prior_sources,prior_preflight,prior_checkpoints,_,old,active,store = relocated_checkpoint
    root = W.WORKSPACE_ROOT
    original_workspace = P.WORKSPACE_ROOT
    for name,value in tuple(vars(P).items()):
        if name.isupper() and isinstance(value,Path) and value.is_relative_to(original_workspace):
            monkeypatch.setattr(P,name,root/value.relative_to(original_workspace))
    monkeypatch.setattr(P,'WORKSPACE_ROOT',root)
    documents = {d.path:d for d in prior_sources.access._documents}
    def register(path):
        relative = path.relative_to(root).as_posix()
        documents[relative] = R.Document(relative,sha256_file(path))
        return path
    def write(path,value):
        # Assemble a fresh synthetic history before its relocation attestation.
        # Production's immutable publisher remains unchanged and rejects rewrites.
        assert path.is_relative_to(root)
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(X.L._pretty_json_bytes(value))
        return register(path)
    def logical(path):return str(M.OLD_ROOT/path.relative_to(root).as_posix())
    for name,filename in [('plan',W.PLAN_FILE),('ledger',S.SOURCE_LEDGER_FILE)]:
        for destination in (P.PREPARATION_ORIGINAL_ROOT,P.PREPARATION_COPY_ROOT):
            destination.mkdir(parents=True,exist_ok=True)
            path = destination/filename
            path.write_bytes((root/f'{name}.json').read_bytes())
            register(path)
    plan_path = P.PREPARATION_ORIGINAL_ROOT/W.PLAN_FILE
    ledger_path = P.PREPARATION_ORIGINAL_ROOT/S.SOURCE_LEDGER_FILE
    report = json.loads((roots['preflight']/X.PREFLIGHT_FILE).read_bytes())
    report['inputs'] = {name:{'path':logical(path),'sha256':sha256_file(path)}
                        for name,path in [('plan',plan_path),('source_ledger',ledger_path)]}
    report['binding_sha256'] = W._seal({'inputs':report['inputs'],'plan_digest':report['plan_digest'],
                                       'attempt_timeout_seconds':3600.0},'binding_sha256')['binding_sha256']
    for role in ('preflight','sync'):
        canary = write(roots[role]/X.P.SYNC_CANARY_FILE,{'canary_schema_version':1,
            'destination_identity':P.SYNC_DESTINATION_IDENTITY,'plan_sha256':report['binding_sha256']})
    report['sync_receipt']['destination_identity'] = P.SYNC_DESTINATION_IDENTITY
    for row in (report['sync_canary'],report['sync_receipt']):
        row['sha256'],row['size_bytes'] = sha256_file(canary),canary.stat().st_size
    for role in ('preflight','sync'):write(roots[role]/X.PREFLIGHT_FILE,report)
    report_sha = sha256_file(roots['preflight']/X.PREFLIGHT_FILE)
    old = copy.deepcopy(old)
    old['source_ledger']['path'] = logical(ledger_path)
    old['preflight'].update(sha256=report_sha,binding_sha256=report['binding_sha256'])
    context = X._execution_context(old)
    old['execution_context_digest'] = context['execution_context_digest']
    old = W._seal({k:v for k,v in old.items() if k != 'checkpoint_digest'},'checkpoint_digest')
    for role in ('output','sync'):
        write(roots[role]/W.START_DIRECTORY/f'{prior_checkpoints.old_token}.json',old)
        write(roots[role]/W.CONTEXT_FILE,context)
    old_path = roots['output']/W.START_DIRECTORY/f'{prior_checkpoints.old_token}.json'
    # These are synthetic original-shaped receipts, with logical historical paths.
    # No production receipt is edited or created by this fixture.
    def pin(left,right):
        assert left.read_bytes() == right.read_bytes() and not os.path.samefile(left,right)
        return {'path':logical(left),'copy_path':logical(right),'sha256':sha256_file(left),'independent_copy':True}
    phase_pins = {}
    def receipt(phase,payload,status):
        left,right = P._receipt_paths(phase)
        document = W._seal({'week8_exp2a_production_schema_version':2,'phase':phase,
            'purpose':'synthetic original receipt','status':status,
            'receipt_paths':{'original':logical(left),'copy':logical(right)},'payload':payload},'receipt_digest')
        write(left,document)
        write(right,document)
        phase_pins[phase] = sha256_file(left)
        return document
    prepared = receipt('prepare',{'expected_git_commit':COMMIT,
        'route':{'device':'cpu','num_threads':4,'num_interop_threads':4,'gpu_used':False},
        'plan':pin(plan_path,P.PREPARATION_COPY_ROOT/W.PLAN_FILE),
        'source_ledger':pin(ledger_path,P.PREPARATION_COPY_ROOT/S.SOURCE_LEDGER_FILE),
        'plan_digest':report['plan_digest'],'fixed_paths':{k:logical(v) for k,v in P._fixed_roots().items()},
        'execution_authorized':False},'complete')
    preflight = receipt('preflight',{'expected_git_commit':COMMIT,'prepare_receipt_sha256':phase_pins['prepare'],
        'preflight':pin(roots['preflight']/X.PREFLIGHT_FILE,roots['sync']/X.PREFLIGHT_FILE),
        'roots':{k:logical(v) for k,v in roots.items()},'attempt_timeout_seconds':3600.0,
        'minimum_free_bytes':8_589_934_592,'sync_destination_identity':P.SYNC_DESTINATION_IDENTITY,
        'shared_lease':{'root':logical(W.COMMON_LEASE_ROOT),'name':W.COMMON_LEASE_NAME}},'ready')
    payload = {'expected_git_commit':COMMIT,'preflight_receipt_sha256':phase_pins['preflight'],
        'preflight':preflight['payload']['preflight'],'plan_digest':report['plan_digest'],
        'source_ledger':prepared['payload']['source_ledger'],
        'shared_lease':{'root':logical(W.COMMON_LEASE_ROOT),'name':W.COMMON_LEASE_NAME},
        'roots':{k:logical(roots[k]) for k in ('output','staging','sync')},
        'attempt_timeout_seconds':3600.0,'expected_physical_fits':261,'expected_member_models':441,
        'automatic_retry_allowed':False,'scientific_files_permitted_for_monitor':False}
    for key,directory,rule in [('checkpoint_identity',W.START_DIRECTORY,'single_32hex_lease_token_json'),
        ('event_identity',X.EVENT_DIRECTORY,'contiguous_six_digit_json'),
        ('launch_report_identity',X.REPORT_DIRECTORY,'matching_lease_token_json')]:
        payload[key] = {'local_directory':logical(roots['output']/directory),
                        'copy_directory':logical(roots['sync']/directory),'filename_rule':rule}
    control = receipt('launch-control',payload,'armed_before_blocking_launch')
    job = next(j for j in W.new_exp2a_jobs() if j.arm == 'baseline')
    rows = [sealed_event([],old,'attempt_started',job.job_id,{'checkpoint_digest':old['checkpoint_digest']})]
    rows.append(sealed_event(rows,old,'job_synced',job.job_id,dict.fromkeys(
        ('execution_digest','source_tree_digest','copy_evidence_digest'),'a'*64)))
    rows.append(sealed_event(rows,old,'attempt_started',M.ORPHAN_JOB_ID,{'checkpoint_digest':old['checkpoint_digest']}))
    for row in rows:
        for role in ('output','sync'):write(roots[role]/X.EVENT_DIRECTORY/f"{row['sequence']:06d}.json",row)
    pairs,documents = prior_sources.access._pairs,tuple(documents.values())
    raw = R.build_record(root,pairs,documents)
    access = R.EvidenceAccess(raw,sha(raw),root,pairs,documents)
    sources = M.SourceReaders(access,W,S,ledger_logical_path=logical(ledger_path),ledger_sha256=sha256_file(ledger_path))
    preflight_reader = M.PreflightReaders(access,sources,X,Storage,preflight_sha256=report_sha)
    checkpoints = M.CheckpointReaders(access,preflight_reader,old_sha256=sha256_file(old_path),
        old_checkpoint_digest=old['checkpoint_digest'],old_context_digest=old['execution_context_digest'])
    events = M.EventReaders(access,checkpoints,old_count=3,old_started=2,old_synced=1,
        old_chain_sha256=sha(json.dumps([r['event_digest'] for r in rows],separators=(',',':')).encode('ascii')),
        old_tail_sha256=sha(X.L._pretty_json_bytes(rows[-1])))
    reader = M.ControlReaders(access,P,events,phase_pins=phase_pins)
    store.loads.clear()
    return {'P':P,'root':root,'roots':roots,'access':access,'sources':sources,'preflight':preflight_reader,
            'checkpoints':checkpoints,'events':events,'reader':reader,'old':old,'rows':rows,
            'control':control,'store':store,'phase_pins':phase_pins}


@pytest.fixture
def control_scope(control_history):
    d = control_history
    with d['sources'].installed(),d['preflight'].installed(),d['checkpoints'].installed(),d['events'].installed(),d['reader'].installed():
        yield d


def test_control_monitor_keeps_original_bytes_without_opening_science(control_scope,monkeypatch):
    d = control_scope
    def no_science(*a,**k):pytest.fail('outcome-blind control opened scientific/environment validation')
    monkeypatch.setattr(X.F,'load_fit_evidence',no_science)
    monkeypatch.setattr(X,'_environment',no_science)
    before = {file.path:(d['root']/file.path).read_bytes() for file in d['access']._documents}
    control = d['P']._load_control(COMMIT,monitor_only=True)
    assert control == {**d['control'],'_file_sha256':d['phase_pins']['launch-control']}
    checkpoint,digest = d['P']._checkpoint_material(control)
    assert checkpoint == d['old'] and digest == d['checkpoints'].old_sha256
    assert d['P']._events_material(control,checkpoint) == (d['rows'],[])
    assert not d['store'].loads
    assert all((d['root']/path).read_bytes() == raw for path,raw in before.items())


def test_control_full_branch_reopens_all_original_source_pairs(control_scope):
    d = control_scope
    assert d['P']._load_control(COMMIT)['payload'] == d['control']['payload']
    assert len(d['store'].loads) == 310


def test_control_new_receipts_keep_original_current_path_reader(control_scope):
    d = control_scope
    P = d['P']
    expected = P._publish_receipt('launch',status='synthetic',purpose='current-path reader test',payload={})
    actual = P._load_receipt('launch')
    assert actual == expected
    assert actual['receipt_paths'] == dict(zip(('original','copy'),map(str,P._receipt_paths('launch'))))


@pytest.mark.parametrize('damage',['receipt-missing','receipt-rewritten','extra-checkpoint','event-tmp','event-missing','context-rewritten'])
def test_control_monitor_refuses_changed_or_partial_metadata(control_scope,damage):
    d = control_scope
    P = d['P']
    if damage.startswith('receipt'):
        target = P._receipt_paths('launch-control')[1]
        if damage == 'receipt-missing':target.unlink()
        else:target.write_bytes(target.read_bytes()+b'\n')
    elif damage == 'extra-checkpoint':
        (d['roots']['output']/W.START_DIRECTORY/('f'*32+'.json')).write_bytes(b'{}')
    elif damage == 'event-tmp':(d['roots']['output']/X.EVENT_DIRECTORY/'.interrupted.tmp').write_bytes(b'keep')
    elif damage == 'event-missing':(d['roots']['sync']/X.EVENT_DIRECTORY/'000001.json').unlink()
    else:
        target = d['roots']['output']/W.CONTEXT_FILE
        target.write_bytes(target.read_bytes()+b'\n')
    with pytest.raises((M.MetadataRefused,R.RelocationRefused,ValueError)):
        control = P._load_control(COMMIT,monitor_only=True)
        checkpoint,_ = P._checkpoint_material(control)
        P._events_material(control,checkpoint)


def test_control_scope_preserves_original_layout_checks_and_restores(control_history,monkeypatch):
    d = control_history
    P = d['P']
    original = {k:getattr(P,k) for k in d['reader']._bindings}
    layout = P._validate_fixed_layout
    with d['sources'].installed(),d['preflight'].installed(),d['checkpoints'].installed(),d['events'].installed():
        with d['reader'].installed():
            assert P._validate_fixed_layout is layout
            with pytest.raises(M.MetadataRefused,match='requested control commit differs'):
                P._load_control('f'*40,monitor_only=True)
            with monkeypatch.context() as patch:
                patch.setattr(P,'OUTPUT_ROOT',d['root']/'wrong-output')
                with pytest.raises(ValueError,match='root names drifted'):
                    P._load_control(COMMIT,monitor_only=True)
        assert all(getattr(P,k) is value for k,value in original.items())


def test_released_inventory_keeps_current_paths_and_original_provenance(completed_epoch,monkeypatch):
    d = completed_epoch
    new_job,path,_ = persist_new_repair(d)
    copy_synthetic_fit(d['store'],path.parent,d['roots']['sync']/'jobs'/new_job.job_id)
    copy_synthetic_fit(d['store'],d['roots']['output']/'jobs'/M.ORPHAN_JOB_ID,
                       d['roots']['sync']/'jobs'/M.ORPHAN_JOB_ID)
    d['lease'].release()
    reader = M.ReleasedInventoryReader(d['access'],d['readers'])
    def no_training(*a,**k):pytest.fail('released inventory tried to train')
    monkeypatch.setattr(X.F,'run_confirmatory_fit',no_training)
    with reader.installed():
        inventory = X.load_released_exp2a_source_inventory(checkpoint_path=d['new_path'],
            checkpoint_sha256=sha256_file(d['new_path']),expected_execution_commit=COMMIT)
    rows = {r['job']['job_id']:r for r in inventory['sources']}
    provenance = {r['job_id']:r['origin'] for r in inventory['source_provenance']}
    assert inventory['ledger'] == d['ledger']
    assert inventory['relocation'] == d['checkpoints'].relocation_binding()
    assert len(rows) == 155+len(d['completed'])+1
    assert set(rows) == set(provenance)
    assert set(rows).isdisjoint(inventory['pending_new_fit_ids'])
    assert set(rows) | set(inventory['pending_new_fit_ids']) == {j.job_id for j in W.registered_exp2a_jobs()}
    for old in d['ledger']['sources']:
        job_id = old['job']['job_id']
        assert Path(rows[job_id]['source_path']).exists() and Path(rows[job_id]['copy_path']).exists()
        assert rows[job_id]['copy_evidence_digest'] != old['copy_evidence_digest']
        assert provenance[job_id] == {'kind':'historical_source_ledger',
            'ledger_sha256':d['sources'].ledger_sha256,'source':old}
    assert provenance[d['new_baseline'].job_id]['kind'] == 'preserved_epoch001_pair'
    assert provenance[M.ORPHAN_JOB_ID]['kind'] == 'preserved_epoch001_orphan_new_copy'
    assert 'source' not in provenance[M.ORPHAN_JOB_ID]
    assert provenance[new_job.job_id]['kind'] == 'relocated_epoch_fit'
    assert provenance[new_job.job_id]['checkpoint_digest'] == d['new']['checkpoint_digest']


def test_released_inventory_refuses_an_active_lease(completed_epoch):
    d = completed_epoch
    reader = M.ReleasedInventoryReader(d['access'],d['readers'])
    original = X.load_released_exp2a_source_inventory
    with reader.installed():
        with pytest.raises(ValueError,match='no active shared lease'):
            X.load_released_exp2a_source_inventory(checkpoint_path=d['new_path'],
                checkpoint_sha256=sha256_file(d['new_path']),expected_execution_commit=COMMIT)
    assert X.load_released_exp2a_source_inventory is original


def test_released_inventory_refuses_unpaired_orphan_without_healing(completed_epoch):
    d = completed_epoch
    d['lease'].release()
    reader = M.ReleasedInventoryReader(d['access'],d['readers'])
    remote = d['roots']['sync']/'jobs'/M.ORPHAN_JOB_ID
    with reader.installed():
        with pytest.raises(ValueError,match='partial local/durable'):
            X.load_released_exp2a_source_inventory(checkpoint_path=d['new_path'],
                checkpoint_sha256=sha256_file(d['new_path']),expected_execution_commit=COMMIT)
    assert not remote.exists()


@pytest.mark.parametrize('fail',[False,True])
def test_inspector_wires_real_metadata_scopes_and_restores(control_history,monkeypatch,fail):
    from contextlib import contextmanager
    from types import SimpleNamespace
    inspector_spec = importlib.util.spec_from_file_location('relocation_inspector_scope_test',
        ROOT/'scripts/week8_exp2a_recovery_inspector.py')
    inspector = importlib.util.module_from_spec(inspector_spec)
    inspector_spec.loader.exec_module(inspector)
    d = control_history
    raw = {'synthetic':True}
    gate = {'raw_authority':raw,'record_digest':'f'*64}
    phases = []
    @contextmanager
    def git_scope(value,*,allow_imports):
        assert value is raw and allow_imports is True
        phases.append('git-enter')
        try:yield
        finally:phases.append('git-exit')
    completed = M.CompletedJobReaders(d['access'],d['checkpoints'])
    # Admission/Git mechanisms have separate adversarial tests. Here the real
    # relocated synthetic readers prove the actor's installation/restoration.
    metadata = SimpleNamespace(load_registered_access=lambda verifier:d['access'],
        verified_historical_git_state=git_scope,
        SourceReaders=lambda *a:d['sources'],PreflightReaders=lambda *a:d['preflight'],
        CheckpointReaders=lambda *a:d['checkpoints'],CompletedJobReaders=lambda *a:completed,
        EventReaders=lambda *a:d['events'],ControlReaders=lambda *a:d['reader'],
        POLICY_SHA256='a'*64,EXPECTED_PAIR_COUNT=len(d['access']._pairs),
        EXPECTED_DOCUMENT_COUNT=len(d['access']._documents))
    helper_binding = {'helper_schema_version':1,'synthetic':True}
    validations = []
    def validate(value):
        assert value is raw
        validations.append('validated')
        return helper_binding
    bundle = SimpleNamespace(modules={'metadata':metadata,'provenance':object()},validate=validate)
    monkeypatch.setattr(inspector,'_validate_entrypoint_authority',lambda:gate)
    monkeypatch.setattr(inspector,'_validate_execution_source',lambda value:None)
    monkeypatch.setattr(inspector,'_install_old_source',lambda value:(object(),object()))
    monkeypatch.setattr(inspector,'_load_bound_raw_authority',lambda:SimpleNamespace(
        load_verified_relocation_helpers=lambda value:bundle))
    monkeypatch.setattr(inspector,'_verify_loaded_bu_modules',lambda *a:[])
    before = X._read_start,X._baseline,X._load_events,d['P']._load_control
    def material(value,finder,dependency_finder,access):
        assert access is d['access'] and phases == ['git-enter']
        assert X._read_start == d['checkpoints'].read_start
        assert X._baseline == completed.baseline
        control = d['P']._load_control(COMMIT,monitor_only=True)
        checkpoint,_ = d['P']._checkpoint_material(control)
        assert d['P']._events_material(control,checkpoint) == (d['rows'],[])
        if fail:raise ValueError('synthetic material refusal')
        return {'inspector_schema_version':2,'status':'complete','loaded_bu_modules':[]}
    monkeypatch.setattr(inspector,'_run_material',material)
    if fail:
        with pytest.raises(ValueError,match='synthetic material refusal'):inspector._run()
    else:
        result = inspector._run()
        assert result['relocation'] == {'relocation_schema_version':1,
            'attestation_sha256':d['access'].attestation_sha256,'policy_sha256':'a'*64,
            'pair_count':len(d['access']._pairs),'document_count':len(d['access']._documents),
            'helpers':helper_binding}
        assert len(validations) == 2
        assert result['inspector_digest'] == inspector._sha_bytes(inspector._canonical(
            {key:value for key,value in result.items() if key != 'inspector_digest'}))
    assert phases == ['git-enter','git-exit']
    assert (X._read_start,X._baseline,X._load_events,d['P']._load_control) == before


@pytest.mark.parametrize('fail',[False,True])
def test_worker_wires_frozen_readers_and_restores(event_history,monkeypatch,fail):
    from types import SimpleNamespace
    spec = importlib.util.spec_from_file_location('relocation_worker_scope_test',
        ROOT/'scripts/week8_exp2a_recovery_worker.py')
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    d = event_history
    metadata = SimpleNamespace(SourceReaders=lambda *a:d['sources'],
        PreflightReaders=lambda *a:d['preflight'],CheckpointReaders=lambda *a:d['checkpoints'],
        CompletedJobReaders=lambda *a:d['readers'],EventReaders=lambda *a:d['event_readers'],
        ReuseReader=lambda *a:d['reuse'])
    validations = []
    def admitted():
        validations.append(True)
        return metadata,d['access'],{'synthetic':'binding'}
    monkeypatch.setattr(worker,'_admitted_relocation',admitted)
    before = X._read_start,X._baseline,X._load_events,X._run_one_job
    def run():
        with worker._worker_relocation_readers(X):
            assert X._baseline == d['readers'].baseline
            assert X._run_one_job == d['reuse'].run_one
            start,ledger,roots = X._load_start(d['old_path'],
                expected_sha256=d['checkpoints'].old_sha256,expected_git_commit=COMMIT)
            assert start == d['old'] and roots == {k:d['roots'][k] for k in ('output','staging','sync')}
            assert ledger == d['ledger']
            row = d['original_events'][0]
            X._validate_event(row,index=0,previous=None,context_digest=d['old']['execution_context_digest'])
            if fail:raise ValueError('synthetic lower refusal')
    if fail:
        with pytest.raises(ValueError,match='synthetic lower refusal'):run()
    else:run()
    assert len(validations) == 2
    assert (X._read_start,X._baseline,X._load_events,X._run_one_job) == before


def orphan_transition_fixture(access, root, original):
    """Synthetic transition authorization; full worker-chain validation is separate."""
    lease = original.document()
    active = root/'week7-production-control/leases/week7-production.lease.json'
    archive = active.parent/'history'/f'week7-production.{M.OLD_LEASE_TOKEN}.orphaned-after-liveness-proof.json'
    archive.parent.mkdir(parents=True,exist_ok=True)
    archive.write_bytes(original.raw)
    paths = tuple(root/folder/'transition-completion.json' for folder in (
        'week8-exp2a-recovery-2026-09-02-attempt-001',
        'week8-exp2a-recovery-2026-09-02-attempt-001-project-evidence'))
    old = {'path':str(active.resolve()),'sha256':original.sha256,'pid':lease['pid'],
           'token':lease['token'],'timestamp':lease['timestamp'],'timestamp_utc':lease['timestamp_utc']}
    payload = {'recovery_schema_version':3,'recovery_id':'week8-exp2a-d161-2026-09-02-attempt-001',
        'decision_id':'D-161','record_type':'transition_completion','scientific_outcomes_consulted':False,
        'scientific_values_emitted':False,'status':'ownership_transition_complete',
        'authorization':{'old_lease':old,'automatic_retry_allowed':False},
        'transition_intent':{'record_digest':'1'*64,'file_sha256':'2'*64},
        'orphan_lease_archive':{'path':str(archive.resolve()),'sha256':original.sha256,
                              'classification':'orphaned_after_liveness_proof'},'quarantine':{'synthetic':True}}
    canonical = lambda value:json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
    document = {**payload,'record_digest':sha(canonical(payload))}
    raw = canonical(document)+b'\n'
    for path in paths:
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(raw)
    binding = {'record_digest':document['record_digest'],'file_sha256':sha(raw)}
    reader = M.OrphanLeaseReader(access,X,binding,workspace=root,old_pid=lease['pid'],old_lease_sha256=original.sha256)
    return {'access':access,'reader':reader,'active':active,'archive':archive,'transition_paths':paths,
            'transition':document,'binding':binding,'original':original,'root':root,'canonical':canonical}


@pytest.fixture
def orphan_history(tmp_path,monkeypatch):
    monkeypatch.setattr(W,'WORKSPACE_ROOT',tmp_path)
    monkeypatch.setattr(W,'COMMON_LEASE_ROOT',tmp_path/'week7-production-control')
    lease_path = tmp_path/'project 2(ongoing)/week7-production-control/leases/week7-production.lease.json'
    lease = {'schema_version':2,'lease_name':'week7-production','pid':48960,'token':M.OLD_LEASE_TOKEN,
             'timestamp':1.0,'timestamp_utc':'2026-09-01T00:00:00Z'}
    atomic_write_json(lease_path,lease)
    for name in ('source','copy'):
        path = tmp_path/name
        path.mkdir()
        (path/'file.bin').write_bytes(b'synthetic')
    content = R.digest([{'path':'file.bin','size':9,'sha256':sha(b'synthetic')}])
    pair = R.Pair('test-pair',str(M.OLD_ROOT/'source/job'),str(M.OLD_ROOT/'copy/job'),
                  'source','copy',content,'1'*64)
    docs = (R.Document(lease_path.relative_to(tmp_path).as_posix(),sha256_file(lease_path)),)
    raw = R.build_record(tmp_path,(pair,),docs)
    access = R.EvidenceAccess(raw,sha(raw),tmp_path,(pair,),docs)
    original = access.historical_file(str(M.OLD_ROOT/'week7-production-control/leases/week7-production.lease.json'))
    return orphan_transition_fixture(access,tmp_path,original)


@pytest.mark.parametrize('active',[False,True])
def test_orphan_history_requires_authorized_twins_and_original_bytes(orphan_history,active):
    d = orphan_history
    original_lookup = X._historical_lease_record
    if active:
        lease = {**d['original'].document(),'pid':os.getpid(),'token':'d'*32}
        atomic_write_json(d['active'],lease)
    before = tuple(p.read_bytes() for p in (*d['transition_paths'],d['archive']))
    with d['reader'].installed():
        row = X._historical_lease_record(M.OLD_LEASE_TOKEN)
        assert row == {'path':str(d['active'].resolve()),'sha256':d['original'].sha256,
            'name':'week7-production','token':M.OLD_LEASE_TOKEN,'started_at':'2026-09-01T00:00:00Z'}
    assert X._historical_lease_record is original_lookup
    assert tuple(p.read_bytes() for p in (*d['transition_paths'],d['archive'])) == before


@pytest.mark.parametrize('mutation',['missing_twin','changed_twin','linked_twins','archive','normal_release',
    'active_old','active_schema','active_pid','binding','status','classification','archive_path','lease_pid','lease_digest'])
def test_orphan_history_refuses_altered_proof(orphan_history,mutation):
    d = orphan_history
    if mutation == 'missing_twin':d['transition_paths'][1].unlink()
    elif mutation == 'changed_twin':d['transition_paths'][1].write_bytes(b'changed')
    elif mutation == 'linked_twins':
        d['transition_paths'][1].unlink()
        os.link(*d['transition_paths'])
    elif mutation == 'archive':d['archive'].write_bytes(b'changed')
    elif mutation == 'normal_release':d['reader'].normal.write_bytes(b'forbidden')
    elif mutation.startswith('active_'):
        lease = {**d['original'].document(),'pid':os.getpid(),'token':'d'*32}
        if mutation == 'active_old':lease['token'] = M.OLD_LEASE_TOKEN
        if mutation == 'active_schema':lease['schema_version'] = True
        if mutation == 'active_pid':lease['pid'] = True
        atomic_write_json(d['active'],lease)
    elif mutation == 'binding':d['reader'].binding['file_sha256'] = 'f'*64
    else:
        document = d['transition']
        if mutation == 'status':document['status'] = 'ownership_transition_intended'
        if mutation == 'classification':document['orphan_lease_archive']['classification'] = 'released'
        if mutation == 'archive_path':document['orphan_lease_archive']['path'] = str(d['archive'].parent/'other.json')
        if mutation == 'lease_pid':document['authorization']['old_lease']['pid'] = True
        if mutation == 'lease_digest':document['authorization']['old_lease']['sha256'] = 'f'*64
        document['record_digest'] = sha(d['canonical']({k:v for k,v in document.items() if k != 'record_digest'}))
        raw = d['canonical'](document)+b'\n'
        for path in d['transition_paths']:path.write_bytes(raw)
        d['reader'].binding = {'file_sha256':sha(raw),'record_digest':document['record_digest']}
    original = X._historical_lease_record
    with d['reader'].installed():
        with pytest.raises((ValueError,OSError)):
            X._historical_lease_record(M.OLD_LEASE_TOKEN)
    assert X._historical_lease_record is original


def test_orphan_history_detects_same_byte_archive_exchange_during_lookup(orphan_history,monkeypatch):
    d = orphan_history
    original = d['reader']._transition
    called = False
    def exchange(lease):
        nonlocal called
        value = original(lease)
        if not called:
            called = True
            raw = d['archive'].read_bytes()
            d['archive'].rename(d['archive'].with_suffix('.previous'))
            d['archive'].write_bytes(raw)
        return value
    monkeypatch.setattr(d['reader'],'_transition',exchange)
    with d['reader'].installed():
        with pytest.raises(ValueError,match='changed during lookup'):
            X._historical_lease_record(M.OLD_LEASE_TOKEN)


def test_orphan_history_delegates_other_tokens_and_restores_after_tampering(orphan_history,monkeypatch):
    d = orphan_history
    calls = []
    original = lambda token:calls.append(token) or {'ordinary':token}
    monkeypatch.setattr(X,'_historical_lease_record',original)
    reader = M.OrphanLeaseReader(d['access'],X,d['binding'],workspace=d['root'],
        old_pid=48960,old_lease_sha256=d['original'].sha256)
    with pytest.raises(ValueError,match='failed restoration'):
        with reader.installed():
            assert X._historical_lease_record('d'*32) == {'ordinary':'d'*32}
            with pytest.raises(ValueError,match='before installation'):
                with reader.installed():pytest.fail('nested history scope admitted')
            X._historical_lease_record = lambda token:None
    assert calls == ['d'*32] and X._historical_lease_record is original


@pytest.mark.parametrize('failure',[None,'body','binding','helper'])
def test_fit_child_wires_real_metadata_and_orphan_scopes(control_history,monkeypatch,failure):
    from types import SimpleNamespace,ModuleType
    spec = importlib.util.spec_from_file_location('relocation_fit_child_scope_test',
        ROOT/'scripts/week8_exp2a_recovery_fit_child.py')
    child = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(child)
    d = control_history
    original = d['access'].historical_file(str(M.OLD_ROOT/'week7-production-control/leases/week7-production.lease.json'))
    history = orphan_transition_fixture(d['access'],d['root'],original)
    history['active'].unlink()  # synthetic transition; the archive retains the bytes
    raw,changed = {'synthetic':True},False
    raw_module = ModuleType(child.RAW_AUTHORITY_MODULE_NAME)
    completed = M.CompletedJobReaders(d['access'],d['checkpoints'])
    metadata = SimpleNamespace(load_registered_access=lambda verifier:d['access'],
        SourceReaders=lambda *a:d['sources'],PreflightReaders=lambda *a:d['preflight'],
        CheckpointReaders=lambda *a:d['checkpoints'],CompletedJobReaders=lambda *a:completed,
        OrphanLeaseReader=lambda *a:history['reader'],OLD_LEASE_TOKEN=M.OLD_LEASE_TOKEN,
        POLICY_SHA256='a'*64,EXPECTED_PAIR_COUNT=len(d['access']._pairs),
        EXPECTED_DOCUMENT_COUNT=len(d['access']._documents))
    validations = []
    def validate(value):
        assert value is raw
        validations.append(True)
        return {'helper_schema_version':1,'synthetic_changed':changed}
    bundle = SimpleNamespace(modules={'metadata':metadata,'provenance':object()},validate=validate)
    loads = []
    def load(value):
        assert value is raw
        loads.append(True)
        return bundle
    raw_module.load_verified_relocation_helpers = load
    monkeypatch.setitem(sys.modules,child.RAW_AUTHORITY_MODULE_NAME,raw_module)
    binding = {'relocation_schema_version':1,'attestation_sha256':d['access'].attestation_sha256,
        'policy_sha256':'a'*64,'pair_count':len(d['access']._pairs),'document_count':len(d['access']._documents),
        'helpers':{'helper_schema_version':1,'synthetic_changed':False}}
    invocation = {'relocation':binding,'orphan_transition':history['binding']}
    before = X._historical_lease_record,X._read_start,X._baseline
    if failure == 'binding':binding['policy_sha256'] = 'f'*64
    def run():
        nonlocal changed
        with child._fit_relocation_scope(raw_module,raw,invocation,X._fit_worker):
            assert X._historical_lease_record == history['reader'].lookup
            assert X._baseline == completed.baseline
            path = d['roots']['output']/W.START_DIRECTORY/f'{M.OLD_LEASE_TOKEN}.json'
            start,ledger,roots = X._read_start(path,expected_sha256=d['checkpoints'].old_sha256,
                expected_git_commit=COMMIT,released=True)
            assert start == d['old'] and len(ledger['sources']) == 155
            if failure == 'body':raise ValueError('synthetic fit refusal')
            if failure == 'helper':changed = True
    if failure is None:run()
    else:
        with pytest.raises(ValueError,match={'body':'synthetic fit refusal','binding':'admission differs','helper':'authority changed'}[failure]):run()
    assert (X._historical_lease_record,X._read_start,X._baseline) == before
    assert loads == [True]
    assert len(validations) == (1 if failure == 'binding' else 2)
