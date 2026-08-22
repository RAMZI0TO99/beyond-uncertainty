"""Ensemble uncertainty metrics (Schedule W3 Fri, Plan §10.3).

**Scope:** this module implements P§10.3's *mean pairwise disagreement*,
*predictive variance*, *per-dimension normalised error* and the *ratio*. It does
**not** implement the per-condition error/disagreement correlation, which
P§10.3 also names as a secondary diagnostic (D-059).

These are the dependent variables. H1 is a claim about how **mean pairwise
disagreement** moves with dataset size; H2 is a claim about the **ratio** of
disagreement to error. Everything here is therefore a preregistered definition
rather than a convenience, and Plan §10.3 fixes several choices that would
otherwise be silent degrees of freedom.

What the plan fixes, and what follows from it
---------------------------------------------
* **Per-dimension normalised error**, so a dimension with a larger natural scale
  cannot dominate. Here that is nearly moot — D-032 already restricted the
  scientific error to the two grid-normalised agent-position dimensions — but
  the normalisation is applied anyway, because the plan says so and because the
  scale it divides by is measured on the evaluation pool rather than assumed.
* **Which set defines that scale is now fixed** (D-061): the full evaluation
  pool restricted to movement transitions, computed **before** any failure mask.
  P§10.3 never said, and the code recomputed it from whatever subset it was
  handed — which moves the registered H2 endpoint by up to 4.6% (D-060, W3-1).

  What :class:`NormalisationScale` does and does not give you (D-064): the
  registered summary path **requires an explicit scale object** and will not
  invent one, so a subset can no longer be normalised by accident. It does not
  make a subset-derived scale *impossible* — the dataclass constructor is
  public, :meth:`NormalisationScale.from_evaluation_pool` accepts any 2-D
  tensor including a masked one, and the low-level metric functions still take
  raw tensors. The rule is therefore a **call-site invariant**, and it is the
  caller's job to satisfy it: the W3 pilot builds the scale from the full
  movement evaluation pool, and the W4 runner must build it **before** it
  produces the failure mask and reuse the same object for the whole-pool and
  masked calculations. That invariant is a required test of the W4 runner, not
  a property this module can enforce alone.
* **Ratio of means, never mean of ratios.** Near-zero denominators make
  per-transition ratios arbitrarily large and a mean of them meaningless. The
  two are different statistics and can differ in the sign of an effect.
* **A numerical floor of 1e-6** on the denominator, as a guard rather than a
  tuning parameter.
* **Computed per seed, reported as a mean across seeds with its standard
  deviation** — never pooled across seeds before the division.

Everything is computed on the **evaluation pool** (D-052), which no model
selection ever touched.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch

from .. import constants as K

#: Guard on the H2 denominator (Plan §10.3). Not tuned; it exists so a
#: near-zero mean error cannot produce an arbitrarily large ratio.
RATIO_FLOOR = 1e-6


def per_dimension_scale(targets: torch.Tensor) -> torch.Tensor:
    """Per-dimension scale (Plan §10.3). **The only place a scale is computed.**

    Measured rather than assumed, and floored so a constant dimension cannot
    divide by zero. Not called directly by analysis code: go through
    :meth:`NormalisationScale.from_evaluation_pool`, which records *what* the
    vector was computed from (D-061).
    """
    scale = targets.std(dim=0, unbiased=False)
    return torch.clamp(scale, min=RATIO_FLOOR)


#: The registered domain of the normalisation (DEV-007): the primary error is
#: agent position over movement transitions, so the scale is measured there.
#: Both live in ``constants.py`` because they are preregistered definitional
#: choices, not implementation details — the same reason the acceptance
#: threshold does (D-061).
SCALE_DOMAIN = K.NORMALISATION_SCALE_DOMAIN
#: What the scale is computed from. Sol's D-061 ruling admits exactly one value.
SCALE_SOURCE = K.NORMALISATION_SCALE_SOURCE


@dataclass(frozen=True)
class NormalisationScale:
    """The per-dimension scale, with the evidence of where it came from (D-061).

    **Why this is an object rather than a tensor.** P§10.3 requires per-dimension
    normalisation but never says which set defines it, and the W3 audit found the
    code recomputing it from whatever targets it was handed. Because the scale is
    a **vector**, it does not cancel between the ratio's numerator and its
    denominator: dividing each dimension by a different amount reshapes both
    vectors, and their norms have no common factor to cancel. Measured on pilot
    data, the registered H2 endpoint moved by up to 4.6% between a pool-derived
    and a failure-set-derived scale — a degree of freedom nobody chose.

    Sol's ruling: compute it **once from the full evaluation pool restricted to
    movement transitions, before any failure mask**, and reuse that exact vector
    for the whole-pool and the failure-subset calculations, across every member
    and every dataset size sharing that evaluation pool.

    **What this type actually guarantees** (D-064). It makes the scale explicit
    and auditable: the registered summary path will not accept a missing scale
    and will not invent one, and ``n_reference`` records how many transitions
    the vector was measured over, so a subset-derived scale is *visible* in
    every artefact that carries it. It does **not** make one impossible — this
    constructor is public and :meth:`from_evaluation_pool` will accept a masked
    tensor if handed one. The ruling is a call-site invariant, checked where the
    call site is built, not a property the type can enforce by itself.
    """

    vector: torch.Tensor
    #: Transitions the vector was computed from — the pool, never a subset.
    n_reference: int
    domain: str = SCALE_DOMAIN
    source: str = SCALE_SOURCE

    @classmethod
    def from_evaluation_pool(
        cls, targets: torch.Tensor, *, domain: str = SCALE_DOMAIN
    ) -> NormalisationScale:
        """Build from the **full** evaluation-pool targets, pre-mask (D-061).

        Args:
            targets: ``(n_pool, dims)`` — every transition in the evaluation
                pool that lies in ``domain``, with no failure mask applied.
                Passing a masked subset here is a **call-site error** this
                method cannot detect; ``n_reference`` is what makes it visible
                afterwards (D-064).
        """
        if targets.ndim != 2:
            raise ValueError(
                f"expected (n_pool, dims) evaluation targets, got {tuple(targets.shape)}"
            )
        return cls(
            vector=per_dimension_scale(targets),
            n_reference=int(targets.shape[0]),
            domain=domain,
        )

    def as_row(self) -> dict:
        """Persisted with every result artefact, so a number carries its units."""
        return {
            "scale": [float(v) for v in self.vector],
            "scale_n_reference": self.n_reference,
            "scale_domain": self.domain,
            "scale_source": self.source,
        }


def _vector(scale: NormalisationScale | torch.Tensor) -> torch.Tensor:
    if isinstance(scale, NormalisationScale):
        return scale.vector
    if isinstance(scale, torch.Tensor):
        return scale
    raise TypeError(
        f"scale must be a NormalisationScale (or a raw tensor in low-level "
        f"code), got {type(scale).__name__}. Build one with "
        "NormalisationScale.from_evaluation_pool(pool_targets) — never from the "
        "subset being scored (D-061)."
    )


def normalised_error(
    predictions: torch.Tensor,
    targets: torch.Tensor,
    scale: NormalisationScale | torch.Tensor,
) -> torch.Tensor:
    """Per-transition error, per-dimension normalised.

    ``scale`` is **required**. It used to default to ``None`` meaning "recompute
    from ``targets``", which is exactly the defect D-061 rules on: scoring a
    failure subset then silently measured it in the subset's own units.

    Args:
        predictions: ``(batch, dims)`` — one model's predictions, or an
            ensemble mean.
        targets: ``(batch, dims)``.
        scale: the evaluation pool's fixed scale.
    """
    return torch.linalg.vector_norm(
        (predictions - targets) / _vector(scale), dim=1
    )


def pairwise_disagreement(
    members: torch.Tensor, scale: NormalisationScale | torch.Tensor | None = None
) -> torch.Tensor:
    """Mean pairwise distance between member predictions, per transition.

    Plan §10.3's definition. ``members`` is ``(n_members, batch, dims)``.

    The sum runs over ordered off-diagonal pairs and divides by ``k(k-1)``,
    which is **numerically identical** to summing unordered pairs and dividing
    by ``k(k-1)/2``. An earlier version of this docstring claimed the two
    conventions differ by a factor of two; they do not, when each is normalised
    by its own pair count (D-059). Verified against an explicit enumeration.
    """
    k = members.shape[0]
    if k < 2:
        raise ValueError(f"disagreement needs at least two members, got {k}")

    if scale is not None:
        members = members / _vector(scale)
    # (batch, k, dims) -> (batch, k, k) pairwise distances
    distances = torch.cdist(members.permute(1, 0, 2), members.permute(1, 0, 2))
    return distances.sum(dim=(1, 2)) / (k * (k - 1))


def predictive_variance(
    members: torch.Tensor, scale: NormalisationScale | torch.Tensor | None = None
) -> torch.Tensor:
    """Ensemble predictive variance, per transition (Plan §10.3).

    Summed over dimensions after normalisation, so it is one number per
    transition like the disagreement it sits beside.
    """
    if scale is not None:
        members = members / _vector(scale)
    return members.var(dim=0, unbiased=False).sum(dim=1)


@dataclass(frozen=True)
class UncertaintySummary:
    """One condition, one seed: the quantities H1 and H2 are stated over."""

    n_transitions: int
    seed: int
    n_evaluated: int
    mean_error: float
    mean_disagreement: float
    mean_predictive_variance: float
    #: Plan §10.3's H2 ratio: a **ratio of means**, floored, per seed.
    ratio: float
    #: The normalisation these numbers are expressed in (D-061). Carried in the
    #: summary itself so a number cannot travel without its units — the failure
    #: mode of D-042 and D-044, arriving through a different quantity.
    scale: tuple[float, ...] = ()
    scale_n_reference: int = 0
    scale_domain: str = SCALE_DOMAIN
    scale_source: str = SCALE_SOURCE

    def as_row(self) -> dict:
        return {
            "n_transitions": self.n_transitions,
            "seed": self.seed,
            "n_evaluated": self.n_evaluated,
            "mean_error": self.mean_error,
            "mean_disagreement": self.mean_disagreement,
            "mean_predictive_variance": self.mean_predictive_variance,
            "ratio": self.ratio,
            "scale": list(self.scale),
            "scale_n_reference": self.scale_n_reference,
            "scale_domain": self.scale_domain,
            "scale_source": self.scale_source,
        }


def summarise(
    members: torch.Tensor,
    targets: torch.Tensor,
    *,
    n_transitions: int,
    seed: int,
    scale: NormalisationScale,
) -> UncertaintySummary:
    """Per-seed summary. The division happens **here**, before any pooling.

    Pooling across seeds and then dividing would be a different statistic, and
    Plan §10.3 names this one.

    ``scale`` is the evaluation pool's fixed scale and is **required** (D-061).
    It previously defaulted to recomputing from ``targets``, so scoring a failure
    subset measured it in the subset's own units: measured on one condition, the
    scale is [0.229, 0.224] over the full evaluation pool and [0.294, 0.348] over
    its worst 5%.

    **A correction to what this docstring used to say.** It claimed the *ratio*
    was invariant to the choice because numerator and denominator share the
    scale. That is false, and the W3 audit measured it false: a **scalar** scale
    would cancel, but a per-dimension one divides each dimension by a different
    amount, reshaping both vectors so their norms have no common factor. The
    registered H2 endpoint moved by up to 4.6% on the choice alone. The error was
    to reason about a vector as though it were a scalar, and it survived three
    files until Sol asked (D-061).
    """
    ensemble_mean = members.mean(dim=0)

    error = normalised_error(ensemble_mean, targets, scale)
    disagreement = pairwise_disagreement(members, scale)
    variance = predictive_variance(members, scale)

    mean_error = float(error.mean())
    return UncertaintySummary(
        n_transitions=n_transitions,
        seed=seed,
        n_evaluated=int(error.numel()),
        mean_error=mean_error,
        mean_disagreement=float(disagreement.mean()),
        mean_predictive_variance=float(variance.mean()),
        ratio=float(disagreement.mean()) / max(mean_error, RATIO_FLOOR),
        scale=tuple(float(v) for v in scale.vector),
        scale_n_reference=scale.n_reference,
        scale_domain=scale.domain,
        scale_source=scale.source,
    )


@dataclass(frozen=True)
class SpreadDiagnostic:
    """Member-level spread, which is what a collapse claim actually needs (D-059).

    A low standard deviation of the **ensemble mean** does not establish that
    each member has collapsed toward a constant: members that vary a great deal
    can cancel in their average. Constructed counterexample — ensemble-mean sd
    0.051 while individual members have sd 2.556. So the mean is reported
    alongside the per-member values rather than standing in for them.
    """

    target_sd: float
    ensemble_mean_sd: float
    member_sds: tuple[float, ...]
    #: Each member's spread as a fraction of the targets'. A collapse claim
    #: needs *every* entry small, not just the ensemble mean.
    member_sd_ratios: tuple[float, ...]

    @property
    def min_member_ratio(self) -> float:
        return min(self.member_sd_ratios)

    @property
    def max_member_ratio(self) -> float:
        return max(self.member_sd_ratios)

    def as_row(self) -> dict:
        return {
            "target_sd": self.target_sd,
            "ensemble_mean_sd": self.ensemble_mean_sd,
            "member_sds": list(self.member_sds),
            "member_sd_ratios": list(self.member_sd_ratios),
        }


def spread_diagnostic(members: torch.Tensor, targets: torch.Tensor) -> SpreadDiagnostic:
    """Per-member and ensemble-mean spread against the targets' (D-059)."""
    target_sd = float(targets.std(dim=0, unbiased=False).mean())
    member_sds = tuple(
        float(members[i].std(dim=0, unbiased=False).mean()) for i in range(members.shape[0])
    )
    denominator = max(target_sd, RATIO_FLOOR)
    return SpreadDiagnostic(
        target_sd=target_sd,
        ensemble_mean_sd=float(members.mean(dim=0).std(dim=0, unbiased=False).mean()),
        member_sds=member_sds,
        member_sd_ratios=tuple(sd / denominator for sd in member_sds),
    )


