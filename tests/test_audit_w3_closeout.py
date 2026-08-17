"""Week 3 closeout: the two defects Sol found in the audit's own fixes (D-062).

Both are cases where a fix addressed the symptom and left the mechanism intact,
which is the failure mode D-055 and D-057 already have entries for. The tests
here are therefore written against the **mechanism**, not against the state the
mechanism happens to leave behind:

* the MC-dropout test uses a model that actually contains a dropout layer and
  asserts that repeated predictions **differ**. Asserting on ``model.training``
  is what the previous test did, and it passed while dropout was disabled;
* the rerun test executes the pilot **twice** and inspects what is on disk,
  rather than asserting that a guard function exists.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import torch
import torch.nn as nn

from bu.config import Config, TrainConfig, UnitSpec
from bu.env.collect import collect_pools
from bu.experiments import w3_pilot
from bu.metrics import RunLogger
from bu.models.ensemble import (
    dropout_modules, forkable_devices, mc_dropout_predictions, prediction_mode,
    train_ensemble,
)
from bu.models.uncertainty import NormalisationScale, pairwise_disagreement
from bu.models.world_model import WorldModel
from bu.streams import stream

SEED = 3
ROOT = Path(__file__).resolve().parents[1]


class DropoutProbe(nn.Module):
    """A model with real dropout, mirroring WorldModel's two-head signature.

    Deliberately a separate class. The point of the test is to exercise the
    prediction policy against an architecture where dropout is live, and
    WorldModel has none -- which is exactly why the defect was invisible.
    """

    def __init__(self, p: float = 0.5) -> None:
        super().__init__()
        self.trunk = nn.Linear(4, 16)
        self.dropout = nn.Dropout(p)
        self.position_head = nn.Linear(16, 2)
        self.activation_head = nn.Linear(16, 1)

    def forward(self, obs: torch.Tensor, action: torch.Tensor):
        h = self.dropout(torch.relu(self.trunk(obs)))
        return self.position_head(h), self.activation_head(h.detach())


@pytest.fixture
def probe() -> DropoutProbe:
    torch.manual_seed(0)
    return DropoutProbe()


@pytest.fixture
def probe_batch() -> tuple[torch.Tensor, torch.Tensor]:
    torch.manual_seed(1)
    return torch.randn(32, 4), torch.zeros(32, dtype=torch.long)


# --- W3-4, reopened: the fix restored state without fixing the mechanism ---


def test_mc_dropout_predictions_actually_vary(probe, probe_batch):
    """THE test. Under P§9.3's fallback B2 the samples must differ.

    The previous fix saved and restored ``model.training`` but still called
    ``eval()`` before the forward pass, so dropout was disabled while
    predictions were generated: every sample identical, disagreement exactly
    zero, and a rung-3 gate reading "MC-dropout also fails H1" when nothing had
    been measured at all.
    """
    obs, action = probe_batch
    samples = mc_dropout_predictions(probe, obs, action, n_samples=8, seed=0)

    assert samples.shape == (8, 32, 2)
    spread = samples.std(dim=0).mean()
    assert float(spread) > 1e-3, (
        f"MC-dropout samples are identical (spread {float(spread):.2e}); dropout "
        "was not active during inference"
    )
    # And the quantity the gate actually reads is non-zero, which is the claim
    # that matters rather than the tensor being merely unequal.
    assert float(pairwise_disagreement(samples).mean()) > 1e-3


def test_deterministic_predictions_do_not_vary(probe, probe_batch):
    """The other half of the policy: the registered estimator is deterministic.

    Without this, "predictions vary" could be satisfied by a model that is
    stochastic in *both* modes, which would break H1's estimator instead.
    """
    obs, action = probe_batch
    with prediction_mode(probe, "deterministic"):
        with torch.no_grad():
            first, _ = probe(obs, action)
            second, _ = probe(obs, action)
    assert torch.equal(first, second)
    assert float(pairwise_disagreement(torch.stack([first, second])).mean()) == 0.0


def test_mc_dropout_keeps_dropout_active_but_nothing_else(probe):
    """Test-time dropout is not the same thing as ``model.train()``.

    Calling ``train()`` would also switch batch-norm to batch statistics, which
    is a different estimator from the one P§9.3 names.
    """
    with prediction_mode(probe, "mc_dropout"):
        assert probe.dropout.training, "dropout inactive under mc_dropout"
        assert not probe.trunk.training, "mc_dropout switched more than dropout"
    with prediction_mode(probe, "deterministic"):
        assert not probe.dropout.training


@pytest.mark.parametrize("mode", ["deterministic", "mc_dropout"])
@pytest.mark.parametrize("before", [True, False])
def test_every_submodule_mode_is_restored(probe, probe_batch, mode, before):
    """Restored per submodule, since the policy changes them independently.

    ``model.train(was_training)`` would restore the top-level flag while leaving
    a mixed model behind it.
    """
    probe.train(before)
    expected = {name: m.training for name, m in probe.named_modules()}
    with prediction_mode(probe, mode):
        pass
    assert {name: m.training for name, m in probe.named_modules()} == expected


def test_mc_dropout_on_a_dropout_free_model_raises(probe_batch):
    """Fail closed. Silence here is the whole defect.

    A model with no dropout returns identical samples and zero disagreement,
    which is indistinguishable from a genuine negative at the reliability gate.
    The current WorldModel has no dropout, so rung 3 must be an explicit
    architectural change and is told so rather than quietly producing a number.
    """
    unit = UnitSpec(hidden_size=16, n_transitions=100)
    model = WorldModel(unit, stream(unit, "exp1", "init", SEED))
    assert dropout_modules(model) == []

    obs = torch.zeros(4, model.encoder.size)
    action = torch.zeros(4, dtype=torch.long)
    with pytest.raises(ValueError, match="no dropout layers"):
        mc_dropout_predictions(model, obs, action, n_samples=4)
    with pytest.raises(ValueError, match="no dropout layers"):
        with prediction_mode(model, "mc_dropout"):
            pass


def test_the_ensemble_prediction_mode_reaches_the_members():
    """The policy is selectable where the gate would select it."""
    unit = UnitSpec(hidden_size=16, n_transitions=500)
    pools = collect_pools(unit, stage="exp1", seed=SEED)
    ensemble = train_ensemble(
        unit, pools, TrainConfig(max_epochs=1, ensemble_size=2), stage="exp1", seed=SEED
    )
    obs = torch.as_tensor(pools.evaluation.obs[:8])
    action = torch.as_tensor(pools.evaluation.action[:8])

    for model in ensemble.members:
        model.train()
    first = ensemble.member_predictions(obs, action)
    assert torch.equal(first, ensemble.member_predictions(obs, action))
    assert all(m.training for m in ensemble.members), "members left in eval mode"

    with pytest.raises(ValueError, match="no dropout layers"):
        ensemble.member_predictions(obs, action, mode="mc_dropout")
    with pytest.raises(ValueError, match="unknown prediction mode"):
        ensemble.member_predictions(obs, action, mode="eval")


def test_mc_dropout_does_not_disturb_the_cpu_rng(probe, probe_batch):
    """Sampling forks the RNG rather than advancing it.

    Otherwise selecting rung 3 at the gate would shift every subsequent draw in
    the process, and a fallback estimator would silently change data elsewhere.

    Renamed from "the global RNG" (D-064): on a CPU-only run this *is* the
    global RNG, but the claim was being read as unrestricted, and the CUDA
    generator was not covered at all. The device case is below.
    """
    obs, action = probe_batch
    torch.manual_seed(7)
    before = torch.randn(3)
    torch.manual_seed(7)
    mc_dropout_predictions(probe, obs, action, n_samples=4, seed=0)
    assert torch.equal(before, torch.randn(3))


def test_a_cpu_computation_forks_no_accelerator(probe, probe_batch):
    """The CPU path is unchanged: no device is named, so none is forked."""
    obs, action = probe_batch
    assert forkable_devices(probe, obs, action) == (None, [])


def test_devices_are_derived_from_the_model_and_its_inputs():
    """The list comes from what the computation touches, not from a default.

    Checked without CUDA by using meta tensors, so the derivation itself is
    covered on any machine — the GPU test below is then about the RNG rather
    than about this bookkeeping.
    """
    model = DropoutProbe().to("meta")
    obs = torch.zeros(4, 4, device="meta")
    action = torch.zeros(4, dtype=torch.long, device="meta")
    assert forkable_devices(model, obs, action) == ("meta", [0])

    mixed = DropoutProbe()  # cpu parameters, meta inputs
    assert forkable_devices(mixed, obs, action) == ("meta", [0])


@pytest.mark.skipif(not torch.cuda.is_available(), reason="no CUDA device")
def test_mc_dropout_does_not_disturb_the_cuda_rng():
    """The claim Sol found unsupported (D-064).

    ``fork_rng`` always forks CPU but forks device generators only for the
    devices it is handed, so the previous ``devices=[]`` left the CUDA
    generator advancing. The reliability gate's fallback estimator is precisely
    what would be run on a GPU, and a shifted CUDA generator moves every
    subsequent draw in that process.

    Deliberately tiny: a 32x4 input through a 16-unit layer.
    """
    torch.manual_seed(0)
    model = DropoutProbe().cuda()
    obs = torch.randn(32, 4, device="cuda")
    action = torch.zeros(32, dtype=torch.long, device="cuda")

    assert forkable_devices(model, obs, action) == ("cuda", [0])

    torch.cuda.manual_seed_all(11)
    before_cuda = torch.cuda.get_rng_state()
    before_cpu = torch.get_rng_state()

    samples = mc_dropout_predictions(model, obs, action, n_samples=8, seed=3)

    assert torch.equal(torch.cuda.get_rng_state(), before_cuda), (
        "the CUDA generator advanced; fork_rng was not given the device"
    )
    assert torch.equal(torch.get_rng_state(), before_cpu)
    # And it is still a real MC-dropout sample on the device.
    assert samples.is_cuda
    assert float(samples.std(dim=0).mean()) > 1e-3


def test_mc_dropout_is_reproducible_from_its_seed(probe, probe_batch):
    obs, action = probe_batch
    a = mc_dropout_predictions(probe, obs, action, n_samples=4, seed=11)
    b = mc_dropout_predictions(probe, obs, action, n_samples=4, seed=11)
    c = mc_dropout_predictions(probe, obs, action, n_samples=4, seed=12)
    assert torch.equal(a, b)
    assert not torch.equal(a, c)


# --- W3-2, reopened: rerunning could mix two executions' evidence ----------


def test_the_metric_stream_refuses_to_append_by_default(tmp_path):
    """The mechanism Sol named: append mode with a counter that restarts at 0.

    Measured before the fix: two writes of five records produced ten lines
    numbered 0-4, 0-4, with nothing to distinguish a rerun from a longer run.
    """
    logger = RunLogger(tmp_path, "r"); [logger.log(member=k) for k in range(5)]; logger.close()

    with pytest.raises(FileExistsError, match="Refusing to append"):
        RunLogger(tmp_path, "r")

    resumed = RunLogger(tmp_path, "r", append=True)
    resumed.log(member=5)
    resumed.close()
    lines = [
        json.loads(line)
        for line in (tmp_path / "metrics.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert [r["i"] for r in lines] == [0, 1, 2, 3, 4, 5], (
        "an explicit append restarted the counter instead of continuing it"
    )


def _pilot_files(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def test_a_second_pilot_run_writes_a_separate_attempt(tmp_path):
    """Run the pilot twice at the same output location and look at the disk.

    Sol's closeout condition. Two sizes rather than six so the test is seconds
    rather than minutes; the property is about directories, not about scale, and
    the delivered 18-run attempt is checked against its own manifest below.
    """
    sizes, seeds = (100, 250), (0,)
    kwargs = dict(sizes=sizes, seeds=seeds, hidden_size=16, out_dir=tmp_path, verbose=False)

    first = w3_pilot.run(**kwargs)
    snapshot = _pilot_files(first.attempt_dir)

    second = w3_pilot.run(**kwargs)
    assert second.attempt_dir != first.attempt_dir
    assert second.attempt_dir.name == "attempt-002"

    # Nothing in the first attempt moved: not the metric streams, not rows.json,
    # not the exports, not the figures.
    assert _pilot_files(first.attempt_dir) == snapshot

    for attempt in (first, second):
        records = sorted((attempt.attempt_dir / "records").glob("*/run.json"))
        assert len(records) == len(sizes) * len(seeds)
        for record in records:
            members = [
                json.loads(line)
                for line in (record.parent / "metrics.jsonl").read_text().splitlines()
                if line.strip()
            ]
            assert len(members) == TrainConfig().ensemble_size
            assert [m["i"] for m in members] == list(range(len(members)))
            assert sorted(m["member"] for m in members) == list(range(len(members)))


def test_two_attempts_cannot_be_loaded_as_one_dataset(tmp_path):
    """Attempts share run_ids by construction, so a tree of them double-counts.

    Separating the executions on disk is only half the fix: an analysis pointed
    at the parent directory would load both and silently double every record
    behind every interval.
    """
    from bu.metrics import load_runs

    kwargs = dict(sizes=(100,), seeds=(0,), hidden_size=16, out_dir=tmp_path, verbose=False)
    first = w3_pilot.run(**kwargs)
    w3_pilot.run(**kwargs)

    assert len(load_runs(first.attempt_dir / "records")) == TrainConfig().ensemble_size
    with pytest.raises(RuntimeError, match="appears in two directories"):
        load_runs(tmp_path)


def test_the_manifest_accounts_for_every_artifact(tmp_path):
    """Each artefact carries the provenance needed to verify it (D-062)."""
    attempt = w3_pilot.run(
        sizes=(100,), seeds=(0,), hidden_size=16, out_dir=tmp_path, verbose=False
    )
    manifest = json.loads((attempt.attempt_dir / "manifest.json").read_text())

    assert manifest["manifest_version"] == w3_pilot.MANIFEST_VERSION
    assert manifest["seed_partition"] == "development"
    assert manifest["n_runs"] == 1
    assert manifest["n_member_records"] == TrainConfig().ensemble_size
    assert manifest["commit"] and manifest["packages"]

    on_disk = {p.name for p in attempt.attempt_dir.iterdir() if p.is_file()}
    listed = {a["path"] for a in manifest["artifacts"]}
    assert listed == on_disk - {"manifest.json"}

    for entry in manifest["artifacts"]:
        path = attempt.attempt_dir / entry["path"]
        assert w3_pilot._sha256(path) == entry["sha256"], f"{entry['path']} changed"
        if entry["kind"] == "per_transition_export":
            for key in ("run_id", "config_id", "unit_id", "seed", "n_transitions",
                        "scale", "scale_source", "scale_domain"):
                assert entry[key] not in (None, ""), f"{key} missing from {entry['path']}"

    # An attempt directory is written once. Nothing may reopen it.
    with pytest.raises(FileExistsError):
        w3_pilot.write_manifest(
            attempt.attempt_dir, artifacts=[], rows=[], scales={}, parameters={}
        )


# --- D-061: the fixed normalisation scale ---------------------------------


def test_the_pilot_scale_comes_from_the_pool_and_is_shared(tmp_path):
    """One vector per evaluation pool, reused across dataset sizes (D-061)."""
    attempt = w3_pilot.run(
        sizes=(100, 250), seeds=(0,), hidden_size=16, out_dir=tmp_path, verbose=False
    )
    scales = {tuple(r.uncertainty["scale"]) for r in attempt.rows}
    assert len(scales) == 1, f"the scale moved between dataset sizes: {scales}"

    for row in attempt.rows:
        assert row.uncertainty["scale_source"] == "evaluation_pool"
        assert row.uncertainty["scale_domain"] == "movement"
        # Measured over the whole movement pool, not over the scored subset --
        # here they coincide, and the recorded count is what proves which.
        assert row.uncertainty["scale_n_reference"] == row.uncertainty["n_evaluated"]

    exported = np.load(attempt.attempt_dir / "transitions_n100_seed0.npz")
    assert list(exported["scale"]) == pytest.approx(attempt.rows[0].uncertainty["scale"])


def test_the_summary_path_will_not_invent_a_scale():
    """What the type actually guarantees — no more (D-064).

    The name this test used to carry was "a mask cannot recompute the scale",
    which claimed more than any assertion below establishes and more than the
    code delivers: the dataclass constructor is public and
    ``from_evaluation_pool`` will accept a masked tensor. What is enforced here
    is narrower and real — the registered summary path refuses to *invent* a
    scale, so a subset can no longer be normalised by accident.
    """
    from bu.models import uncertainty

    targets = torch.randn(200, 2)
    members = targets.unsqueeze(0) + 0.2 * torch.randn(3, 200, 2)

    with pytest.raises(TypeError, match="scale"):
        uncertainty.summarise(members, targets, n_transitions=1, seed=0)
    with pytest.raises(TypeError, match="scale"):
        uncertainty.normalised_error(members.mean(dim=0), targets)

    scale = NormalisationScale.from_evaluation_pool(targets)
    assert scale.n_reference == 200
    with pytest.raises(ValueError, match="expected"):
        NormalisationScale.from_evaluation_pool(targets[:, 0])


def test_a_subset_derived_scale_is_visible_in_the_artefact():
    """Since it cannot be prevented here, it must be *auditable* (D-064).

    ``n_reference`` is the mechanism: a scale built from a mask records the
    size of the mask, so any artefact carrying it can be checked against the
    evaluation pool it claims to be measured in.
    """
    targets = torch.randn(200, 2)
    mask = torch.zeros(200, dtype=torch.bool)
    mask[:10] = True

    pool = NormalisationScale.from_evaluation_pool(targets)
    illegal = NormalisationScale.from_evaluation_pool(targets[mask])

    assert pool.n_reference == 200
    assert illegal.n_reference == 10, (
        "a subset-derived scale must record the subset's size, or nothing "
        "downstream can tell the two apart"
    )
    assert not torch.equal(pool.vector, illegal.vector)
    assert illegal.as_row()["scale_n_reference"] == 10


# --- the delivered evidence ------------------------------------------------


@pytest.mark.skipif(
    not (ROOT / "runs" / "w3_pilot").exists(), reason="no delivered pilot attempt"
)
def test_the_delivered_pilot_attempt_matches_its_manifest():
    """The claimed 18 runs and 90 member records, checked against the disk.

    This is the closeout's evidence requirement: the numbers in the delta are
    verifiable from the repository rather than on my word.
    """
    attempts = sorted((ROOT / "runs" / "w3_pilot").glob(f"{w3_pilot.ATTEMPT_PREFIX}*"))
    if not attempts:
        pytest.skip("the delivered pilot predates attempt directories")
    attempt = attempts[-1]
    manifest = json.loads((attempt / "manifest.json").read_text())
    rows = json.loads((attempt / "rows.json").read_text())

    assert manifest["n_runs"] == 18
    assert manifest["n_member_records"] == 90

    # Checked against the artefacts rather than against the manifest's own
    # counters. Only manifest.json and rows.json are tracked (the run records
    # and exports are regenerable and stay out of git), so the claim has to be
    # supported by what actually reaches the bundle: 18 runs each carrying five
    # member validation errors is where 90 comes from.
    assert len(rows) == 18
    assert len(manifest["runs"]) == 18
    assert sum(len(r["val_position_errors"]) for r in rows) == 90
    assert len({r["run_id"] for r in rows}) == 18
    assert {r["n_transitions"] for r in rows} == set(w3_pilot.K.DATA_SIZES)
    assert {r["seed"] for r in rows} == set(w3_pilot.PILOT_SEEDS)

    # One normalisation vector per evaluation pool, shared by every size.
    assert len(manifest["normalisation"]) == len(w3_pilot.PILOT_SEEDS)
    for seed, recorded in manifest["normalisation"].items():
        scales = {
            tuple(r["uncertainty"]["scale"]) for r in rows if r["seed"] == int(seed)
        }
        assert scales == {tuple(recorded["scale"])}, (
            f"seed {seed}: the scale differs between rows.json and the manifest"
        )
        assert recorded["scale_source"] == "evaluation_pool"

    # The run was recorded from a real commit, not a working tree.
    assert manifest["commit"] != "UNCOMMITTED"
    assert manifest["dirty"] is False, (
        "the delivered attempt was generated from a dirty tree, so its commit "
        "does not identify the code that produced it"
    )

    for entry in manifest["artifacts"]:
        path = attempt / entry["path"]
        if not path.exists():
            continue  # untracked and regenerable; the digest below is for the
            # copy on the machine that produced it
        assert w3_pilot._sha256(path) == entry["sha256"], (
            f"{entry['path']} has changed since the attempt was written"
        )
