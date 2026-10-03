"""Verified historical Git scope for the captured relocation helper."""
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('relocation_git_under_test',ROOT/'scripts/week8_relocation_metadata.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


@pytest.fixture
def git_modules(tmp_path,monkeypatch):
    root = tmp_path/'execution'
    source = root/'src/bu/runrecord.py'
    source.parent.mkdir(parents=True)
    source.write_text('''class GitState:
    def __init__(self,commit,dirty,branch):
        self.commit,self.dirty,self.branch = commit,dirty,branch
def git_state(repo=None):
    raise AssertionError('bare Git must not execute')
''',encoding='utf-8')
    runrecord = ModuleType('bu.runrecord')
    exec(compile(source.read_bytes(),str(source),'exec'),runrecord.__dict__)
    runrecord.PROJECT_ROOT = root
    runrecord.__spec__ = SimpleNamespace(loader=SimpleNamespace(
        binding_marker='week8_d161_verified_source_v2',tree_kind='execution'))
    original = runrecord.git_state
    modules = {'bu.runrecord':runrecord}
    for name in ('bu.experiments.confirmatory','bu.experiments.fit_evidence','bu.experiments.preflight'):
        module = ModuleType(name)
        module.git_state = original
        modules[name] = module
    for name,module in modules.items():monkeypatch.setitem(sys.modules,name,module)
    monkeypatch.setattr(M,'EXECUTION_WORKTREE',root)
    monkeypatch.setattr(M,'EXECUTION_SOURCE',root/'src')
    raw = {'execution':{'path':str(root),'git_commit':M.EXECUTION_COMMIT,'branch':'HEAD','detached':True,
                        'worktree_inventory_digest':'a'*64,'stability_observations':2}}
    return root,raw,modules,original


def test_relocation_git_uses_authority_and_restores_all_aliases(git_modules,tmp_path):
    root,raw,modules,original = git_modules
    with M.verified_historical_git_state(raw) as adapter:
        assert all(module.git_state is adapter for module in modules.values())
        state = modules['bu.experiments.preflight'].git_state(root)
        assert (state.commit,state.dirty,state.branch) == (M.EXECUTION_COMMIT,False,'HEAD')
        with pytest.raises(M.MetadataRefused,match='another repository'):adapter(tmp_path)
    assert all(module.git_state is original for module in modules.values())


def test_relocation_git_covers_new_import_alias_and_restores(git_modules,monkeypatch):
    _,raw,modules,original = git_modules
    with M.verified_historical_git_state(raw,allow_imports=True) as adapter:
        late = ModuleType('bu.synthetic_late')
        late.git_state = adapter
        monkeypatch.setitem(sys.modules,late.__name__,late)
        assert late.git_state().commit == M.EXECUTION_COMMIT
    assert late.git_state is original
    assert all(module.git_state is original for module in modules.values())


@pytest.mark.parametrize('damage',['alias','state-type','authority'])
def test_relocation_git_refuses_mutation_and_restores(git_modules,monkeypatch,damage):
    _,raw,modules,original = git_modules
    with pytest.raises(M.MetadataRefused):
        with M.verified_historical_git_state(raw) as adapter:
            if damage == 'alias':modules['bu.experiments.preflight'].git_state = lambda:None
            elif damage == 'state-type':monkeypatch.setattr(modules['bu.runrecord'],'GitState',type('Fake',(),{}))
            else:raw['execution']['git_commit'] = 'f'*40
            adapter()
    assert all(module.git_state is original for module in modules.values())


@pytest.mark.parametrize('damage',['loader','dirty-identity','path','observations'])
def test_relocation_git_refuses_wrong_initial_authority(git_modules,damage):
    _,raw,modules,original = git_modules
    if damage == 'loader':modules['bu.runrecord'].__spec__.loader.tree_kind = 'controller'
    elif damage == 'dirty-identity':raw['execution']['detached'] = False
    elif damage == 'path':raw['execution']['path'] += '/wrong'
    else:raw['execution']['stability_observations'] = 1
    with pytest.raises(M.MetadataRefused):
        with M.verified_historical_git_state(raw):pytest.fail('wrong authority admitted')
    assert all(module.git_state is original for module in modules.values())