def per_transition_table(
    members: torch.Tensor,
    targets: torch.Tensor,
    *,
    episode: np.ndarray,
    step: np.ndarray,
    scale: NormalisationScale,
) -> dict[str, np.ndarray]:
    """The per-transition export the schedule requires (D-059).

    *"Mean pairwise disagreement and predictive variance, exported **per
    transition**."* Summaries are a derived artefact; without the transition
    level, failure-set filtering, the local error/disagreement correlation and
    independent regeneration of the registered H2 endpoint are all impossible
    after the fact.

    The scale travels **inside the export** (D-061). A downstream failure-set
    analysis reading this file must apply its mask to these rows, not recompute
    a normalisation from them, and it can now check which vector produced them.
    """
    return {
        "episode": np.asarray(episode),
        "step": np.asarray(step),
        "error": normalised_error(members.mean(dim=0), targets, scale).numpy(),
        "disagreement": pairwise_disagreement(members, scale).numpy(),
        "predictive_variance": predictive_variance(members, scale).numpy(),
        "scale": np.asarray([float(v) for v in scale.vector], dtype=np.float64),
        "scale_n_reference": np.asarray(scale.n_reference),
        "scale_domain": np.asarray(scale.domain),
        "scale_source": np.asarray(scale.source),
    }


def across_seeds(summaries: list[UncertaintySummary]) -> dict[str, float]:
    """Mean and standard deviation across seeds, never pooled before dividing."""
    if not summaries:
        raise ValueError("no summaries to aggregate")
    out: dict[str, float] = {"n_seeds": len(summaries)}
    for field in ("mean_error", "mean_disagreement", "mean_predictive_variance", "ratio"):
        values = np.array([getattr(s, field) for s in summaries], dtype=float)
        out[f"{field}_mean"] = float(values.mean())
        out[f"{field}_sd"] = float(values.std(ddof=1)) if len(values) > 1 else 0.0
    return out


