# Setup Needed

Items flagged by `python scripts/dev.py doctor`:

- **Python 3.12+**: Host interpreter is Python 3.11.9. Python 3.12 recommended.
- **Docker daemon**: Not currently running on host.
- **Node.js 20+ & npm**: Not found on PATH. Required for web frontend builds and Playwright browser tests.
- **gh (GitHub CLI)**: Not found on PATH. Working offline per AUTOPILOT.md Section 4 (PR bodies saved to `.scratch/weathergpt/pr/<branch>.md`).
- **.env**: Missing. Keys configured via environment or stubs for offline development.
