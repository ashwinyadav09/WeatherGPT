"""Data download helper and MANIFEST recorder (Ticket R10.1).

Writes MANIFEST.json per source containing:
- url: source URL
- parameters: query/API parameters
- retrieved_at: UTC ISO timestamp
- bytes: size in bytes
- sha256: SHA-256 digest
- rows: row count (for tabular/delimited data)

Raises immediately on HTTP errors and never returns fallback data (Rule T7).
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any

import httpx


def count_file_rows(file_path: Path) -> int:
    """Count data rows in a file (CSV rows excluding header, JSON lines, or text lines)."""
    if not file_path.exists():
        return 0

    suffix = file_path.suffix.lower()
    try:
        if suffix in (".csv", ".tsv"):
            with file_path.open("r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                rows = list(reader)
                return max(0, len(rows) - 1) if rows else 0
        elif suffix in (".jsonl", ".txt"):
            with file_path.open("r", encoding="utf-8", errors="replace") as f:
                return sum(1 for line in f if line.strip())
        elif suffix == ".json":
            with file_path.open("r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return len(data)
                elif isinstance(data, dict):
                    # Check for common array keys
                    for k in ("data", "items", "rows", "records", "results", "daily", "hourly"):
                        if k in data and isinstance(data[k], list):
                            return len(data[k])
                    return 1
                return 1
        else:
            with file_path.open("rb") as f:
                return sum(1 for line in f if line.strip())
    except Exception:
        return 0


def download_and_record_manifest(
    url: str,
    output_path: Path,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    manifest_path: Path | None = None,
    client: httpx.Client | None = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """Download data from a real URL and write MANIFEST.json.

    Raises:
        httpx.HTTPStatusError: On 4xx/5xx HTTP errors (never falls back or hides errors).
        httpx.RequestError: On network or transport failures.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if client is not None:
        resp = client.get(url, params=params, headers=headers, timeout=timeout)
    else:
        with httpx.Client(timeout=timeout) as new_client:
            resp = new_client.get(url, params=params, headers=headers)

    # Raise immediately on any error response — never return fallback data
    resp.raise_for_status()

    content = resp.content
    output_path.write_bytes(content)

    sha256_hash = hashlib.sha256(content).hexdigest()
    byte_count = len(content)
    row_count = count_file_rows(output_path)
    now_utc = dt.datetime.now(dt.timezone.utc).isoformat()

    manifest_record: dict[str, Any] = {
        "url": url,
        "parameters": params or {},
        "retrieved_at": now_utc,
        "bytes": byte_count,
        "sha256": sha256_hash,
        "rows": row_count,
        "file": output_path.name,
    }

    m_path = manifest_path or (output_path.parent / "MANIFEST.json")
    m_path.parent.mkdir(parents=True, exist_ok=True)

    # If MANIFEST.json already exists as a list of sources, append or update
    existing_records: list[dict[str, Any]] = []
    if m_path.exists():
        try:
            with m_path.open("r", encoding="utf-8") as f:
                prev_data = json.load(f)
                if isinstance(prev_data, list):
                    existing_records = [r for r in prev_data if isinstance(r, dict) and r.get("file") != output_path.name]
                elif isinstance(prev_data, dict):
                    if prev_data.get("file") != output_path.name:
                        existing_records = [prev_data]
        except Exception:
            existing_records = []

    all_records = existing_records + [manifest_record]
    with m_path.open("w", encoding="utf-8") as f:
        json.dump(all_records, f, indent=2)

    return manifest_record


def verify_manifest(manifest_path: Path, data_file: Path) -> bool:
    """Verify that a data file matches its recorded MANIFEST.json entry."""
    if not manifest_path.exists() or not data_file.exists():
        return False

    try:
        content = manifest_path.read_text(encoding="utf-8")
        data = json.loads(content)
        records = data if isinstance(data, list) else [data]

        target_name = data_file.name
        matched = next((r for r in records if r.get("file") == target_name), None)
        if not matched:
            return False

        computed_sha = hashlib.sha256(data_file.read_bytes()).hexdigest()
        return computed_sha.lower() == str(matched.get("sha256", "")).lower()
    except Exception:
        return False