@dataclass(frozen=True)
class ScaledEvaluation:
    """The evaluation pool, its one scale, and the only sanctioned way to score a
    subset of it (**C-010**, enforcing D-061 as corrected by D-064).

    **What this closes.** ``NormalisationScale`` makes the scale explicit and
    auditable, but D-064 was explicit that it cannot make a subset-derived scale
    *impossible*: the constructor is public and
    :meth:`NormalisationScale.from_evaluation_pool` will accept a masked tensor
    if handed one. The rule is a **call-site invariant**. This type is that call
    site, and it enforces the rule structurally rather than by discipline:

    * :meth:`from_pool` is the only constructor, and it takes **no mask**. The
      scale is built there, from the full movement evaluation pool, before any
      mask exists — not "before the mask is applied", but before the object is
      capable of receiving one.
    * :meth:`masked` reuses ``self.scale`` — the identical object, not an equal
      one — and there is no parameter by which a caller could supply another.
      There is deliberately no ``scale=None`` convenience anywhere on this path.

    **Why it matters, measured rather than asserted.** The scale is a *vector*,
    so it does not cancel between the ratio's numerator and denominator. On
    pilot data the registered H2 endpoint moved by up to **4.6%** between a
    pool-derived and a failure-set-derived scale: [0.229, 0.224] over the full
    evaluation pool against [0.294, 0.348] over its worst 5%. That is a degree
    of freedom nobody chose, and W4 Friday is the first cell where a mask exists
    at all — so it is the first cell where this can go wrong.

    **What it still does not guarantee.** If a caller hands ``from_pool`` an
    already-masked tensor, the scale is that subset's. Nothing here can detect
    it, exactly as D-064 says. What survives is visibility: ``n_reference``
    records the transition count the vector was measured over and travels into
    every summary this object produces, including masked ones — so a masked
    summary always reports the *pool's* reference count, and a subset-derived
    scale shows up as a reference count that does not match the pool.
    """

    #: ``(K, n_pool, dims)`` — every member's prediction over the full movement
    #: evaluation pool.
    members: torch.Tensor
    #: ``(n_pool, dims)`` — the pool's targets, unmasked.
    targets: torch.Tensor
    #: Built in :meth:`from_pool`, before this object could hold a mask.
    scale: NormalisationScale
    n_transitions: int
    seed: int

    @classmethod
    def from_pool(
        cls,
        members: torch.Tensor,
        targets: torch.Tensor,
        *,
        n_transitions: int,
        seed: int,
    ) -> ScaledEvaluation:
        """Build from the **full** movement evaluation pool. Takes no mask.

        Args:
            members: ``(K, n_pool, dims)``, every member over the whole pool.
            targets: ``(n_pool, dims)``, the whole pool's targets, **unmasked**.
        """
        if members.ndim != 3:
            raise ValueError(
                f"members must be (K, n_pool, dims); got shape {tuple(members.shape)}"
            )
        if targets.ndim != 2 or targets.shape[0] != members.shape[1]:
            raise ValueError(
                f"targets must be (n_pool, dims) matching members' pool axis; got "
                f"{tuple(targets.shape)} against members {tuple(members.shape)}"
            )
        if targets.shape[0] == 0:
            raise ValueError(
                "the evaluation pool is empty, so there is nothing to measure a "
                "scale over. A scale built from nothing would propagate as nan "
                "into every summary that reused it"
            )
        return cls(
            members=members,
            targets=targets,
            scale=NormalisationScale.from_evaluation_pool(targets),
            n_transitions=n_transitions,
            seed=seed,
        )

    @property
    def n_pool(self) -> int:
        return int(self.targets.shape[0])

    def whole_pool(self) -> UncertaintySummary:
        """Summarise the entire pool, in the pool's own scale."""
        return summarise(
            self.members,
            self.targets,
            n_transitions=self.n_transitions,
            seed=self.seed,
            scale=self.scale,
        )

    def ensemble_mean_error(self) -> torch.Tensor:
        """Per-transition error over the whole pool, in the pool's scale.

        **This is the quantity the threshold was calibrated on**, computed the
        same way W4 Friday computed it: the ensemble *mean prediction* scored
        against the targets, not the mean of the members' errors. Those are
        different numbers, and calibrating on one while masking with the other
        would shift the failure set silently — the failure rate would simply not
        be 5% any more, with nothing raised.
        """
        return normalised_error(self.members.mean(dim=0), self.targets, self.scale)

    def failure_mask(self) -> torch.Tensor:
        """The **registered** failure set: error strictly greater than the frozen
        threshold (D-107, promoted under D-035).

        **It takes no threshold, and there is deliberately no override.** Sol's
        promotion ruling required that registered failure-mask construction
        consume the constant with no caller-selectable alternative, for the same
        reason ``from_pool`` takes no mask (C-010, D-076): a value a caller can
        pass is a degree of freedom somebody eventually uses. The threshold was
        calibrated once, on a reference model, and every failure set and repair
        label in the thesis descends from it. If you want a different cut, you
        do not want the registered failure set.

        **Strictly greater** is part of the definition, not a convention. At
        exact equality the transition is *not* a failure, and two transitions in
        the calibration pool itself sit exactly there.

        Returns:
            boolean ``(n_pool,)``, ready for :meth:`masked`. It may select
            nothing — on a model that never exceeds the threshold — and
            :meth:`masked` refuses an empty mask rather than returning a nan
            summary, which is the correct fail-closed behaviour and not a bug.
        """
        return self.ensemble_mean_error() > K.FAILURE_THRESHOLD

    def masked(self, mask: torch.Tensor) -> UncertaintySummary:
        """Summarise a subset — the failure set — **in the pool's scale** (D-061).

        Args:
            mask: boolean ``(n_pool,)``. Index tensors are refused: a long
                tensor of the wrong length silently selects the wrong rows,
                whereas a boolean of the wrong length cannot.
        """
        if mask.dtype != torch.bool:
            raise ValueError(
                f"mask must be a boolean tensor, got dtype {mask.dtype}. An index "
                "tensor of the wrong length selects the wrong transitions without "
                "any error; a boolean of the wrong length cannot"
            )
        if mask.shape != (self.n_pool,):
            raise ValueError(
                f"mask has shape {tuple(mask.shape)}; the evaluation pool has "
                f"{self.n_pool} transitions. A mask built against a different pool "
                "would score a different set than the one it names"
            )
        if not bool(mask.any()):
            raise ValueError(
                "the mask selects no transitions. A mean over nothing is nan, and "
                "a silently empty failure set is how nan reaches a registered "
                "endpoint (see `movement_position_error`)"
            )
        return summarise(
            self.members[:, mask],
            self.targets[mask],
            n_transitions=self.n_transitions,
            seed=self.seed,
            scale=self.scale,
        )
