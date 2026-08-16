"""Ensemble uncertainty metrics (Schedule W3 Fri, Plan §10.3).

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

#: Guard on the H2 denominator (Plan §10.3). Not tuned; it exists so a
#: near-zero mean error cannot produce an arbitrarily large ratio.
RATIO_FLOOR = 1e-6


def per_dimension_scale(targets: torch.Tensor) -> torch.Tensor:
    """Per-dimension scale used to normalise error (Plan §10.3).

    Measured on the evaluation targets rather than assumed, and floored so a
    constant dimension cannot divide by zero.
    """
    scale = targets.std(dim=0, unbiased=False)
    return torch.clamp(scale, min=RATIO_FLOOR)


def normalised_error(
    predictions: torch.Tensor, targets: torch.Tensor, scale: torch.Tensor | None = None
) -> torch.Tensor:
    """Per-transition error, per-dimension normalised.

    Args:
        predictions: ``(batch, dims)`` — one model's predictions, or an
            ensemble mean.
        targets: ``(batch, dims)``.
    """
    scale = per_dimension_scale(targets) if scale is None else scale
    return torch.linalg.vector_norm((predictions - targets) / scale, dim=1)


def pairwise_disagreement(
    members: torch.Tensor, scale: torch.Tensor | None = None
) -> torch.Tensor:
    """Mean pairwise distance between member predictions, per transition.

    Plan §10.3's definition. ``members`` is ``(n_members, batch, dims)``.

    The mean is over **ordered** pairs excluding the diagonal, which is the same
    number as the mean over unordered pairs — stated because the two conventions
    differ by a factor of two and a disagreement number without its convention
    is not comparable to anything.
    """
    k = members.shape[0]
    if k < 2:
        raise ValueError(f"disagreement needs at least two members, got {k}")

    if scale is not None:
        members = members / scale
    # (batch, k, dims) -> (batch, k, k) pairwise distances
    distances = torch.cdist(members.permute(1, 0, 2), members.permute(1, 0, 2))
    return distances.sum(dim=(1, 2)) / (k * (k - 1))


def predictive_variance(
    members: torch.Tensor, scale: torch.Tensor | None = None
) -> torch.Tensor:
    """Ensemble predictive variance, per transition (Plan §10.3).

    Summed over dimensions after normalisation, so it is one number per
    transition like the disagreement it sits beside.
    """
    if scale is not None:
        members = members / scale
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

    def as_row(self) -> dict[str, float | int]:
        return {
            "n_transitions": self.n_transitions,
            "seed": self.seed,
            "n_evaluated": self.n_evaluated,
            "mean_error": self.mean_error,
            "mean_disagreement": self.mean_disagreement,
            "mean_predictive_variance": self.mean_predictive_variance,
            "ratio": self.ratio,
        }


def summarise(
    members: torch.Tensor,
    targets: torch.Tensor,
    *,
    n_transitions: int,
    seed: int,
) -> UncertaintySummary:
    """Per-seed summary. The division happens **here**, before any pooling.

    Pooling across seeds and then dividing would be a different statistic, and
    Plan §10.3 names this one.
    """
    scale = per_dimension_scale(targets)
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
    )


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
