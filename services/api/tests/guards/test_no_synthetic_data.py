from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]

SCAN_DIRS = ["ml", "eval", "scripts/tasks"]
FORBIDDEN_WORDS = ["simulate", "synthetic", "surrogate", "canned"]

METRIC_NAME_RE = re.compile(
    r"^(.*_)?(accuracy|f1|mae|rmse|wer|latency|uptime|faithfulness|kappa|recall|precision|mrr|brier|skill)(_.*)?$",
    re.IGNORECASE,
)
BUDGET_CONST_RE = re.compile(
    r"^(min|max)_(accuracy|f1|mae|rmse|wer|latency|uptime|faithfulness|kappa|recall|precision|mrr|brier|skill).*$",
    re.IGNORECASE,
)


def _get_docstring_nodes(tree: ast.AST) -> set[ast.AST]:
    """Collect docstring string constant nodes to exempt them from word checks."""
    docstrings: set[ast.AST] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                docstrings.add(node.body[0].value)
    return docstrings


def scan_source_for_synthetic_data(source_code: str, filename: str = "<string>") -> list[str]:
    """Scan python source AST for forbidden imports, forbidden literals, hard-coded metrics, and budget constants.

    Except ml/common/stats.py which is allowed to use a seeded bootstrap.
    """
    if "ml/common/stats.py" in filename.replace("\\", "/"):
        return []

    try:
        tree = ast.parse(source_code, filename=filename)
    except SyntaxError as exc:
        return [f"{filename}:{exc.lineno}: SyntaxError: {exc.msg}"]

    docstrings = _get_docstring_nodes(tree)
    violations: list[str] = []

    for node in ast.walk(tree):
        lineno = getattr(node, "lineno", 0)

        # 1. Imports: random, faker, numpy.random
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name.lower()
                if name == "random" or name == "faker" or name.startswith("numpy.random"):
                    violations.append(
                        f"{filename}:{lineno}: Forbidden import '{alias.name}'. Rule T1 / R9.1: No random/synthetic generators."
                    )
        elif isinstance(node, ast.ImportFrom):
            mod = (node.module or "").lower()
            if mod == "random" or mod == "faker" or mod.startswith("numpy.random"):
                violations.append(
                    f"{filename}:{lineno}: Forbidden import from '{node.module}'. Rule T1 / R9.1: No random/synthetic generators."
                )

        # 2. String literals containing simulate, synthetic, surrogate, canned
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node not in docstrings:
                val_lower = node.value.lower()
                for word in FORBIDDEN_WORDS:
                    if word in val_lower:
                        violations.append(
                            f"{filename}:{lineno}: Forbidden string literal containing '{word}': {node.value!r}"
                        )

        # 3. Hard-coded numeric metric assignments & budget constants
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            val = node.value
            if isinstance(val, ast.Constant) and isinstance(val.value, (int, float)):
                for t in targets:
                    if isinstance(t, ast.Name):
                        if BUDGET_CONST_RE.match(t.id):
                            violations.append(
                                f"{filename}:{lineno}: Forbidden budget constant '{t.id} = {val.value}'. Rule T5: No min/max budget bounds on measured results."
                            )
                        elif METRIC_NAME_RE.match(t.id):
                            violations.append(
                                f"{filename}:{lineno}: Hard-coded metric literal assigned to '{t.id} = {val.value}'. Metrics must be computed from real data."
                            )

    return violations


def scan_file(path: Path) -> list[str]:
    rel_path = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return [f"{rel_path}: ReadError: {exc}"]
    return scan_source_for_synthetic_data(content, filename=rel_path)


def test_no_synthetic_data_in_codebase() -> None:
    """R9.1: AST-scan ml/**, eval/**, scripts/tasks/** for synthetic data, forbidden imports, and hard-coded metrics."""
    all_violations: list[str] = []
    scanned_count = 0

    for d in SCAN_DIRS:
        dir_path = ROOT / d
        if not dir_path.exists():
            continue
        for py_path in dir_path.rglob("*.py"):
            scanned_count += 1
            all_violations.extend(scan_file(py_path))

    assert scanned_count > 0, f"Expected python files to scan in {SCAN_DIRS}"
    assert not all_violations, (
        f"Static guard violations found ({len(all_violations)}):\n" + "\n".join(all_violations)
    )


def test_guard_catches_import_random_in_temp_file(tmp_path: Path) -> None:
    """Done when proof: deliberately inserting 'import random' into ml/intent/data.py makes guard fail."""
    test_file = tmp_path / "ml" / "intent" / "data.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("import random\n\ndef sample():\n    return random.random()\n", encoding="utf-8")
    violations = scan_file(test_file)
    assert any("import 'random'" in v for v in violations)


