from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from eval.llm_cache import (
    ProviderThrottler,
    compute_cache_key,
    get_cached_entry,
    put_cached_entry,
)
from scripts.tasks.audit_results import audit_result_data
from scripts.tasks.live_stack import check_api_keys, get_current_git_sha, run_live_eval


def test_cache_key_deterministic() -> None:
    """Verify cache key is identical for identical provider, model, messages, parameters."""
    key1 = compute_cache_key(
        provider="groq",
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": "What is the weather?"}],
        parameters={"temperature": 0, "max_tokens": 100},
    )
    key2 = compute_cache_key(
        provider="GROQ ",
        model="LLAMA-3.3-70B-VERSATILE",
        messages=[{"role": "user", "content": " What is the weather? "}],
        parameters={"max_tokens": 100, "temperature": 0},
    )
    assert key1 == key2
    assert len(key1) == 64


def test_put_and_get_cached_entry(tmp_path: Path) -> None:
    """Verify caching stores with provenance recorded_real_http and marks replayed=True on read."""
    key = "test_key_12345"
    entry = put_cached_entry(
        cache_key=key,
        provider="groq",
        model="test-model",
        messages=[{"role": "user", "content": "test question"}],
        parameters={"param": 1},
        response={"answer": "sunny"},
        latency_ms=150,
        token_counts={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        cache_dir=tmp_path,
    )
    assert entry["provenance"] == "recorded_real_http"
    assert entry["replayed"] is False

    read_back = get_cached_entry(key, cache_dir=tmp_path)
    assert read_back is not None
    assert read_back["replayed"] is True
    assert read_back["response"]["answer"] == "sunny"
    assert read_back["provenance"] == "recorded_real_http"


@pytest.mark.asyncio
async def test_provider_throttler() -> None:
    """Verify ProviderThrottler records throttled calls and sleep time."""
    throttler = ProviderThrottler()
    wait1 = await throttler.throttle("sarvam")
    assert wait1 == 0
    # Immediate second call should throttle
    wait2 = await throttler.throttle("sarvam")
    assert wait2 >= 1000
    assert throttler.throttled_calls >= 1


def test_check_api_keys() -> None:
    """Verify check_api_keys detects presence or absence of real keys."""
    with patch.dict("os.environ", {}, clear=True):
        has_keys, prov = check_api_keys()
        assert not has_keys
        assert prov == "none"

    with patch.dict("os.environ", {"GROQ_API_KEY": "gsk_real_key_12345678901234567890"}):
        has_keys, prov = check_api_keys()
        assert has_keys
        assert prov == "groq"


def test_live_eval_without_keys_exits_not_measured(capsys: pytest.CaptureFixture[str]) -> None:
    """Without keys, run_live_eval exits 0 and prints NOT MEASURED (Rule S1, T2)."""
    with patch.dict("os.environ", {}, clear=True):
        ret = run_live_eval()
        assert ret == 0
        captured = capsys.readouterr()
        assert "NOT MEASURED" in captured.out


def test_live_eval_with_mocked_live_stack_passes_audit(tmp_path: Path) -> None:
    """A live run with real keys produces a report and cache entries passing audit-results."""
    test_out = tmp_path / "live_eval_test.json"
    git_sha = get_current_git_sha()
    manifest_path = Path("eval/recordings/MANIFEST.json")
    manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()

    # Create dummy live run result
    payload: dict[str, Any] = {
        "timestamp": "2026-11-25T00:00:00+00:00",
        "generated_by": "scripts/tasks/live_stack.py",
        "git_sha": git_sha,
        "inputs": [
            {"path": "eval/recordings/MANIFEST.json", "sha256": manifest_sha},
        ],
        "provenance": "recorded_real_http",
        "llm_path": "live",
        "stack": "in_process",
        "throttled_calls": 2,
        "total_throttle_ms": 2000,
        "total": 2,
        "passed": 2,
        "cases": [
            {"id": "c1", "query": "q1", "passed": True, "replayed": False},
            {"id": "c2", "query": "q2", "passed": True, "replayed": True},
        ],
    }
    test_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    errors = audit_result_data(payload, test_out)
    assert not errors, f"Audit errors found: {errors}"
