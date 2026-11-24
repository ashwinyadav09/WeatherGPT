"""Unit tests for ML foundation common library (Ticket R10.1).

Tests every function in ml.common using hand-calculated cases:
- ml.common.manifest: download helper, row counter, error raising, manifest verification
- ml.common.splits: chronological split with embargo, rolling-origin folds
- ml.common.stats: MAE, RMSE, bias, Brier, BSS, HSS, PR-AUC, ECE, paired block bootstrap
- ml.common.report: MODEL_CARD.md rendering and missing field enforcement
"""
from __future__ import annotations

import datetime as dt
import math
from pathlib import Path
from typing import Any

import httpx
import pytest

from ml.common.manifest import (
    count_file_rows,
    download_and_record_manifest,
    verify_manifest,
)
from ml.common.report import render_model_card
from ml.common.splits import (
    chronological_split,
    rolling_origin_folds,
)
from ml.common.stats import (
    brier_score,
    brier_skill_score,
    expected_calibration_error,
    heidke_skill_score,
    mean_absolute_error,
    mean_bias_error,
    paired_block_bootstrap,
    pr_auc,
    root_mean_squared_error,
)

# ---------------------------------------------------------------------------
# ml.common.manifest tests
# ---------------------------------------------------------------------------


def test_count_file_rows(tmp_path: Path) -> None:
    # 1. CSV with header + 3 rows
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("id,val\n1,10\n2,20\n3,30\n", encoding="utf-8")
    assert count_file_rows(csv_file) == 3

    # 2. JSON list with 4 items
    json_list_file = tmp_path / "data.json"
    json_list_file.write_text('[{"a": 1}, {"a": 2}, {"a": 3}, {"a": 4}]', encoding="utf-8")
    assert count_file_rows(json_list_file) == 4

    # 3. JSON lines with 2 records
    jsonl_file = tmp_path / "data.jsonl"
    jsonl_file.write_text('{"a": 1}\n{"a": 2}\n', encoding="utf-8")
    assert count_file_rows(jsonl_file) == 2

    # 4. Non-existent file
    assert count_file_rows(tmp_path / "missing.csv") == 0


def test_download_and_record_manifest_success(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="col1,col2\n10,20\n30,40\n", headers={"content-type": "text/csv"})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    dest_file = tmp_path / "data" / "source.csv"
    manifest_file = tmp_path / "data" / "MANIFEST.json"

    rec = download_and_record_manifest(
        url="https://example.com/api/weather",
        output_path=dest_file,
        params={"city": "Delhi"},
        manifest_path=manifest_file,
        client=client,
    )

    assert dest_file.exists()
    assert manifest_file.exists()
    assert rec["url"] == "https://example.com/api/weather"
    assert rec["parameters"] == {"city": "Delhi"}
    assert rec["rows"] == 2
    assert rec["bytes"] == len("col1,col2\n10,20\n30,40\n")
    assert len(rec["sha256"]) == 64

    # Manifest verification helper
    assert verify_manifest(manifest_file, dest_file) is True


