"""Independent metric recompute implementation (Ticket R9.3).

Recomputes headline metrics from predictions_test.csv using a minimal,
separate standard-library implementation without relying on the training
framework or external libraries.

Enforces:
1. n_test in metrics.json equals row count in predictions_test.csv
2. Input file hashes in metrics.json match the files on disk
3. Headline metrics match recomputed values within 1e-9
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def _find_column(fieldnames: list[str], candidates: list[str]) -> str | None:
    for c in candidates:
        for f in fieldnames:
            if f.lower().strip() == c.lower():
                return f
    return None


def recompute_classification_metrics(rows: list[dict[str, str]], fieldnames: list[str]) -> dict[str, float]:
    y_true_col = _find_column(fieldnames, ["y_true", "true", "label", "actual", "true_intent", "ground_truth"])
    y_pred_col = _find_column(fieldnames, ["y_pred", "pred", "prediction", "predicted", "predicted_intent"])

    if not y_true_col or not y_pred_col:
        return {}

    n = len(rows)
    if n == 0:
        return {"accuracy": 0.0}

    correct = 0
    classes = set()
    tp_per_class: dict[str, int] = {}
    fp_per_class: dict[str, int] = {}
    fn_per_class: dict[str, int] = {}

    for r in rows:
        t = str(r[y_true_col]).strip()
        p = str(r[y_pred_col]).strip()
        classes.add(t)
        classes.add(p)
        if t == p:
            correct += 1
            tp_per_class[t] = tp_per_class.get(t, 0) + 1
        else:
            fp_per_class[p] = fp_per_class.get(p, 0) + 1
            fn_per_class[t] = fn_per_class.get(t, 0) + 1

    accuracy = correct / n
    metrics: dict[str, float] = {"accuracy": accuracy}

    # Macro F1
    f1s = []
    for c in sorted(classes):
        tp = tp_per_class.get(c, 0)
        fp = fp_per_class.get(c, 0)
        fn = fn_per_class.get(c, 0)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        f1s.append(f1)

    if f1s:
        metrics["macro_f1"] = sum(f1s) / len(f1s)

    return metrics


def recompute_regression_metrics(rows: list[dict[str, str]], fieldnames: list[str]) -> dict[str, float]:
    y_true_col = _find_column(fieldnames, ["y_true", "true", "obs", "observed", "actual", "tmax_true", "rain_true"])
    y_pred_col = _find_column(fieldnames, ["y_pred", "pred", "predicted", "prediction", "tmax_pred", "rain_pred"])

    if not y_true_col or not y_pred_col:
        return {}

    n = len(rows)
    if n == 0:
        return {}

    errors = []
    for r in rows:
        try:
            t = float(r[y_true_col])
            p = float(r[y_pred_col])
            errors.append(p - t)
        except (ValueError, TypeError):
            continue

    if not errors:
        return {}

    k = len(errors)
    mae = sum(abs(e) for e in errors) / k
    rmse = math.sqrt(sum(e * e for e in errors) / k)
    bias = sum(errors) / k

    return {
        "mae": mae,
        "rmse": rmse,
        "bias": bias,
    }


def verify_model_metrics(
    model_dir: Path | str,
    root_dir: Path = ROOT,
    tolerance: float = 1e-9,
) -> dict[str, Any]:
    """Verify metrics for a model directory.

    Requires:
    - predictions_test.csv
    - reports/metrics.json or metrics.json
    """
    model_path = Path(model_dir) if isinstance(model_dir, Path) else root_dir / "ml" / model_dir
    model_name = model_path.name

    # 1. Locate predictions_test.csv
    pred_candidates = [
        model_path / "predictions_test.csv",
        model_path / "reports" / "predictions_test.csv",
    ]
    pred_file = next((p for p in pred_candidates if p.exists()), None)
    if not pred_file:
        return {
            "model": model_name,
            "status": "not_trained",
            "message": f"No predictions_test.csv found in {model_path}",
        }

    # 2. Locate metrics.json
    metrics_candidates = [
        model_path / "reports" / "metrics.json",
        model_path / "metrics.json",
    ]
    metrics_file = next((p for p in metrics_candidates if p.exists()), None)
    if not metrics_file:
        raise FileNotFoundError(f"metrics.json missing for model {model_name} in {model_path}")

    # 3. Read and verify predictions_test.csv
    with pred_file.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    n_test = len(rows)

    # 4. Read metrics.json
    with metrics_file.open("r", encoding="utf-8") as f:
        metrics_data = json.load(f)

    # Verify n_test
    if "n_test" in metrics_data:
        claimed_n = int(metrics_data["n_test"])
        if claimed_n != n_test:
            raise ValueError(
                f"Row count mismatch in {model_name}: metrics.json claimed n_test={claimed_n}, "
                f"but predictions_test.csv has {n_test} rows."
            )

    # Verify input hashes if present
    if "inputs" in metrics_data and isinstance(metrics_data["inputs"], list):
        for item in metrics_data["inputs"]:
            if isinstance(item, dict) and "path" in item and "sha256" in item:
                inp_file = root_dir / item["path"]
                if inp_file.exists():
                    computed = hashlib.sha256(inp_file.read_bytes()).hexdigest()
                    if computed.lower() != item["sha256"].lower():
                        raise ValueError(
                            f"Input hash mismatch for {item['path']} in {model_name}: "
                            f"claimed {item['sha256']}, actual {computed}"
                        )

    # 5. Recompute headline metrics
    cls_metrics = recompute_classification_metrics(rows, fieldnames)
    reg_metrics = recompute_regression_metrics(rows, fieldnames)
    recomputed = {**cls_metrics, **reg_metrics}

    if not recomputed:
        raise ValueError(f"Could not identify y_true and y_pred columns in {pred_file}")

    # Check matches within tolerance
    verified_metrics = {}
    for metric_name, computed_val in recomputed.items():
        if metric_name in metrics_data:
            claimed_val = float(metrics_data[metric_name])
            diff = abs(claimed_val - computed_val)
            if diff >= tolerance:
                raise ValueError(
                    f"Metric recompute mismatch for {model_name}.{metric_name}: "
                    f"claimed {claimed_val}, recomputed {computed_val} (diff: {diff:.2e} >= {tolerance})"
                )
            verified_metrics[metric_name] = computed_val

    return {
        "model": model_name,
        "status": "verified",
        "n_test": n_test,
        "verified_metrics": verified_metrics,
        "recomputed_all": recomputed,
    }
