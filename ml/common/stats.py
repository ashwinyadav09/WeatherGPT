"""Statistical metrics and paired block bootstrap for model evaluation (Ticket R10.1).

Implements:
- MAE, RMSE, mean bias error
- Brier score, Brier skill score (BSS)
- Heidke skill score (HSS)
- PR-AUC (Precision-Recall Area Under Curve)
- ECE (Expected Calibration Error)
- Paired block bootstrap (weekly blocks, B=2000, fixed seed) for differences against baseline
"""
from __future__ import annotations

import datetime as dt
import math
from typing import Any, Callable, Sequence

import numpy as np


def mean_absolute_error(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    """Compute Mean Absolute Error (MAE)."""
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have the same length")
    if len(y_true) == 0:
        return 0.0
    return float(np.mean(np.abs(np.array(y_pred, dtype=float) - np.array(y_true, dtype=float))))


def root_mean_squared_error(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    """Compute Root Mean Squared Error (RMSE)."""
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have the same length")
    if len(y_true) == 0:
        return 0.0
    diff = np.array(y_pred, dtype=float) - np.array(y_true, dtype=float)
    return float(np.sqrt(np.mean(diff ** 2)))


def mean_bias_error(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    """Compute Mean Bias Error (forecast - observed)."""
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have the same length")
    if len(y_true) == 0:
        return 0.0
    diff = np.array(y_pred, dtype=float) - np.array(y_true, dtype=float)
    return float(np.mean(diff))


def brier_score(y_true: Sequence[float | int], y_prob: Sequence[float]) -> float:
    """Compute Brier Score for binary probabilistic forecasts.

    BS = mean((y_prob - y_true)^2)
    """
    if len(y_true) != len(y_prob):
        raise ValueError("y_true and y_prob must have the same length")
    if len(y_true) == 0:
        return 0.0
    yt = np.array(y_true, dtype=float)
    yp = np.array(y_prob, dtype=float)
    return float(np.mean((yp - yt) ** 2))


def brier_skill_score(
    y_true: Sequence[float | int],
    y_prob: Sequence[float],
    y_clim_prob: float | None = None,
) -> float:
    """Compute Brier Skill Score against climatological reference.

    BSS = 1 - (BS / BS_ref)
    """
    if len(y_true) != len(y_prob):
        raise ValueError("y_true and y_prob must have the same length")
    if len(y_true) == 0:
        return 0.0

    yt = np.array(y_true, dtype=float)
    bs = brier_score(y_true, y_prob)

    if y_clim_prob is not None:
        p_ref = float(y_clim_prob)
    else:
        p_ref = float(np.mean(yt))

    bs_ref = float(np.mean((p_ref - yt) ** 2))

    if math.isclose(bs_ref, 0.0, abs_tol=1e-12):
        return 1.0 if math.isclose(bs, 0.0, abs_tol=1e-12) else 0.0

    return float(1.0 - (bs / bs_ref))


def heidke_skill_score(y_true: Sequence[float | int], y_pred: Sequence[float | int]) -> float:
    """Compute Heidke Skill Score (HSS) for binary forecasts.

    HSS = 2 * (a*d - b*c) / ((a+c)*(c+d) + (a+b)*(b+d))
    where:
      a: hit (true=1, pred=1)
      b: false alarm (true=0, pred=1)
      c: miss (true=1, pred=0)
      d: correct rejection (true=0, pred=0)
    """
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have the same length")
    if len(y_true) == 0:
        return 0.0

    yt = np.array(y_true, dtype=int)
    yp = np.array(y_pred, dtype=int)

    a = int(np.sum((yt == 1) & (yp == 1)))
    b = int(np.sum((yt == 0) & (yp == 1)))
    c = int(np.sum((yt == 1) & (yp == 0)))
    d = int(np.sum((yt == 0) & (yp == 0)))

    n = a + b + c + d
    if n == 0:
        return 0.0

    expected_correct = ((a + b) * (a + c) + (b + d) * (c + d)) / n
    denominator = n - expected_correct

    if math.isclose(denominator, 0.0, abs_tol=1e-12):
        return 0.0

    return float(((a + d) - expected_correct) / denominator)


def pr_auc(y_true: Sequence[float | int], y_prob: Sequence[float]) -> float:
    """Compute Area Under the Precision-Recall Curve (PR-AUC) using trapezoidal integration."""
    if len(y_true) != len(y_prob):
        raise ValueError("y_true and y_prob must have the same length")
    if len(y_true) == 0:
        return 0.0

    yt = np.array(y_true, dtype=int)
    yp = np.array(y_prob, dtype=float)

    total_positives = int(np.sum(yt == 1))
    if total_positives == 0 or total_positives == len(yt):
        return 1.0 if total_positives == len(yt) else 0.0

    # Sort descending by predicted probability
    desc_indices = np.argsort(-yp)
    yt_sorted = yt[desc_indices]
    yp_sorted = yp[desc_indices]

    # Find distinct thresholds
    distinct_value_indices = np.where(np.diff(yp_sorted))[0]
    threshold_idxs = np.concatenate([distinct_value_indices, [len(yp_sorted) - 1]])

    tps = np.cumsum(yt_sorted == 1)[threshold_idxs]
    fps = np.cumsum(yt_sorted == 0)[threshold_idxs]

    precisions = tps / (tps + fps)
    recalls = tps / total_positives

    # Prepend (precision=1.0, recall=0.0)
    precisions = np.concatenate([[1.0], precisions])
    recalls = np.concatenate([[0.0], recalls])

    # Trapezoidal integration along recall axis (supports NumPy 1.x and 2.x)
    trapezoid_func = getattr(np, "trapezoid", getattr(np, "trapz", None))
    if trapezoid_func is not None:
        auc = float(trapezoid_func(precisions, recalls))
    else:
        auc = float(np.sum((recalls[1:] - recalls[:-1]) * (precisions[1:] + precisions[:-1]) / 2.0))
    return max(0.0, min(1.0, auc))


def expected_calibration_error(
    y_true: Sequence[float | int],
    y_prob: Sequence[float],
    n_bins: int = 10,
) -> float:
    """Compute Expected Calibration Error (ECE) for probability predictions."""
    if len(y_true) != len(y_prob):
        raise ValueError("y_true and y_prob must have the same length")
    if len(y_true) == 0:
        return 0.0

    yt = np.array(y_true, dtype=float)
    yp = np.array(y_prob, dtype=float)
    n = len(yt)

    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0

    for i in range(n_bins):
        bin_lower = bin_edges[i]
        bin_upper = bin_edges[i + 1]

        if i == n_bins - 1:
            in_bin = (yp >= bin_lower) & (yp <= bin_upper)
        else:
            in_bin = (yp >= bin_lower) & (yp < bin_upper)

        bin_count = int(np.sum(in_bin))
        if bin_count > 0:
            bin_acc = float(np.mean(yt[in_bin]))
            bin_conf = float(np.mean(yp[in_bin]))
            ece += (bin_count / n) * abs(bin_acc - bin_conf)

    return float(ece)


def _parse_to_date(d: Any) -> dt.date:
    if isinstance(d, dt.datetime):
        return d.date()
    elif isinstance(d, dt.date):
        return d
    elif isinstance(d, str):
        cleaned = d.strip().split("T")[0].split(" ")[0]
        return dt.date.fromisoformat(cleaned)
    raise TypeError(f"Cannot parse date from {type(d)}: {d!r}")


def paired_block_bootstrap(
    y_true: Sequence[float],
    y_pred_model: Sequence[float],
    y_pred_baseline: Sequence[float],
    timestamps: Sequence[Any],
    metric_func: Callable[[Sequence[float], Sequence[float]], float],
    block_size_days: int = 7,
    n_bootstrap: int = 2000,
    seed: int = 42,
    ci: float = 0.95,
) -> dict[str, Any]:
    """Perform a paired block bootstrap on weekly blocks with a fixed seed.

    Computes the difference: delta = metric(model) - metric(baseline).
    Resamples entire weekly blocks with replacement to preserve temporal autocorrelation.

    Returns:
        dict with delta_mean, delta_std, ci_lower, ci_upper, ci_level, p_value, n_blocks, n_bootstrap
    """
    n = len(y_true)
    if not (n == len(y_pred_model) == len(y_pred_baseline) == len(timestamps)):
        raise ValueError("y_true, y_pred_model, y_pred_baseline, and timestamps must have identical lengths")

    if n == 0:
        return {
            "delta_mean": 0.0,
            "delta_std": 0.0,
            "ci_lower": 0.0,
            "ci_upper": 0.0,
            "ci_level": ci,
            "p_value": 1.0,
            "n_blocks": 0,
            "n_bootstrap": n_bootstrap,
        }

    # Group sample indices into temporal blocks (e.g., weekly)
    parsed_dates = [_parse_to_date(t) for t in timestamps]
    min_date = min(parsed_dates)

    block_map: dict[int, list[int]] = {}
    for idx, d in enumerate(parsed_dates):
        block_id = (d - min_date).days // block_size_days
        block_map.setdefault(block_id, []).append(idx)

    blocks = list(block_map.values())
    n_blocks = len(blocks)
    if n_blocks == 0:
        return {}

    # Seeded random generator
    rng = np.random.default_rng(seed)

    deltas: list[float] = []
    yt_arr = np.array(y_true)
    ym_arr = np.array(y_pred_model)
    yb_arr = np.array(y_pred_baseline)

    for _ in range(n_bootstrap):
        sampled_block_indices = rng.integers(0, n_blocks, size=n_blocks)
        sample_indices: list[int] = []
        for b_idx in sampled_block_indices:
            sample_indices.extend(blocks[b_idx])

        if not sample_indices:
            continue

        b_yt = yt_arr[sample_indices]
        b_ym = ym_arr[sample_indices]
        b_yb = yb_arr[sample_indices]

        m_score = metric_func(b_yt, b_ym)
        b_score = metric_func(b_yt, b_yb)
        deltas.append(float(m_score - b_score))

    deltas_arr = np.array(deltas)
    alpha = (1.0 - ci) / 2.0
    lower_pct = alpha * 100.0
    upper_pct = (1.0 - alpha) * 100.0

    ci_lower = float(np.percentile(deltas_arr, lower_pct))
    ci_upper = float(np.percentile(deltas_arr, upper_pct))
    delta_mean = float(np.mean(deltas_arr))
    delta_std = float(np.std(deltas_arr, ddof=1)) if len(deltas_arr) > 1 else 0.0

    # Two-sided empirical p-value for delta != 0
    # Proportion of bootstrap iterations crossing zero
    if delta_mean >= 0:
        p_val = float(2.0 * np.mean(deltas_arr <= 0))
    else:
        p_val = float(2.0 * np.mean(deltas_arr >= 0))
    p_val = min(1.0, max(0.0, p_val))

    return {
        "delta_mean": delta_mean,
        "delta_std": delta_std,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "ci_level": ci,
        "p_value": p_val,
        "n_blocks": n_blocks,
        "n_bootstrap": n_bootstrap,
    }


def bootstrap_sample_indices(n: int, n_bootstrap: int = 2000, seed: int = 42) -> list[list[int]]:
    """Generate bootstrap sample index arrays with a fixed seed. Permitted under Rule T1/N1 in ml/common/stats.py."""
    if n <= 0:
        return []
    rng = np.random.default_rng(seed)
    return [rng.integers(0, n, size=n).tolist() for _ in range(n_bootstrap)]
