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
DICT_METRIC_KEY_RE = re.compile(
    r"^(.*_)?(mean|ci_lower|ci_upper|accuracy|latency|speedup|significant|passed|ok|f1|recall|precision|mrr|brier|wer|kappa|rate)(_.*)?$",
    re.IGNORECASE,
)

ALLOWLIST_PATH = Path(__file__).resolve().parent / "float_allowlist.json"
_FLOAT_ALLOWLIST: set[tuple[str, float]] | None = None


def get_float_allowlist() -> set[tuple[str, float]]:
    global _FLOAT_ALLOWLIST
    if _FLOAT_ALLOWLIST is None:
        _FLOAT_ALLOWLIST = set()
        if ALLOWLIST_PATH.exists():
            try:
                data = json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))
                for item in data:
                    f = str(item.get("file", "")).replace("\\", "/").lstrip("./")
                    v = item.get("value")
                    if isinstance(v, (int, float)):
                        _FLOAT_ALLOWLIST.add((f, round(float(v), 6)))
                        _FLOAT_ALLOWLIST.add((Path(f).name, round(float(v), 6)))
            except Exception:
                pass
    return _FLOAT_ALLOWLIST


def _is_random_attribute(node: ast.AST) -> bool:
    """Check if an AST node is an attribute access containing 'random' or 'default_rng'."""
    if isinstance(node, ast.Attribute):
        if node.attr in {"random", "default_rng"}:
            return True
        curr = node.value
        while isinstance(curr, ast.Attribute):
            if curr.attr in {"random", "default_rng"}:
                return True
            curr = curr.value
        if isinstance(curr, ast.Name) and curr.id in {"random", "default_rng"}:
            return True
    elif isinstance(node, ast.Name) and node.id == "default_rng":
        return True
    return False


