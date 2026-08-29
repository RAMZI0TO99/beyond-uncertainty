"""C-010: the masked call site, and the scale it is not allowed to reinvent.

D-061 fixed the normalising scale to the full movement evaluation pool measured
**before any failure mask**. D-064 then corrected the claim that `NormalisationScale`
enforces this: it does not, and cannot — the constructor is public and
`from_evaluation_pool` will accept a masked tensor. The rule is a *call-site*
invariant, and `ScaledEvaluation` is that call site.

W4 Friday is the first cell in the project where a mask exists at all, which is
why this exists before it rather than after.
"""

from __future__ import annotations

import pytest
import torch

from bu.models.uncertainty import (
    NormalisationScale, ScaledEvaluation, summarise,
)

POOL = 400
DIMS = 2


def evaluation(seed: int = 0, pool: int = POOL):
    g = torch.Generator().manual_seed(seed)
    targets = torch.randn(pool, DIMS, generator=g)
    members = torch.randn(5, pool, DIMS, generator=g) * 0.3 + targets
    return ScaledEvaluation.from_pool(members, targets, n_transitions=1000, seed=seed)


def worst_fraction_mask(ev: ScaledEvaluation, fraction: float) -> torch.Tensor:
    """The worst `fraction` of transitions by ensemble-mean error — a failure set."""
    err = (ev.members.mean(dim=0) - ev.targets).norm(dim=-1)
    k = max(1, int(round(ev.n_pool * fraction)))
    mask = torch.zeros(ev.n_pool, dtype=torch.bool)
    mask[err.argsort(descending=True)[:k]] = True
    return mask


# --- the invariant ---------------------------------------------------------


def test_the_masked_summary_reuses_the_pool_scale_object_itself():
    """Not an equal scale — the same object. Equality could be coincidence."""
    ev = evaluation()
    mask = worst_fraction_mask(ev, 0.05)

    whole, masked = ev.whole_pool(), ev.masked(mask)
    assert whole.scale == masked.scale
    assert whole.scale_n_reference == masked.scale_n_reference == ev.n_pool
    # The masked summary reports the POOL's reference count, so a subset-derived
    # scale is visible in the artefact rather than having to be inferred.
    assert masked.n_evaluated < whole.n_evaluated


def test_the_invariant_is_load_bearing_not_decorative():
    """If both choices gave the same answer, enforcing one would be pointless.

    This is the measurement behind D-061: the scale is a *vector*, so it does
    not cancel between the ratio's numerator and denominator. If this test ever
    fails, the scale has become effectively scalar and the whole call-site rule
    should be revisited rather than quietly kept.
    """
    ev = evaluation()
    mask = worst_fraction_mask(ev, 0.05)

    registered = ev.masked(mask)
    subset_scale = NormalisationScale.from_evaluation_pool(ev.targets[mask])
    wrong = summarise(
        ev.members[:, mask], ev.targets[mask],
        n_transitions=ev.n_transitions, seed=ev.seed, scale=subset_scale,
    )

    assert subset_scale.vector.tolist() != ev.scale.vector.tolist()
    assert registered.ratio != wrong.ratio, (
        "the registered H2 ratio is unchanged by which set defined the scale; "
        "if that is genuinely true the D-061 rule is not doing any work"
    )
    # And the subset-derived one is visible for what it is.
    assert subset_scale.n_reference < ev.n_pool


def test_there_is_no_way_to_hand_masked_a_different_scale():
    """No `scale=` parameter, and no `scale=None` convenience to add back."""
    ev = evaluation()
    mask = worst_fraction_mask(ev, 0.1)
    with pytest.raises(TypeError):
        ev.masked(mask, scale=NormalisationScale.from_evaluation_pool(ev.targets[mask]))


def test_from_pool_takes_no_mask_at_all():
    """The scale is built before the object can receive a mask."""
    g = torch.Generator().manual_seed(1)
    targets = torch.randn(POOL, DIMS, generator=g)
    members = torch.randn(5, POOL, DIMS, generator=g)
    with pytest.raises(TypeError):
        ScaledEvaluation.from_pool(members, targets, n_transitions=1, seed=0, mask=None)


# --- refusals --------------------------------------------------------------


def test_an_empty_mask_is_refused():
    """A mean over nothing is nan, and nan reaching an endpoint is silent."""
    ev = evaluation()
    with pytest.raises(ValueError, match="selects no transitions"):
        ev.masked(torch.zeros(ev.n_pool, dtype=torch.bool))


def test_a_mask_of_the_wrong_length_is_refused():
    ev = evaluation()
    with pytest.raises(ValueError, match="the evaluation pool has"):
        ev.masked(torch.ones(ev.n_pool - 1, dtype=torch.bool))


def test_an_index_tensor_is_refused_in_favour_of_a_boolean():
    """A wrong-length index tensor selects the wrong rows without erroring."""
    ev = evaluation()
    with pytest.raises(ValueError, match="must be a boolean tensor"):
        ev.masked(torch.tensor([0, 1, 2]))


def test_an_empty_pool_is_refused():
    with pytest.raises(ValueError, match="pool is empty"):
        ScaledEvaluation.from_pool(
            torch.zeros(5, 0, DIMS), torch.zeros(0, DIMS), n_transitions=1, seed=0
        )


@pytest.mark.parametrize(
    "members, targets",
    [
        (torch.zeros(400, 2), torch.zeros(400, 2)),        # members not 3-D
        (torch.zeros(5, 400, 2), torch.zeros(399, 2)),     # pool axes disagree
    ],
)
def test_mismatched_shapes_are_refused(members, targets):
    with pytest.raises(ValueError):
        ScaledEvaluation.from_pool(members, targets, n_transitions=1, seed=0)


# --- one immutable attempt, chosen explicitly ------------------------------


def test_a_single_attempt_resolves_and_an_unknown_one_does_not(tmp_path):
    from bu.stats.gate import select_attempt

    (tmp_path / "attempt-001").mkdir()
    assert select_attempt(tmp_path).name == "attempt-001"
    assert select_attempt(tmp_path, attempt="attempt-001").name == "attempt-001"
    with pytest.raises(ValueError, match="has no attempt"):
        select_attempt(tmp_path, attempt="attempt-002")


def test_several_attempts_must_be_chosen_between_explicitly(tmp_path):
    """There is no 'latest'. A second attempt exists because the first was wrong."""
    from bu.stats.gate import select_attempt

    (tmp_path / "attempt-001").mkdir()
    (tmp_path / "attempt-002").mkdir()
    with pytest.raises(ValueError, match="name the one you mean"):
        select_attempt(tmp_path)
    assert select_attempt(tmp_path, attempt="attempt-001").name == "attempt-001"


def test_an_empty_root_is_refused(tmp_path):
    from bu.stats.gate import select_attempt

    with pytest.raises(ValueError, match="no attempt-NNN"):
        select_attempt(tmp_path)
