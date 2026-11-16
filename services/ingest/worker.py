from __future__ import annotations

import time


def main() -> None:
    print("Ingest worker started. Waiting for scheduled tasks...")
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
