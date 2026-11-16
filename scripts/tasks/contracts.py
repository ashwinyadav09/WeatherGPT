from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.api.app.main import app

CONTRACTS_DIR = ROOT / "packages" / "contracts"
SCHEMAS_DIR = CONTRACTS_DIR / "schemas"
OPENAPI_FILE = CONTRACTS_DIR / "openapi.json"


def main() -> int:
    CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)
    SCHEMAS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Export OpenAPI JSON
    openapi_schema = app.openapi()
    with OPENAPI_FILE.open("w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
    print(f"Exported OpenAPI schema to {OPENAPI_FILE.relative_to(ROOT)}")

    # 2. Validate all JSON schemas
    schema_files = list(SCHEMAS_DIR.glob("*.json"))
    if not schema_files:
        print("ERROR: No schema files found in packages/contracts/schemas/")
        return 1

    validator_cls = jsonschema.validators.validator_for({"$schema": "https://json-schema.org/draft/2020-12/schema"})
    for s_path in schema_files:
        with s_path.open("r", encoding="utf-8") as f:
            schema = json.load(f)
            validator_cls.check_schema(schema)
        print(f"Schema valid: {s_path.name}")

    print("contracts: openapi.json and schemas successfully validated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
