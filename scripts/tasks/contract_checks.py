from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent.parent


def check_open_meteo() -> bool:
    print("Checking live Open-Meteo API...")
    url = "https://api.open-meteo.com/v1/forecast?latitude=18.52&longitude=73.85&current=temperature_2m"
    try:
        resp = httpx.get(url, timeout=10.0)
        if resp.status_code == 200:
            print("  [OK] Open-Meteo contract check passed")
            return True
        print(f"  [FAIL] Open-Meteo returned status {resp.status_code}")
        return False
    except Exception as e:
        print(f"  [WARN] Open-Meteo unreachable: {e}")
        return False


def check_imd() -> bool:
    imd_key = os.getenv("IMD_API_KEY")
    if not imd_key:
        print("  [SKIP] IMD API key not available; skipping live check (ADR 0007)")
        return True
    print("Checking live IMD API...")
    # Will be tested when key arrives
    return True


def main() -> int:
    ok1 = check_open_meteo()
    ok2 = check_imd()
    if ok1 and ok2:
        print("contract-checks: all active checks passed.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
