"""Download official public disaster management and weather safety documents (Ticket R15).

Downloads public guidance PDFs and bulletins from IMD Agrimet, NDMA, and ICAR
into data/raw/knowledge/ and records provenance in MANIFEST.json and sources.csv.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RAW_DIR = ROOT / "data" / "raw" / "knowledge"
SOURCES_CSV = ROOT / "seeds" / "knowledge" / "sources.csv"
MANIFEST_FILE = RAW_DIR / "MANIFEST.json"

BASE_URL = "https://imdagrimet.gov.in/"

OFFICIAL_DOCUMENTS: list[dict[str, Any]] = [
    {
        "filename": "imdagrimet_heatwave_en.pdf",
        "title": "IMD-NDMA National Heatwave Do's and Don'ts (English)",
        "hazard": "heat_wave",
        "language": "en",
        "url": BASE_URL + "Files/Dos_Donts/Heat_wave_Dos_and_Donts.pdf",
        "license": "OGDL-India",
    },
    {
        "filename": "imdagrimet_coldwave_en.pdf",
        "title": "IMD-NDMA National Cold Wave Do's and Don'ts (English)",
        "hazard": "cold_wave",
        "language": "en",
        "url": BASE_URL + "Files/Dos_Donts/Cold%20wave_Dos_and_Donts.pdf",
        "license": "OGDL-India",
    },
    {
        "filename": "imdagrimet_floods_en.pdf",
        "title": "IMD-NDMA National Floods Do's and Don'ts (English)",
        "hazard": "flood",
        "language": "en",
        "url": BASE_URL + "Files/Dos_Donts/Floods_Dos_and_Donts.pdf",
        "license": "OGDL-India",
    },
    {
        "filename": "imdagrimet_cyclone_en.pdf",
        "title": "IMD-NDMA National Cyclone Do's and Don'ts (English)",
        "hazard": "cyclone",
        "language": "en",
        "url": BASE_URL + "Files/Dos_Donts/Cyclone_Dos_and_Donts.pdf",
        "license": "OGDL-India",
    },
    {
        "filename": "imdagrimet_thunderstorm_en.pdf",
        "title": "IMD-NDMA National Thunderstorm & Lightning Safety (English)",
        "hazard": "thunderstorm",
        "language": "en",
        "url": BASE_URL + "Files/Dos_Donts/Thunderstorm_dos_and_donts.pdf",
        "license": "OGDL-India",
    },
    {
        "filename": "imdagrimet_heatwave_hi.pdf",
        "title": "IMD-NDMA Heatwave Do's and Don'ts (Hindi)",
        "hazard": "heat_wave",
        "language": "hi",
        "url": BASE_URL + "Files/Dos_Donts/Dos_Donts_Hindi/Dos_Donts_HeatWave_Hindi.pdf",
        "license": "OGDL-India",
    },
    {
        "filename": "imdagrimet_coldwave_hi.pdf",
        "title": "IMD-NDMA Cold Wave Do's and Don'ts (Hindi)",
        "hazard": "cold_wave",
        "language": "hi",
        "url": BASE_URL + "Files/Dos_Donts/Dos_Donts_Hindi/Dos_Donts_ColdWave_Hindi.pdf",
        "license": "OGDL-India",
    },
    {
        "filename": "imdagrimet_floods_hi.pdf",
        "title": "IMD-NDMA Floods Safety (Hindi)",
        "hazard": "flood",
        "language": "hi",
        "url": BASE_URL + "Files/Dos_Donts/Dos_Donts_Hindi/Dos_Donts_Floods_Hindi.pdf",
        "license": "OGDL-India",
    },
    {
        "filename": "imdagrimet_cyclone_hi.pdf",
        "title": "IMD-NDMA Cyclone Safety (Hindi)",
        "hazard": "cyclone",
        "language": "hi",
        "url": BASE_URL + "Files/Dos_Donts/Dos_Donts_Hindi/Dos_Donts_Cyclone_Hindi.pdf",
        "license": "OGDL-India",
    },
    {
        "filename": "imdagrimet_heatwave_bn.pdf",
        "title": "IMD-NDMA Heatwave Do's and Don'ts (Bengali)",
        "hazard": "heat_wave",
        "language": "bn",
        "url": BASE_URL + "Files/Dos_Donts/Dos_Donts_Bengali/Dos_Donts_HeatWave_Bengali.pdf",
        "license": "OGDL-India",
    },
    {
        "filename": "imdagrimet_heatwave_mr.pdf",
        "title": "IMD-NDMA Heatwave Do's and Don'ts (Marathi)",
        "hazard": "heat_wave",
        "language": "mr",
        "url": BASE_URL + "Files/Dos_Donts/Dos_Donts_Marathi/Dos_Donts_HeatWave_Marathi.pdf",
        "license": "OGDL-India",
    },
    {
        "filename": "imdagrimet_heatwave_or.pdf",
        "title": "IMD-NDMA Heatwave Do's and Don'ts (Odia)",
        "hazard": "heat_wave",
        "language": "or",
        "url": BASE_URL + "Files/Dos_Donts/Dos_Donts_Odia/Dos_Donts_HeatWave_Odia.pdf",
        "license": "OGDL-India",
    },
    {
        "filename": "imdagrimet_heatwave_ta.pdf",
        "title": "IMD-NDMA Heatwave Do's and Don'ts (Tamil)",
        "hazard": "heat_wave",
        "language": "ta",
        "url": BASE_URL + "Files/Dos_Donts/Dos_Donts_Tamil/Dos_Donts_HeatWave_Tamil.pdf",
        "license": "OGDL-India",
    },
    {
        "filename": "imdagrimet_heatwave_te.pdf",
        "title": "IMD-NDMA Heatwave Do's and Don'ts (Telugu)",
        "hazard": "heat_wave",
        "language": "te",
        "url": BASE_URL + "Files/Dos_Donts/Dos_Donts_Telugu/Dos_Donts_HeatWave_Telugu.pdf",
        "license": "OGDL-India",
    },
    {
        "filename": "imd_colour_codes.pdf",
        "title": "IMD Weather Warning Colour Code System (About Urban Met Services)",
        "hazard": "colour_code",
        "language": "en",
        "url": "https://mausam.imd.gov.in/delhiums/mcdata/Aboutus.pdf",
        "license": "CC-BY-4.0",
    },
    {
        "filename": "ddma_heat_action_plan.pdf",
        "title": "Delhi Disaster Management Authority State Heat Action Plan",
        "hazard": "heat_wave",
        "language": "en",
        "url": "https://ddma.delhi.gov.in/sites/default/files/ddma/generic_multiple_files/hap_delhi_21.4.25_3.pdf",
        "license": "OGDL-India",
    },
    {
        "filename": "imd_fishermen_warning.pdf",
        "title": "IMD National Cyclone & Marine Fishermen Warning Bulletin",
        "hazard": "marine",
        "language": "en",
        "url": "https://rsmcnewdelhi.imd.gov.in/uploads/archive/45/45_0bbace9d6227c530ddcc.pdf",
        "license": "CC-BY-4.0",
    },
    {
        "filename": "imdagrimet_coldwave_bn.pdf",
        "title": "IMD-NDMA Cold Wave Do's and Don'ts (Bengali)",
        "hazard": "cold_wave",
        "language": "bn",
        "url": BASE_URL + "Files/Dos_Donts/Dos_Donts_Bengali/Dos_Donts_ColdWave_Bengali.pdf",
        "license": "OGDL-India",
    },
    {
        "filename": "imdagrimet_coldwave_mr.pdf",
        "title": "IMD-NDMA Cold Wave Do's and Don'ts (Marathi)",
        "hazard": "cold_wave",
        "language": "mr",
        "url": BASE_URL + "Files/Dos_Donts/Dos_Donts_Marathi/Dos_Donts_ColdWave_Marathi.pdf",
        "license": "OGDL-India",
    },
    {
        "filename": "imdagrimet_coldwave_or.pdf",
        "title": "IMD-NDMA Cold Wave Do's and Don'ts (Odia)",
        "hazard": "cold_wave",
        "language": "or",
        "url": BASE_URL + "Files/Dos_Donts/Dos_Donts_Odia/Dos_Donts_ColdWave_Odia.pdf",
        "license": "OGDL-India",
    },
    {
        "filename": "imdagrimet_coldwave_ta.pdf",
        "title": "IMD-NDMA Cold Wave Do's and Don'ts (Tamil)",
        "hazard": "cold_wave",
        "language": "ta",
        "url": BASE_URL + "Files/Dos_Donts/Dos_Donts_Tamil/Dos_Donts_ColdWave_Tamil.pdf",
        "license": "OGDL-India",
    },
    {
        "filename": "imdagrimet_coldwave_te.pdf",
        "title": "IMD-NDMA Cold Wave Do's and Don'ts (Telugu)",
        "hazard": "cold_wave",
        "language": "te",
        "url": BASE_URL + "Files/Dos_Donts/Dos_Donts_Telugu/Dos_Donts_ColdWave_Telugu.pdf",
        "license": "OGDL-India",
    },
    {
        "filename": "imdagrimet_floods_bn.pdf",
        "title": "IMD-NDMA Floods Safety (Bengali)",
        "hazard": "flood",
        "language": "bn",
        "url": BASE_URL + "Files/Dos_Donts/Dos_Donts_Bengali/Dos_Donts_Floods_Bengali.pdf",
        "license": "OGDL-India",
    },
    {
        "filename": "imdagrimet_floods_mr.pdf",
        "title": "IMD-NDMA Floods Safety (Marathi)",
        "hazard": "flood",
        "language": "mr",
        "url": BASE_URL + "Files/Dos_Donts/Dos_Donts_Marathi/Dos_Donts_Floods_Marathi.pdf",
        "license": "OGDL-India",
    },
    {
        "filename": "imdagrimet_floods_or.pdf",
        "title": "IMD-NDMA Floods Safety (Odia)",
        "hazard": "flood",
        "language": "or",
        "url": BASE_URL + "Files/Dos_Donts/Dos_Donts_Odia/Dos_Donts_Floods_Odia.pdf",
        "license": "OGDL-India",
    },
    {
        "filename": "imdagrimet_floods_ta.pdf",
        "title": "IMD-NDMA Floods Safety (Tamil)",
        "hazard": "flood",
        "language": "ta",
        "url": BASE_URL + "Files/Dos_Donts/Dos_Donts_Tamil/Dos_Donts_Floods_Tamil.pdf",
        "license": "OGDL-India",
    },
    {
        "filename": "imdagrimet_floods_te.pdf",
        "title": "IMD-NDMA Floods Safety (Telugu)",
        "hazard": "flood",
        "language": "te",
        "url": BASE_URL + "Files/Dos_Donts/Dos_Donts_Telugu/Dos_Donts_Floods_Telugu.pdf",
        "license": "OGDL-India",
    },
    {
        "filename": "imdagrimet_cyclone_bn.pdf",
        "title": "IMD-NDMA Cyclone Safety (Bengali)",
        "hazard": "cyclone",
        "language": "bn",
        "url": BASE_URL + "Files/Dos_Donts/Dos_Donts_Bengali/Dos_Donts_Cyclone_Bengali.pdf",
        "license": "OGDL-India",
    },
    {
        "filename": "imdagrimet_cyclone_mr.pdf",
        "title": "IMD-NDMA Cyclone Safety (Marathi)",
        "hazard": "cyclone",
        "language": "mr",
        "url": BASE_URL + "Files/Dos_Donts/Dos_Donts_Marathi/Dos_Donts_Cyclone_Marathi.pdf",
        "license": "OGDL-India",
    },
    {
        "filename": "imdagrimet_cyclone_or.pdf",
        "title": "IMD-NDMA Cyclone Safety (Odia)",
        "hazard": "cyclone",
        "language": "or",
        "url": BASE_URL + "Files/Dos_Donts/Dos_Donts_Odia/Dos_Donts_Cyclone_Odia.pdf",
        "license": "OGDL-India",
    },
    {
        "filename": "imdagrimet_cyclone_ta.pdf",
        "title": "IMD-NDMA Cyclone Safety (Tamil)",
        "hazard": "cyclone",
        "language": "ta",
        "url": BASE_URL + "Files/Dos_Donts/Dos_Donts_Tamil/Dos_Donts_Cyclone_Tamil.pdf",
        "license": "OGDL-India",
    },
    {
        "filename": "imdagrimet_cyclone_te.pdf",
        "title": "IMD-NDMA Cyclone Safety (Telugu)",
        "hazard": "cyclone",
        "language": "te",
        "url": BASE_URL + "Files/Dos_Donts/Dos_Donts_Telugu/Dos_Donts_Cyclone_Telugu.pdf",
        "license": "OGDL-India",
    },
]


def download_corpus(force: bool = False) -> list[dict[str, Any]]:
    """Download public documents, compute SHA256 hashes, and save manifest."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    today_str = dt.date.today().isoformat()
    results: list[dict[str, Any]] = []

    with httpx.Client(timeout=30.0, verify=False, follow_redirects=True) as client:
        for doc in OFFICIAL_DOCUMENTS:
            fname = doc["filename"]
            out_file = RAW_DIR / fname

            if out_file.exists() and not force:
                content = out_file.read_bytes()
                sha = hashlib.sha256(content).hexdigest()
                status = "cached"
            else:
                try:
                    resp = client.get(doc["url"])
                    if resp.status_code == 200 and len(resp.content) > 100:
                        content = resp.content
                        out_file.write_bytes(content)
                        sha = hashlib.sha256(content).hexdigest()
                        status = "downloaded"
                    else:
                        print(f"[WARN] Failed to download {doc['url']}: HTTP {resp.status_code}")
                        status = "unavailable"
                        sha = ""
                except Exception as exc:
                    print(f"[WARN] Error downloading {doc['url']}: {exc}")
                    status = "unavailable"
                    sha = ""

            doc_record = {
                "filename": fname,
                "title": doc["title"],
                "hazard": doc["hazard"],
                "language": doc["language"],
                "url": doc["url"],
                "license": doc["license"],
                "retrieval_date": today_str,
                "sha256": sha,
                "status": status,
            }
            results.append(doc_record)
            print(f"[{status.upper()}] {fname}: sha256={sha[:12]}...")

    # Write MANIFEST.json
    manifest_data = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "total_documents": len(results),
        "available_documents": sum(1 for r in results if r["status"] != "unavailable"),
        "documents": results,
    }
    MANIFEST_FILE.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    # Update seeds/knowledge/sources.csv
    SOURCES_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["filename", "title", "hazard", "language", "url", "license", "retrieval_date", "sha256", "status"]
    with SOURCES_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(r)

    print(f"[OK] Downloaded {manifest_data['available_documents']}/{len(results)} documents.")
    print(f"[OK] Updated {SOURCES_CSV.relative_to(ROOT)} and {MANIFEST_FILE.relative_to(ROOT)}")
    return results


if __name__ == "__main__":
    download_corpus()
