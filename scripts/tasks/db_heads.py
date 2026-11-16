from __future__ import annotations

import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

ROOT = Path(__file__).resolve().parent.parent.parent
ALEMBIC_INI = ROOT / "services" / "api" / "alembic.ini"


def main() -> int:
    if not ALEMBIC_INI.exists():
        print(f"alembic.ini not found at {ALEMBIC_INI}")
        return 1

    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ROOT / "services" / "api" / "alembic"))
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()

    print(f"Alembic heads found: {heads}")
    if len(heads) != 1:
        print(f"ERROR: Expected exactly 1 migration head, but found {len(heads)}: {heads}")
        return 1

    print("db-heads: exactly one migration head verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
