"""Chronological train/test splits with embargo and rolling-origin folds (Ticket R10.1).

Enforces:
1. Chronological order (no shuffling or temporal leakage).
2. Embargo buffer (default 7 days) immediately preceding test intervals to eliminate
   autocorrelation / weather system persistence leakage.
3. Rolling-origin cross-validation with expanding train windows and embargo.
"""
from __future__ import annotations

import datetime as dt
from typing import Sequence


def _parse_date(d: dt.date | dt.datetime | str) -> dt.date:
    """Parse date-like object to dt.date."""
    if isinstance(d, dt.datetime):
        return d.date()
    elif isinstance(d, dt.date):
        return d
    elif isinstance(d, str):
        # Support ISO formats: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS
        cleaned = d.strip().split("T")[0].split(" ")[0]
        return dt.date.fromisoformat(cleaned)
    raise TypeError(f"Cannot parse date from type {type(d)}: {d!r}")


def chronological_split(
    dates: Sequence[dt.date | dt.datetime | str],
    test_fraction: float = 0.2,
    embargo_days: int = 7,
    test_start_date: dt.date | dt.datetime | str | None = None,
) -> tuple[list[int], list[int]]:
    """Perform a chronological train/test split with an embargo buffer.

    Args:
        dates: Sequence of timestamps or dates corresponding to samples.
        test_fraction: Fraction of data reserved for testing (ignored if test_start_date given).
        embargo_days: Days before the test period to drop from training to prevent autocorrelation leakage.
        test_start_date: Optional explicit start date for the test period.

    Returns:
        (train_indices, test_indices)
    """
    if not dates:
        return [], []

    parsed_dates = [_parse_date(d) for d in dates]
    indexed_dates = list(enumerate(parsed_dates))
    # Sort strictly by date while preserving original index
    indexed_dates.sort(key=lambda x: x[1])

    n = len(indexed_dates)
    if test_start_date is not None:
        split_date = _parse_date(test_start_date)
    else:
        # Determine split date based on fraction of unique dates or sorted index
        test_size = max(1, int(n * test_fraction))
        split_idx = max(0, n - test_size)
        split_date = indexed_dates[split_idx][1]

    embargo_delta = dt.timedelta(days=embargo_days)
    embargo_cutoff = split_date - embargo_delta

    train_indices: list[int] = []
    test_indices: list[int] = []

    for orig_idx, d in indexed_dates:
        if d >= split_date:
            test_indices.append(orig_idx)
        elif d <= embargo_cutoff:
            train_indices.append(orig_idx)
        # Any date between embargo_cutoff < d < split_date is embargoed and dropped

    return sorted(train_indices), sorted(test_indices)


def rolling_origin_folds(
    dates: Sequence[dt.date | dt.datetime | str],
    n_splits: int = 5,
    min_train_days: int = 30,
    test_days: int = 7,
    embargo_days: int = 7,
    step_days: int | None = None,
) -> list[tuple[list[int], list[int]]]:
    """Generate rolling-origin (expanding window) folds for time series evaluation.

    Each fold consists of:
    - Train window: all observations on or before (origin_date - embargo_days)
    - Test window: all observations in [origin_date, origin_date + test_days)

    Args:
        dates: Sequence of dates for each sample.
        n_splits: Number of rolling folds.
        min_train_days: Minimum number of historical days required before first fold origin.
        test_days: Duration of test window for each fold.
        embargo_days: Number of days before origin excluded from training.
        step_days: Days between origins (defaults to test_days if None).

    Returns:
        List of (train_indices, test_indices) tuples.
    """
    if not dates:
        return []

    parsed_dates = [_parse_date(d) for d in dates]
    min_date = min(parsed_dates)
    max_date = max(parsed_dates)
    total_span = (max_date - min_date).days

    required_span = min_train_days + embargo_days + test_days
    if total_span < required_span:
        raise ValueError(
            f"Dataset span ({total_span} days) is shorter than required minimum "
            f"({required_span} days: min_train={min_train_days} + embargo={embargo_days} + test={test_days})"
        )

    actual_step = step_days if step_days is not None else test_days
    earliest_origin = min_date + dt.timedelta(days=min_train_days + embargo_days)
    latest_origin = max_date - dt.timedelta(days=test_days)

    available_span = (latest_origin - earliest_origin).days
    if available_span < 0:
        # Only one origin possible
        origins = [earliest_origin]
    else:
        if n_splits <= 1:
            origins = [latest_origin]
        else:
            computed_step = max(1, available_span // (n_splits - 1))
            step = min(actual_step, computed_step)
            origins = [earliest_origin + dt.timedelta(days=i * step) for i in range(n_splits)]
            origins = [o for o in origins if o <= latest_origin]

    folds: list[tuple[list[int], list[int]]] = []
    embargo_delta = dt.timedelta(days=embargo_days)
    test_delta = dt.timedelta(days=test_days)

    for origin in origins:
        train_cutoff = origin - embargo_delta
        test_end = origin + test_delta

        train_idx = [i for i, d in enumerate(parsed_dates) if d <= train_cutoff]
        test_idx = [i for i, d in enumerate(parsed_dates) if origin <= d < test_end]

        if train_idx and test_idx:
            folds.append((train_idx, test_idx))

    return folds
