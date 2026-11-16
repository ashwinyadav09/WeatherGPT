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
    ensure_installed("ruff")
    ensure_installed("mypy")

    print("\n--- Running ruff ---")
    r1 = subprocess.run([sys.executable, "-m", "ruff", "check", "."], cwd=str(ROOT))
    if r1.returncode != 0:
        return r1.returncode

    print("\n--- Running mypy ---")
    r2 = subprocess.run(
        [sys.executable, "-m", "mypy", "services/api/app", "packages/contracts"],
        cwd=str(ROOT),
    )
    return r2.returncode


if __name__ == "__main__":
    sys.exit(main())