def test_download_and_record_manifest_raises_on_http_error(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    dest_file = tmp_path / "fail.csv"
    with pytest.raises(httpx.HTTPStatusError):
        download_and_record_manifest(
            url="https://example.com/api/missing",
            output_path=dest_file,
            client=client,
        )

    # File must not be created on error
    assert not dest_file.exists()


# ---------------------------------------------------------------------------
# ml.common.splits tests
# ---------------------------------------------------------------------------


def test_chronological_split_with_embargo() -> None:
    # 10 daily dates: 2024-01-01 through 2024-01-10
    dates = [f"2024-01-{i:02d}" for i in range(1, 11)]

    # test_fraction = 0.3 -> test size = 3 (indices 7, 8, 9 -> 2024-01-08, 09, 10)
    # test starts on 2024-01-08.
    # With embargo_days = 2: embargo cutoff is 2024-01-08 - 2 days = 2024-01-06.
    # Train dates must be <= 2024-01-06 (indices 0, 1, 2, 3, 4, 5).
    # Date 2024-01-07 (index 6) falls within the embargo window and must be dropped.
    train_idx, test_idx = chronological_split(dates, test_fraction=0.3, embargo_days=2)

    assert test_idx == [7, 8, 9]
    assert train_idx == [0, 1, 2, 3, 4, 5]
    assert 6 not in train_idx  # index 6 (2024-01-07) dropped by embargo
    assert 6 not in test_idx


def test_chronological_split_empty() -> None:
    train_idx, test_idx = chronological_split([])
    assert train_idx == []
    assert test_idx == []


def test_rolling_origin_folds() -> None:
    # 60 daily observations
    base_date = dt.date(2024, 1, 1)
    dates = [base_date + dt.timedelta(days=i) for i in range(60)]

    folds = rolling_origin_folds(
        dates,
        n_splits=3,
        min_train_days=20,
        test_days=7,
        embargo_days=3,
    )

    assert len(folds) >= 1
    for train_idx, test_idx in folds:
        assert len(train_idx) > 0
        assert len(test_idx) > 0

        max_train_date = max(dates[i] for i in train_idx)
        min_test_date = min(dates[i] for i in test_idx)

        # Embargo buffer strictly respected: test_start - train_end >= embargo_days
        assert (min_test_date - max_train_date).days >= 3


def test_rolling_origin_folds_raises_on_insufficient_span() -> None:
    dates = [dt.date(2024, 1, 1) + dt.timedelta(days=i) for i in range(10)]
    with pytest.raises(ValueError, match="Dataset span"):
        rolling_origin_folds(dates, min_train_days=30, test_days=7, embargo_days=7)


# ---------------------------------------------------------------------------
# ml.common.stats tests (hand-calculated values)
# ---------------------------------------------------------------------------


def test_mean_absolute_error_hand_calculated() -> None:
    y_true = [10.0, 20.0, 30.0]
    y_pred = [12.0, 19.0, 35.0]
    # |12-10| = 2, |19-20| = 1, |35-30| = 5. Mean = 8/3
    expected = 8.0 / 3.0
    assert math.isclose(mean_absolute_error(y_true, y_pred), expected, rel_tol=1e-9)


def test_root_mean_squared_error_hand_calculated() -> None:
    y_true = [10.0, 20.0, 30.0]
    y_pred = [12.0, 19.0, 35.0]
    # Diffs: [2, -1, 5]. Squared: [4, 1, 25] = 30. Mean = 10. RMSE = sqrt(10)
    expected = math.sqrt(10.0)
    assert math.isclose(root_mean_squared_error(y_true, y_pred), expected, rel_tol=1e-9)


def test_mean_bias_error_hand_calculated() -> None:
    y_true = [10.0, 20.0, 30.0]
    y_pred = [12.0, 19.0, 35.0]
    # Diffs: [12-10, 19-20, 35-30] = [2, -1, 5] -> Sum = 6. Mean = 2.0
    assert math.isclose(mean_bias_error(y_true, y_pred), 2.0, rel_tol=1e-9)


def test_brier_score_hand_calculated() -> None:
    y_true = [1, 0, 1]
    y_prob = [0.8, 0.2, 0.6]
    # Diffs: [0.8-1, 0.2-0, 0.6-1] = [-0.2, 0.2, -0.4]
    # Squared: [0.04, 0.04, 0.16] = 0.24. Mean = 0.08
    assert math.isclose(brier_score(y_true, y_prob), 0.08, rel_tol=1e-9)


def test_brier_skill_score_hand_calculated() -> None:
    y_true = [1, 0, 1, 0]
    y_prob = [0.9, 0.1, 0.8, 0.2]
    # Climatology mean = 0.5. BS_ref = (0.5-1)^2 * 2 + (0.5-0)^2 * 2 / 4 = 0.25
    # BS = (0.1^2 + 0.1^2 + 0.2^2 + 0.2^2) / 4 = (0.01 + 0.01 + 0.04 + 0.04) / 4 = 0.10 / 4 = 0.025
    # BSS = 1 - (0.025 / 0.25) = 1 - 0.10 = 0.90
    bss = brier_skill_score(y_true, y_prob)
    assert math.isclose(bss, 0.90, rel_tol=1e-9)


def test_heidke_skill_score_hand_calculated() -> None:
    # Contingency table:
    # a (hits): 20
    # b (false alarms): 5
    # c (misses): 5
    # d (correct rejections): 70
    # Total n = 100
    # Expected correct = ((a+b)*(a+c) + (b+d)*(c+d)) / n
    # = (25 * 25 + 75 * 75) / 100 = (625 + 5625) / 100 = 62.5
    # HSS = ((20 + 70) - 62.5) / (100 - 62.5) = 27.5 / 37.5 = 11/15 = 0.7333333333333333
    y_true = [1] * 20 + [0] * 5 + [1] * 5 + [0] * 70
    y_pred = [1] * 20 + [1] * 5 + [0] * 5 + [0] * 70
    hss = heidke_skill_score(y_true, y_pred)
    assert math.isclose(hss, 11.0 / 15.0, rel_tol=1e-9)


def test_pr_auc_perfect_predictions() -> None:
    y_true = [1, 1, 0, 0]
    y_prob = [0.9, 0.8, 0.2, 0.1]
    auc = pr_auc(y_true, y_prob)
    assert math.isclose(auc, 1.0, rel_tol=1e-5)


def test_expected_calibration_error_hand_calculated() -> None:
    # 2 bins: [0, 0.5) and [0.5, 1.0]
    # Bin 1: prob=0.2, true=0 -> conf=0.2, acc=0.0 -> diff=0.2
    # Bin 2: prob=0.8, true=1 -> conf=0.8, acc=1.0 -> diff=0.2
    # Total ECE = 0.5 * 0.2 + 0.5 * 0.2 = 0.2
    y_true = [0, 1]
    y_prob = [0.2, 0.8]
    ece = expected_calibration_error(y_true, y_prob, n_bins=2)
    assert math.isclose(ece, 0.2, rel_tol=1e-9)


def test_paired_block_bootstrap_weekly() -> None:
    # 28 days of data (4 weekly blocks)
    base_d = dt.date(2024, 1, 1)
    timestamps = [base_d + dt.timedelta(days=i) for i in range(28)]
    y_true = [10.0 + i * 0.5 for i in range(28)]
    # Model has small error (diff = 0.5) -> MAE = 0.5
    y_model = [y + 0.5 for y in y_true]
    # Baseline has larger error (diff = 2.0) -> MAE = 2.0
    y_base = [y + 2.0 for y in y_true]

    res = paired_block_bootstrap(
        y_true=y_true,
        y_pred_model=y_model,
        y_pred_baseline=y_base,
        timestamps=timestamps,
        metric_func=mean_absolute_error,
        block_size_days=7,
        n_bootstrap=100,
        seed=42,
    )

    assert "delta_mean" in res
    assert "ci_lower" in res
    assert "ci_upper" in res
    assert "p_value" in res
    # Model MAE (0.5) - Baseline MAE (2.0) = -1.5
    assert math.isclose(res["delta_mean"], -1.5, abs_tol=1e-5)
    assert res["ci_lower"] <= res["delta_mean"] <= res["ci_upper"]


# ---------------------------------------------------------------------------
# ml.common.report tests
# ---------------------------------------------------------------------------


def test_render_model_card_success(tmp_path: Path) -> None:
    data: dict[str, Any] = {
        "model_name": "BiasCorrection_MOS_v1",
        "version": "1.0.0",
        "task": "Point-forecast 2m temperature post-processing",
        "dataset": {
            "name": "IMD Open-Meteo ERA5 Reanalysis",
            "source": "Open-Meteo API",
            "split_date_range": "2020-01-01 to 2024-06-30",
        },
        "n_train": 1000,
        "n_test": 200,
        "metrics": {"mae": 0.85, "rmse": 1.12, "bias": -0.05},
        "baseline_comparison": {
            "mae": {
                "baseline": 1.50,
                "model": 0.85,
                "delta": -0.65,
                "ci_lower": -0.72,
                "ci_upper": -0.58,
                "p_value": 0.001,
            }
        },
        "limitations": ["Requires at least 30 days of recent station data"],
        "generated_by": "ml/bias_correction/train.py",
        "git_sha": "abcdef1234567890abcdef1234567890abcdef12",
        "provenance": "recorded_real_http",
    }

    out_file = tmp_path / "MODEL_CARD.md"
    rendered = render_model_card(data, output_path=out_file)

    assert out_file.exists()
    assert "# Model Card: BiasCorrection_MOS_v1" in rendered
    assert "0.8500" in rendered
    assert "recorded_real_http" in rendered
    assert "-0.65" in rendered


def test_render_model_card_fails_strictly_on_missing_field() -> None:
    incomplete_data = {
        "model_name": "IncompleteModel",
        "version": "0.1.0",
        # Missing required task, dataset, n_train, n_test, metrics, etc.
    }
    with pytest.raises(ValueError, match="Missing required field"):
        render_model_card(incomplete_data)