def _is_numeric_expr(node: ast.AST) -> bool:
    """Check if an AST node is a numeric literal or unary/binary numeric expression."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return True
    if isinstance(node, ast.UnaryOp) and _is_numeric_expr(node.operand):
        return True
    if isinstance(node, ast.BinOp) and (_is_numeric_expr(node.left) or _is_numeric_expr(node.right)):
        return True
    return False


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
    norm_filename = filename.replace("\\", "/").lstrip("./")
    if "ml/common/stats.py" in norm_filename:
        return []

    try:
        tree = ast.parse(source_code, filename=filename)
    except SyntaxError as exc:
        return [f"{filename}:{exc.lineno}: SyntaxError: {exc.msg}"]

    docstrings = _get_docstring_nodes(tree)
    violations: list[str] = []
    is_eval_or_task = "eval/" in norm_filename or "scripts/tasks/" in norm_filename
    is_result_code = is_eval_or_task or "eval.py" in norm_filename
    allowlist = get_float_allowlist()

    for node in ast.walk(tree):
        lineno = getattr(node, "lineno", 0)

        # 1. Imports and attribute chains: random, faker, numpy.random, default_rng
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
        elif _is_random_attribute(node):
            violations.append(
                f"{filename}:{lineno}: Forbidden attribute chain containing random/default_rng. Rule R20.2 #1."
            )

        # 2. numpy.ones, zeros, full, ones_like, zeros_like in eval/** and scripts/tasks/**
        elif is_eval_or_task and isinstance(node, ast.Call):
            func_name = ""
            if isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            elif isinstance(node.func, ast.Name):
                func_name = node.func.id
            if func_name in {"ones", "zeros", "full", "ones_like", "zeros_like"}:
                violations.append(
                    f"{filename}:{lineno}: Forbidden constant array generator 'np.{func_name}' in evaluation/benchmark script. Rule R20.2 #2."
                )

        # 3. String literals containing simulate, synthetic, surrogate, canned
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node not in docstrings:
                val_lower = node.value.lower()
                for word in FORBIDDEN_WORDS:
                    if word in val_lower:
                        violations.append(
                            f"{filename}:{lineno}: Forbidden string literal containing '{word}': {node.value!r}"
                        )

        # 4. Hard-coded numeric metric assignments & budget constants
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

        # 5. Non-integer float literals not in float_allowlist.json
        if isinstance(node, ast.Constant) and isinstance(node.value, float) and not node.value.is_integer():
            val = round(node.value, 6)
            clean_base = Path(norm_filename).name
            if not any(
                (entry_file == norm_filename or entry_file == clean_base or norm_filename.endswith(entry_file))
                and round(entry_val, 6) == val
                for entry_file, entry_val in allowlist
            ):
                violations.append(
                    f"{filename}:{lineno}: Non-integer float literal {node.value} not found in float_allowlist.json. Rule R20.2 #3."
                )

        # 6. Numeric or boolean literals in dict displays whose key matches metric names
        elif isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    if DICT_METRIC_KEY_RE.match(k.value):
                        if isinstance(v, ast.Constant) and isinstance(v.value, (int, float, bool)):
                            violations.append(
                                f"{filename}:{lineno}: Hard-coded metric literal in dict key '{k.value}': {v.value!r}. Rule R20.2 #4."
                            )

        # 7. max(<float literal>, x) and min(<float literal>, x)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("max", "min"):
            for a in node.args:
                if isinstance(a, ast.Constant) and isinstance(a.value, float) and not a.value.is_integer():
                    violations.append(
                        f"{filename}:{lineno}: Forbidden {node.func.id}() with float literal floor: {a.value}. Rule R20.2 #5."
                    )

        # 8. Fallback .get(<key>, <numeric literal>) and x if cond else <numeric literal or constant array> in result-producing code
        if is_result_code:
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get":
                if len(node.args) >= 2:
                    default_arg = node.args[1]
                    key_arg = node.args[0]
                    key_str = key_arg.value if isinstance(key_arg, ast.Constant) and isinstance(key_arg.value, str) else ""
                    if _is_numeric_expr(default_arg):
                        if METRIC_NAME_RE.search(key_str) or (
                            isinstance(default_arg, ast.Constant)
                            and isinstance(default_arg.value, float)
                            and not default_arg.value.is_integer()
                        ):
                            violations.append(
                                f"{filename}:{lineno}: Fallback default in .get({key_str!r}, <numeric>) in result-producing code. Rule R20.2 #6."
                            )
            elif isinstance(node, ast.IfExp):
                for sub in ast.walk(node.orelse):
                    if isinstance(sub, ast.Call):
                        p_name = sub.func.attr if isinstance(sub.func, ast.Attribute) else (sub.func.id if isinstance(sub.func, ast.Name) else "")
                        if p_name in {"ones", "zeros", "full"}:
                            violations.append(
                                f"{filename}:{lineno}: Fallback constant array generator '{p_name}' in IfExp orelse in result-producing code. Rule R20.2 #6."
                            )
                    elif isinstance(sub, ast.Constant) and isinstance(sub.value, float) and not sub.value.is_integer():
                        violations.append(
                            f"{filename}:{lineno}: Fallback float literal {sub.value} in IfExp orelse in result-producing code. Rule R20.2 #6."
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


def test_guard_flags_fabricated_old_eval_ablations() -> None:
    """R20.2: Guard must flag the fabricated old_eval_ablations.py across all 6 categories."""
    old_script_path = ROOT / "docs" / "archive" / "unverified" / "old_eval_ablations.py.txt"
    assert old_script_path.exists(), "old_eval_ablations.py.txt must be preserved for testing"
    source = old_script_path.read_text(encoding="utf-8")

    violations = scan_source_for_synthetic_data(source, filename="scripts/tasks/eval_ablations.py")

    # Guard must flag:
    # 1. Attribute chain containing random / default_rng
    assert any("default_rng" in v or "random" in v.lower() for v in violations), "Must flag np.random.default_rng"
    # 2. numpy.ones or zeros in eval/scripts
    assert any("np.ones" in v or "zeros" in v for v in violations), "Must flag np.ones / np.zeros"
    # 3. Non-integer float literal not in allowlist (e.g. 0.705, 0.85, 55.0)
    assert any("float literal" in v for v in violations), "Must flag unlisted float literals"
    # 4. Metric keys with numeric/boolean literals in dict displays (e.g. mean: 0.0, significant: True)
    assert any("dict" in v.lower() and "metric" in v.lower() for v in violations), "Must flag dict metric literals"
    # 5. max(<float>, x) floor
    assert any("max(" in v or "floor" in v.lower() for v in violations), "Must flag max(0.01, ...)"
    # 6. Fallback .get or ifexp with numeric literal
    assert any("fallback" in v.lower() or "ifexp" in v.lower() or ".get(" in v for v in violations), "Must flag fallback .get / ifexp"


def test_audit_requires_per_case_csv_for_ablations(tmp_path: Path) -> None:
    """R20.2 Rule 7: Ablation/comparison results require per-case CSV in inputs."""
    from scripts.tasks.audit_results import audit_json_file
    script = tmp_path / "scripts" / "tasks" / "eval_ablations.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text("# eval\n", encoding="utf-8")

    ablation_json = tmp_path / "ablations_report.json"
    ablation_json.write_text(json.dumps({
        "generated_by": "scripts/tasks/eval_ablations.py",
        "git_sha": "0000000000000000000000000000000000000000",
        "provenance": "recorded_real_http",
        "inputs": [],
        "ablations": {"test": 1}
    }), encoding="utf-8")
    errors = audit_json_file(ablation_json, root_dir=tmp_path)
    assert any("per-case file (CSV)" in e or "inputs" in e for e in errors)


def test_audit_rejects_degenerate_intervals(tmp_path: Path) -> None:
    """R20.2 Rule 8: Reject ci_lower == ci_upper unless degenerate_reason exists."""
    from scripts.tasks.audit_results import audit_json_file
    script = tmp_path / "scripts" / "eval.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text("# eval\n", encoding="utf-8")

    res_json = tmp_path / "result.json"
    res_json.write_text(json.dumps({
        "generated_by": "scripts/eval.py",
        "git_sha": "0000000000000000000000000000000000000000",
        "provenance": "recorded_real_http",
        "inputs": [{"path": "data.csv", "sha256": "0"*64}],
        "metrics": {"ci_lower": 0.705, "ci_upper": 0.705, "sample_size": 100}
    }), encoding="utf-8")
    errors = audit_json_file(res_json, root_dir=tmp_path)
    assert any("degenerate" in e.lower() for e in errors)


def test_audit_rejects_disabled_llm_path_for_product_quality(tmp_path: Path) -> None:
    """R20.2 Rule 9: Reject live_api/recorded_real_http with llm_path: disabled for product accuracy."""
    from scripts.tasks.audit_results import audit_json_file
    script = tmp_path / "scripts" / "eval.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text("# eval\n", encoding="utf-8")

    res_json = tmp_path / "result.json"
    res_json.write_text(json.dumps({
        "generated_by": "scripts/eval.py",
        "git_sha": "0000000000000000000000000000000000000000",
        "provenance": "recorded_real_http",
        "llm_path": "disabled",
        "accuracy": 0.95,
        "inputs": []
    }), encoding="utf-8")
    errors = audit_json_file(res_json, root_dir=tmp_path)
    assert any("llm_path: disabled" in e or "product" in e.lower() for e in errors)


def test_audit_verifies_significant_matches_interval(tmp_path: Path) -> None:
    """R20.2 Rule 10: significant must match interval excluding zero."""
    from scripts.tasks.audit_results import audit_json_file
    script = tmp_path / "scripts" / "eval.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text("# eval\n", encoding="utf-8")

    res_json = tmp_path / "result.json"
    res_json.write_text(json.dumps({
        "generated_by": "scripts/eval.py",
        "git_sha": "0000000000000000000000000000000000000000",
        "provenance": "recorded_real_http",
        "inputs": [],
        "delta": {"ci_lower": -0.05, "ci_upper": 0.10, "significant": True}
    }), encoding="utf-8")
    errors = audit_json_file(res_json, root_dir=tmp_path)
    assert any("significant" in e.lower() for e in errors)


def test_audit_docs_scan_fails_on_n6_phrases(tmp_path: Path) -> None:
    """R20.2 Rule 11: Fail CI if docs contain Rule N6 phrases."""
    from scripts.tasks.audit_results import scan_docs_for_banned_phrases
    doc = tmp_path / "docs" / "test.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text("We achieved " + "zero " + "simulated metrics here.", encoding="utf-8")
    errors = scan_docs_for_banned_phrases(root_dir=tmp_path)
    assert any("zero simulated" in e.lower() for e in errors)

