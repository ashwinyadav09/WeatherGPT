"""Download and unpack real MASSIVE NLU dataset from Amazon S3 (Ticket R12).

Downloads:
- Amazon MASSIVE 1.1 multilingual dataset (tar.gz from S3).
- Extracts en-US, hi-IN, bn-BD, ta-IN, te-IN jsonl partitions.
- Records provenance in ml/intent/data/MANIFEST.json per Rule T1/T6.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
import tarfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.common.manifest import count_file_rows, download_and_record_manifest  # noqa: E402

DATA_DIR = ROOT / "ml" / "intent" / "data"
RAW_DIR = DATA_DIR / "raw"
MASSIVE_DIR = RAW_DIR / "massive"
MANIFEST_FILE = DATA_DIR / "MANIFEST.json"

MASSIVE_TAR_URL = "https://amazon-massive-nlu-dataset.s3.amazonaws.com/amazon-massive-dataset-1.1.tar.gz"
TARGET_LOCALES = ["en-US", "hi-IN", "bn-BD", "ta-IN", "te-IN"]


def download_massive_dataset() -> dict[str, Any]:
    """Download Amazon MASSIVE 1.1 tarball and extract target Indic and English files."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    MASSIVE_DIR.mkdir(parents=True, exist_ok=True)

    tar_path = RAW_DIR / "amazon-massive-dataset-1.1.tar.gz"

    print(f"Downloading Amazon MASSIVE 1.1 from {MASSIVE_TAR_URL}...")
    manifest_rec = download_and_record_manifest(
        url=MASSIVE_TAR_URL,
        output_path=tar_path,
        manifest_path=MANIFEST_FILE,
        timeout=180.0,
    )
    print(f"[OK] Downloaded {manifest_rec['bytes']} bytes (sha256={manifest_rec['sha256'][:12]}...)")

    # Extract target locales from tarfile
    extracted_files: dict[str, Path] = {}
    with tarfile.open(tar_path, mode="r:gz") as tf:
        for member in tf.getmembers():
            for locale in TARGET_LOCALES:
                if member.name.endswith(f"/{locale}.jsonl"):
                    out_file = MASSIVE_DIR / f"{locale}.jsonl"
                    fileobj = tf.extractfile(member)
                    if fileobj:
                        content = fileobj.read()
                        out_file.write_bytes(content)
                        extracted_files[locale] = out_file
                        sha = hashlib.sha256(content).hexdigest()
                        rec = {
                            "source": "AmazonScience/massive",
                            "locale": locale,
                            "file": out_file.name,
                            "path": str(out_file.relative_to(ROOT)).replace("\\", "/"),
                            "bytes": len(content),
                            "sha256": sha,
                            "rows": count_file_rows(out_file),
                            "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                        }
                        # Append to manifest
                        try:
                            records = json.loads(MANIFEST_FILE.read_text(encoding="utf-8")) if MANIFEST_FILE.exists() else []
                            if not isinstance(records, list):
                                records = [records]
                        except Exception:
                            records = []
                        records = [r for r in records if r.get("file") != out_file.name]
                        records.append(rec)
                        MANIFEST_FILE.write_text(json.dumps(records, indent=2), encoding="utf-8")
                        print(f"[OK] Extracted {locale}: {count_file_rows(out_file)} utterances -> {out_file.name}")

    return {
        "tarball": str(tar_path),
        "extracted_files": {k: str(v) for k, v in extracted_files.items()},
    }


def main() -> int:
    download_massive_dataset()
    return 0


if __name__ == "__main__":
    sys.exit(main())
