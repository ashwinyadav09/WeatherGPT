from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.contracts.validator import validate_schema
from services.api.app.evidence.models import AlertModel
from services.api.app.modules.alerts.engine import AlertEngine


def main() -> int:
    fixtures_dir = ROOT / "eval" / "fixtures" / "sachet"
    if not fixtures_dir.exists():
        print(f"No alert fixtures found in {fixtures_dir}")
        return 0

    engine = AlertEngine()
    replayed = 0

    for fix_file in fixtures_dir.glob("*.json"):
        with fix_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
        cleaned = {k: v for k, v in data.items() if not k.startswith("_")}
        validate_schema("alert", cleaned)
        alert = AlertModel(**cleaned)
        engine.ingest_sample_alert(alert)
        replayed += 1
        print(f"Replayed alert {alert.id} from {fix_file.name} (severity: {alert.severity}, level: {alert.level})")

    print(f"replay-alerts: successfully replayed {replayed} alerts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
