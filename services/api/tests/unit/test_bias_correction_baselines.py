"""Unit tests verifying all baselines for bias correction (Ticket R20.6 / ADR 0011).

Enforces:
1. Baselines are all real and distinct:
   - Best single raw model (ECMWF IFS 0.25°)
   - Multi-model mean (average of GFS, ECMWF, ICON)
   - Persistence (previous day's observed Tmax: T_obs(d-1))
   - Trailing 30-day mean-error correction (raw MMM - trailing 30d mean bias)
   - Station-day-of-year climatology computed strictly from training years only
2. Test asserts that climatology and multi-model mean are computed by different code
   and produce distinct values.
"""
from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np
import pandas as pd

from ml.bias_correction.dataset import (
    build_processed_dataset,
    get_three_way_splits,
    load_dataset,
)


def test_climatology_and_mmm_computed_by_different_code() -> None:
    """Explicitly verify that climatology and multi-model mean are computed by different code (R20.6)."""
    from ml.bias_correction.dataset import _parse_previous_runs_file

    source_build = inspect.getsource(build_processed_dataset)
    source_nwp = inspect.getsource(_parse_previous_runs_file)

    # Multi-model mean is computed in NWP parsing by averaging model forecasts
    assert "mmm_tmax = sum(tmax_vals) / len(tmax_vals)" in source_nwp

    # Climatology is computed from station observations in the training window
    assert "climatology_table" in source_build
    assert "TRAIN_START_DATE <= d_str <= TRAIN_END_DATE" in source_build
    assert "train_st_doy_sums" in source_build

    # Assert they use completely different logic:
    # NWP uses model forecast fields, whereas climatology uses observed METAR Tmax by DOY
    assert "observed_tmax" not in source_nwp
    assert "sum(tmax_vals) / len(tmax_vals)" not in source_build


def test_baselines_distinct_on_dataset() -> None:
    """Verify that all five baselines produce real, distinct values across the dataset."""
    pred_path = Path("ml/bias_correction/reports/predictions_test.csv")
    if pred_path.exists():
        df = pd.read_csv(pred_path)
        assert len(df) >= 400, "Must have at least 400 test samples per Rule S1"
        y_true = df["y_true"].to_numpy()
        y_gfs = df["tmax_gfs"].to_numpy()
        y_ecmwf = df["tmax_ecmwf"].to_numpy()
        y_icon = df["tmax_icon"].to_numpy()
        y_mmm = df["multi_model_mean"].to_numpy()
        y_persist = df["persistence"].to_numpy()
        y_trailing = df["trailing_30d_correction"].to_numpy()
        y_clim = df["climatology"].to_numpy()
    else:
        rows = load_dataset()
        train_rows, val_rows, test_rows = get_three_way_splits(rows)
        assert len(test_rows) >= 400, "Must have at least 400 test samples per Rule S1"
        y_true = np.array([r["observed_tmax"] for r in test_rows])
        y_gfs = np.array([r["tmax_gfs"] for r in test_rows])
        y_ecmwf = np.array([r["tmax_ecmwf"] for r in test_rows])
        y_icon = np.array([r["tmax_icon"] for r in test_rows])
        y_mmm = np.array([r["tmax_mmm"] for r in test_rows])
        y_persist = np.array([r["persistence_tmax"] for r in test_rows])
        y_trailing = np.array([r["tmax_mmm"] - r["trailing_30d_bias"] for r in test_rows])
        y_clim = np.array([r["climatology_tmax"] for r in test_rows])

    mae_gfs = float(np.mean(np.abs(y_gfs - y_true)))
    mae_ecmwf = float(np.mean(np.abs(y_ecmwf - y_true)))
    mae_icon = float(np.mean(np.abs(y_icon - y_true)))
    mae_mmm = float(np.mean(np.abs(y_mmm - y_true)))
    mae_persist = float(np.mean(np.abs(y_persist - y_true)))
    mae_trailing = float(np.mean(np.abs(y_trailing - y_true)))
    mae_clim = float(np.mean(np.abs(y_clim - y_true)))

    print("\nTest Block Baseline MAEs:")
    print(f"  GFS: {mae_gfs:.4f}")
    print(f"  ECMWF (best raw): {mae_ecmwf:.4f}")
    print(f"  ICON: {mae_icon:.4f}")
    print(f"  Multi-model mean: {mae_mmm:.4f}")
    print(f"  Persistence: {mae_persist:.4f}")
    print(f"  Trailing 30d bias correction: {mae_trailing:.4f}")
    print(f"  Station-DOY Climatology: {mae_clim:.4f}")

    # Climatology and MMM must NOT be identical (resolves Finding V7)
    assert abs(mae_clim - mae_mmm) > 5 / 100, f"Climatology ({mae_clim}) and MMM ({mae_mmm}) must be distinct"
    assert not np.allclose(y_clim, y_mmm), "Climatology and MMM predictions must not be identical"

    # Persistence must be distinct from MMM and Climatology
    assert abs(mae_persist - mae_mmm) > 1 / 100
    assert abs(mae_persist - mae_clim) > 5 / 100
    assert not np.allclose(y_persist, y_mmm)

    # Trailing 30d correction must be distinct from raw MMM
    assert not np.allclose(y_trailing, y_mmm)