def test_guard_catches_hardcoded_accuracy_in_temp_file(tmp_path: Path) -> None:
    """Done when proof: deliberately inserting 'accuracy = 0.97' makes the guard fail."""
    test_file = tmp_path / "mock_eval.py"
    test_file.write_text("def compute():\n    accuracy = 0.97\n    return accuracy\n", encoding="utf-8")
    violations = scan_file(test_file)
    assert any("Hard-coded metric literal assigned to 'accuracy = 0.97'" in v for v in violations)


def test_guard_catches_synthetic_string_literal(tmp_path: Path) -> None:
    """Done when proof: deliberately inserting forbidden words like 'synthetic' makes guard fail."""
    test_file = tmp_path / "mock_source.py"
    test_file.write_text("data_mode = 'synthetic_test_data'\n", encoding="utf-8")
    violations = scan_file(test_file)
    assert any("Forbidden string literal containing 'synthetic'" in v for v in violations)


def test_guard_catches_budget_constant_rule_t5(tmp_path: Path) -> None:
    """Done when proof: assigning min_accuracy budget bound fails rule T5."""
    test_file = tmp_path / "mock_budget.py"
    test_file.write_text("min_accuracy_threshold = 0.85\n", encoding="utf-8")
    violations = scan_file(test_file)
    assert any("Forbidden budget constant" in v for v in violations)


def test_guard_allows_seeded_bootstrap_in_ml_common_stats(tmp_path: Path) -> None:
    """Stats module ml/common/stats.py is permitted for block bootstrap resamples."""
    stats_file = tmp_path / "ml" / "common" / "stats.py"
    stats_file.parent.mkdir(parents=True, exist_ok=True)
    stats_file.write_text("import numpy.random\n\ndef bootstrap(): pass\n", encoding="utf-8")
    violations = scan_file(stats_file)
    assert violations == []


def test_editing_number_in_metrics_json_causes_recompute_failure(tmp_path: Path) -> None:
    """Done when proof: editing a number in metrics.json causes verify_model_metrics to fail."""
    from ml.common.recompute import verify_model_metrics

    model_dir = tmp_path / "ml" / "intent"
    reports_dir = model_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Real predictions CSV with 4 samples: 3 correct -> accuracy = 0.75
    pred_csv = reports_dir / "predictions_test.csv"
    pred_csv.write_text(
        "y_true,y_pred\n"
        "weather_query,weather_query\n"
        "weather_query,weather_query\n"
        "weather_query,weather_query\n"
        "weather_query,crop_advisory\n",
        encoding="utf-8",
    )

    # Deliberately falsified / edited metrics.json (accuracy edited to 0.97)
    metrics_json = reports_dir / "metrics.json"
    metrics_json.write_text(
        '{"accuracy": 0.97, "n_test": 4}\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"Metric recompute mismatch for intent\.accuracy: claimed 0\.97, recomputed 0\.75"):
        verify_model_metrics(model_dir=model_dir, root_dir=tmp_path)


def test_editing_row_count_in_metrics_json_causes_failure(tmp_path: Path) -> None:
    """Done when proof: editing n_test in metrics.json causes row count mismatch failure."""
    from ml.common.recompute import verify_model_metrics

    model_dir = tmp_path / "ml" / "bias_correction"
    reports_dir = model_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    pred_csv = reports_dir / "predictions_test.csv"
    pred_csv.write_text("y_true,y_pred\n10.0,10.1\n", encoding="utf-8")

    metrics_json = reports_dir / "metrics.json"
    metrics_json.write_text('{"mae": 0.1, "n_test": 100}\n', encoding="utf-8")

    with pytest.raises(ValueError, match=r"Row count mismatch"):
        verify_model_metrics(model_dir=model_dir, root_dir=tmp_path)


def test_auditing_falsified_hash_causes_audit_failure(tmp_path: Path) -> None:
    """Done when proof: editing an input file without updating sha256 fails audit."""
    from scripts.tasks.audit_results import audit_json_file

    input_file = tmp_path / "data.csv"
    input_file.write_text("col1,col2\n1,2\n", encoding="utf-8")

    # Script file that exists
    script_file = tmp_path / "scripts" / "train.py"
    script_file.parent.mkdir(parents=True, exist_ok=True)
    script_file.write_text("# train\n", encoding="utf-8")

    result_json = tmp_path / "result.json"
    result_json.write_text(
        json.dumps({
            "generated_by": "scripts/train.py",
            "git_sha": "0000000000000000000000000000000000000000",
            "provenance": "live_api",
            "inputs": [{"path": "data.csv", "sha256": "0" * 64}],
        }),
        encoding="utf-8",
    )

    errors = audit_json_file(result_json, root_dir=tmp_path)
    assert any("sha256 mismatch" in err or "git_sha" in err for err in errors)
