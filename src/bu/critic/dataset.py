"""Week 6 critic dataset boundary: physically separate ``X``, ``y``, groups.

The critic may see only the exact feature tuple registered for its chosen
variant in :mod:`bu.critic.schema`.  Labels and construction/splitting metadata
remain in separate objects and are never returned by :meth:`model_input`.

Inputs and outputs are copied recursively.  This matters because several
registered features are array- or history-valued objects: pandas' ordinary
``deep=True`` copy does not recursively copy Python objects stored in cells.
"""

from __future__ import annotations

import copy
from numbers import Integral

import pandas as pd

from .balance import ESTIMATION, HYPOTHESIS_CLASS, UNDECIDABLE
from .schema import CRITIC_SCHEMA_VERSION, features_for

GROUP_ID_COLUMNS = ("unit_id", "comparison_group_id")


def _copy_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Copy a frame and every cell object, including nested feature values."""
    out = frame.copy(deep=True)
    for row in range(frame.shape[0]):
        for column in range(frame.shape[1]):
            out.iat[row, column] = copy.deepcopy(frame.iat[row, column])
    return out


def _copy_series(series: pd.Series) -> pd.Series:
    """Copy a series and every cell object."""
    out = series.copy(deep=True)
    for row in range(series.shape[0]):
        out.iat[row] = copy.deepcopy(series.iat[row])
    return out


def _validate_unique_string_columns(
    frame: pd.DataFrame,
    *,
    structure: str,
) -> tuple[str, ...]:
    columns = tuple(frame.columns)
    if any(not isinstance(column, str) for column in columns):
        raise ValueError(
            f"{structure} column names must all be strings, got {columns!r}"
        )
    if len(set(columns)) != len(columns):
        raise ValueError(f"{structure} has duplicate columns: {columns!r}")
    return columns


def _validate_observed_label(value: object, *, index: object) -> None:
    if isinstance(value, bool):
        raise ValueError(
            f"y[{index!r}] is boolean {value!r}; booleans are not observed "
            "labels even though bool subclasses int and compares equal to an "
            "observed integer label"
        )
    if isinstance(value, Integral) and int(value) in (
        ESTIMATION,
        HYPOTHESIS_CLASS,
    ):
        return
    if isinstance(value, str) and value in UNDECIDABLE:
        return
    raise ValueError(
        f"y[{index!r}] has invalid observed label {value!r} "
        f"({type(value).__name__}); expected integer 0/1 or "
        f"{'/'.join(UNDECIDABLE)}"
    )


class CriticDataset:
    """A copied, validated three-road dataset for one frozen critic variant.

    ``X``, ``y`` and ``groups`` properties each return fresh deep copies.  The
    sole model-facing method, :meth:`model_input`, returns ``X`` alone.
    """

    __slots__ = ("_X", "_y", "_groups", "_variant")

    def __init__(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        groups: pd.DataFrame,
        *,
        variant: str,
    ) -> None:
        if not isinstance(X, pd.DataFrame):
            raise ValueError(f"X must be a pandas DataFrame, got {type(X).__name__}")
        if not isinstance(y, pd.Series):
            raise ValueError(f"y must be a pandas Series, got {type(y).__name__}")
        if not isinstance(groups, pd.DataFrame):
            raise ValueError(
                "groups must be a pandas DataFrame, got "
                f"{type(groups).__name__}"
            )

        expected = features_for(variant)
        columns = _validate_unique_string_columns(X, structure="X")
        _validate_unique_string_columns(groups, structure="groups")
        if columns != expected:
            missing = tuple(feature for feature in expected if feature not in columns)
            extra = tuple(column for column in columns if column not in expected)
            raise ValueError(
                f"X columns must exactly equal the registered ordered feature "
                f"tuple for variant {variant!r}; missing={missing}, extra={extra}, "
                f"expected={expected}, received={columns}. Labels, metadata and "
                "unknown columns cannot enter X"
            )
        if not X.index.is_unique:
            raise ValueError("X index must be unique so alignment is unambiguous")
        if len(X) == 0:
            raise ValueError(
                "critic dataset is empty; a zero-row boundary passes alignment "
                "and leakage checks vacuously but cannot train or evaluate a critic"
            )
        if not X.index.equals(y.index) or not X.index.equals(groups.index):
            raise ValueError(
                "X, y and groups indices must match exactly in values and order; "
                "implicit reindexing is refused"
            )

        missing_group_columns = tuple(
            column for column in GROUP_ID_COLUMNS if column not in groups.columns
        )
        if missing_group_columns:
            raise ValueError(
                f"groups is missing required identity column(s) "
                f"{missing_group_columns}; identities belong in groups, never X"
            )
        for column in GROUP_ID_COLUMNS:
            for index, value in groups[column].items():
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(
                        f"groups[{column!r}][{index!r}] must be a non-blank "
                        f"string, got {value!r} ({type(value).__name__})"
                    )

        unit_to_group: dict[str, str] = {}
        for unit_id, group_id in groups.loc[:, GROUP_ID_COLUMNS].itertuples(
            index=False, name=None
        ):
            prior = unit_to_group.setdefault(unit_id, group_id)
            if prior != group_id:
                raise ValueError(
                    f"unit_id {unit_id!r} maps to both comparison groups "
                    f"{prior!r} and {group_id!r}"
                )

        for index, value in y.items():
            _validate_observed_label(value, index=index)

        self._X = _copy_frame(X)
        self._y = _copy_series(y)
        self._groups = _copy_frame(groups)
        self._variant = variant

    @property
    def variant(self) -> str:
        return self._variant

    @property
    def schema_version(self) -> int:
        return CRITIC_SCHEMA_VERSION

    @property
    def X(self) -> pd.DataFrame:
        return _copy_frame(self._X)

    @property
    def y(self) -> pd.Series:
        return _copy_series(self._y)

    @property
    def groups(self) -> pd.DataFrame:
        return _copy_frame(self._groups)

    def model_input(self) -> pd.DataFrame:
        """Return the allowlisted feature frame alone, with no labels/metadata."""
        return _copy_frame(self._X)
