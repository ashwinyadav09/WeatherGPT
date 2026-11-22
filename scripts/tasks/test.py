from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def ensure_installed(package: str) -> None:
    try:
        __import__(package)
    except ImportError:
        print(f"Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(ROOT / "requirements.txt"), "-q"])


def main() -> int:
    ensure_installed("pytest")
    ensure_installed("pytest_asyncio")
    ensure_installed("numpy")
    ensure_installed("rank_bm25")

    args = sys.argv[1:]
    target = args if args else ["services/api/tests"]

    print(f"\n--- Running pytest on {target} ---")
    proc = subprocess.run([sys.executable, "-m", "pytest", *target], cwd=str(ROOT))
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
