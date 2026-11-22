#!/usr/bin/env python3
"""WeatherGPT task runner (cross-platform, standard library only).

Commands
  doctor            check prerequisites and the local setup (--strict, --write)
  up / down         start or stop the Docker Compose stack
  test              run all test suites
  lint              run linters and type checks
  eval --lang CODE  run the golden-set evaluation
  replay-alerts     replay recorded alerts through the alert pipeline
  contracts         export OpenAPI and JSON Schemas to packages/contracts
  acceptance        run every acceptance gate
  contract-checks   run live contract checks against outside APIs (needs keys)
  ci                everything CI runs: secret-scan, progress, lint, test, migration heads, eval (en)
  secret-scan       look for keys committed by mistake
  progress          roll the per-person ledgers up into .scratch/weathergpt/PROGRESS.md
  demo              start the scripted demo

doctor, up, down, secret-scan, progress and ci are built in. Every other command is delegated to
scripts/tasks/<name>.py (dashes become underscores) once a ticket creates that file. A task file is
run as: python scripts/tasks/<name>.py <extra args>; exit code 0 means success. Ticket 01a creates
the tasks; keep the command names stable.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRATCH = ROOT / ".scratch" / "weathergpt"
ISSUES = SCRATCH / "issues"
LEDGERS = SCRATCH / "progress"
PROGRESS = SCRATCH / "PROGRESS.md"
TASKS = ROOT / "scripts" / "tasks"
TICKET_ID = r"(\d{2}[a-c]?|R\d+(?:\.\d+)?)"


def say(msg: str = "") -> None:
    print(msg, flush=True)


def run(cmd, cwd=None) -> int:
    say("$ " + " ".join(str(c) for c in cmd))
    try:
        return subprocess.call([str(c) for c in cmd], cwd=str(cwd or ROOT))
    except FileNotFoundError:
        say(f"  command not found: {cmd[0]}")
        return 127


def delegate(name: str, extra: list[str]):
    """Run scripts/tasks/<name>.py. Returns its exit code, or None if the task does not exist yet."""
    path = TASKS / f"{name.replace('-', '_')}.py"
    if not path.exists():
        return None
    return run([sys.executable, path, *extra])


def delegated(name: str, extra: list[str]) -> int:
    code = delegate(name, extra)
    if code is None:
        say(f"'{name}' is not created yet (ticket 01a adds scripts/tasks/{name.replace('-', '_')}.py). Nothing to do.")
        return 0
    return code


# ---------------------------------------------------------------- doctor
def first_line(text: str) -> str:
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    return lines[0].strip() if lines else "ok"


def probe(exe: str, args: list[str]):
    path = shutil.which(exe)
    if not path:
        return None
    try:
        out = subprocess.run([path, *args], capture_output=True, text=True, timeout=30)
        return first_line(out.stdout or out.stderr)
    except Exception:
        return "found"


def cmd_doctor(args, rest) -> int:
    rows = []

    def add(name, ok, detail, required, hint):
        rows.append((name, ok, detail, required, hint))

    add("python 3.12+", sys.version_info >= (3, 12), sys.version.split()[0], True, "Install Python 3.12 (python.org or pyenv)")
    git = probe("git", ["--version"])
    add("git", bool(git), git or "not found", True, "Install Git")
    docker = probe("docker", ["--version"])
    add("docker", bool(docker), docker or "not found", True, "Install Docker Desktop or Docker Engine")
    compose = probe("docker", ["compose", "version"]) if docker else None
    add("docker compose v2", bool(compose), compose or "not found", True, "Update Docker so 'docker compose' works")
    daemon_ok = False
    if docker:
        daemon_ok = subprocess.run([shutil.which("docker"), "info"], capture_output=True).returncode == 0
    add("docker daemon running", daemon_ok, "running" if daemon_ok else "not running", True, "Start Docker Desktop or the docker service")
    node = probe("node", ["--version"])
    node_ok = False
    if node:
        m = re.match(r"v?(\d+)", node)
        node_ok = bool(m and int(m.group(1)) >= 20)
    add("node 20+", node_ok, node or "not found", True, "Install Node.js 20 or newer")
    npm = probe("npm", ["--version"])
    add("npm", bool(npm), npm or "not found", True, "Comes with Node.js")
    ffmpeg = probe("ffmpeg", ["-version"])
    add("ffmpeg (audio conversion; also inside the API image)", bool(ffmpeg), ffmpeg or "not found", False, "Install ffmpeg if you run the API outside Docker")
    gh = probe("gh", ["--version"])
    add("gh (GitHub CLI)", bool(gh), gh or "not found", False, "Install the GitHub CLI and run 'gh auth login' to let agents open pull requests")
    env_ok = (ROOT / ".env").exists()
    add(".env file", env_ok, "present" if env_ok else "missing", False, "Copy .env.example to .env and fill in your keys")

    width = max(len(r[0]) for r in rows)
    missing_required = []
    for name, ok, detail, required, hint in rows:
        flag = "OK     " if ok else ("MISSING" if required else "optional")
        say(f"{flag}  {name.ljust(width)}  {detail}")
        if not ok:
            say(f"         hint: {hint}")
            if required:
                missing_required.append((name, hint))
    if missing_required:
        say("")
        say("Missing required items: " + ", ".join(n for n, _ in missing_required))
        if getattr(args, "write", False):
            lines = ["# Setup needed", "", "Generated by `python scripts/dev.py doctor --write`. A human must fix these.", ""]
            lines += [f"- {n}: {h}" for n, h in missing_required]
            (ROOT / "SETUP_NEEDED.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
            say("Wrote SETUP_NEEDED.md")
    else:
        say("")
        say("All required tools are present.")
    return 1 if (missing_required and getattr(args, "strict", False)) else 0


# ---------------------------------------------------------------- stack
def cmd_up(args, rest) -> int:
    if not (ROOT / "docker-compose.yml").exists():
        say("docker-compose.yml is not created yet (ticket 01a). Nothing to start.")
        return 0
    return run(["docker", "compose", "up", "-d", "--build", *rest])


def cmd_down(args, rest) -> int:
    if not (ROOT / "docker-compose.yml").exists():
        say("docker-compose.yml is not created yet (ticket 01a). Nothing to stop.")
        return 0
    return run(["docker", "compose", "down", *rest])


# ---------------------------------------------------------------- secret scan
PATTERNS = [
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("OpenAI or OpenRouter style key", re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}")),
    ("Groq key", re.compile(r"\bgsk_[A-Za-z0-9]{20,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}")),
    ("GitHub token", re.compile(r"\b(?:ghp|gho|ghs|ghu)_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}")),
    ("secret assignment", re.compile(r"""(?i)\b(?:api[_-]?key|secret|token|password)\b\s*[:=]\s*['"][A-Za-z0-9_\-/+=]{24,}['"]""")),
]
SKIP_SUFFIX = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".zip", ".pdf", ".lock", ".zarr", ".grib", ".grib2", ".grd"}
SKIP_NAMES = {".env.example", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "poetry.lock", "uv.lock", "dev.py"}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "data", "__pycache__", "dist", "build"}
SKIP_WORDS = ("example", "placeholder", "change-me", "your-key", "your_key", "xxxx")


def candidate_files():
    if (ROOT / ".git").exists() and shutil.which("git"):
        out = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=str(ROOT), capture_output=True,
        )
        if out.returncode == 0:
            for rel in out.stdout.decode("utf-8", "replace").split("\0"):
                if rel:
                    yield ROOT / rel
            return
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            yield Path(d) / f


def cmd_secret_scan(args, rest) -> int:
    hits = []
    for path in candidate_files():
        if path.name in SKIP_NAMES or path.suffix.lower() in SKIP_SUFFIX or not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            low = line.lower()
            if any(w in low for w in SKIP_WORDS):
                continue
            for label, pat in PATTERNS:
                m = pat.search(line)
                if m:
                    hits.append((path.relative_to(ROOT), n, label, m.group(0)[:6] + "..."))
    if hits:
        say("Possible secrets found:")
        for rel, n, label, shown in hits:
            say(f"  {rel}:{n}  {label}  {shown}")
        say("Remove them, rotate the key, and keep keys in .env only.")
        return 1
    say("secret-scan: no secrets found.")
    return 0


# ---------------------------------------------------------------- progress
def read_csv(path: Path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def ticket_titles() -> dict:
    titles = {}
    for p in sorted(ISSUES.glob("*.md")):
        m = re.match(rf"^({TICKET_ID})-", p.name)
        if not m:
            continue
        first = p.read_text(encoding="utf-8").splitlines()[0] if p.stat().st_size else ""
        t = re.sub(rf"^#\s*{TICKET_ID}:\s*", "", first).strip()
        titles[m.group(1)] = t or p.stem
    rem_plan = SCRATCH / "REMEDIATION_PLAN.md"
    if rem_plan.exists():
        for m in re.finditer(r"\*\*(R\d+(?:\.\d+)?)\s+([^*]+)\*\*", rem_plan.read_text(encoding="utf-8")):
            titles[m.group(1)] = m.group(2).strip()
    return titles


def parse_ledger(path: Path) -> dict:
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 3 and re.fullmatch(TICKET_ID, cells[0]):
            rows[cells[0]] = (cells[2].lower() or "todo", cells[3] if len(cells) > 3 else "")
    return rows


def cmd_progress(args, rest) -> int:
    assignments = read_csv(ROOT / "team" / "assignments.csv")
    if not assignments:
        say("team/assignments.csv not found or empty.")
        return 1
    titles = ticket_titles()
    ledgers = {}
    if LEDGERS.exists():
        for p in LEDGERS.glob("*.md"):
            ledgers[p.stem.lower()] = parse_ledger(p)
    lines = [
        "# Progress",
        "",
        f"Generated by `python scripts/dev.py progress` on {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC. Do not edit by hand.",
        "Each person edits only their own ledger in `.scratch/weathergpt/progress/<name>.md`.",
        "",
        "| Ticket | Title | Owner | Reviewer | Wave | Status | Notes |",
        "|---|---|---|---|---|---|---|",
    ]
    summary: dict = {}
    for row in assignments:
        t, owner = row["ticket"], row["owner"].lower()
        status, notes = ledgers.get(owner, {}).get(t, ("todo", ""))
        lines.append(f"| {t} | {titles.get(t, '?')} | {owner} | {row['reviewer']} | {row['wave']} | {status} | {notes} |")
        summary.setdefault(owner, {}).setdefault(status, 0)
        summary[owner][status] += 1
    lines += ["", "## Summary", "", "| Owner | Status counts |", "|---|---|"]
    for owner, counts in sorted(summary.items()):
        lines.append(f"| {owner} | " + ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())) + " |")
    PROGRESS.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    say(f"Wrote {PROGRESS.relative_to(ROOT)}")
    for owner, counts in sorted(summary.items()):
        say(f"  {owner}: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    return 0


# ---------------------------------------------------------------- ci
def cmd_ci(args, rest) -> int:
    failures = []

    def step(name, fn):
        say(f"\n== {name} ==")
        code = fn()
        if code not in (0, None):
            failures.append(name)

    step("secret-scan", lambda: cmd_secret_scan(args, []))
    step("progress", lambda: cmd_progress(args, []))
    step("lint", lambda: delegated("lint", []))
    step("test", lambda: delegated("test", []))
    step("migration heads", lambda: delegated("db-heads", []))
    step("eval (en)", lambda: delegated("eval", ["--lang", "en"]))
    say("")
    if failures:
        say("CI failed: " + ", ".join(failures))
        return 1
    say("CI passed.")
    return 0


# ---------------------------------------------------------------- main
DELEGATED = {
    "test": "run all test suites",
    "lint": "run linters and type checks",
    "eval": "run the golden-set evaluation (--lang CODE)",
    "replay-alerts": "replay recorded alerts",
    "contracts": "export OpenAPI and JSON Schemas",
    "acceptance": "run every acceptance gate",
    "contract-checks": "run live contract checks (needs keys)",
    "demo": "start the scripted demo",
    "translate-static": "pre-translate static strings into seeds/translations/<lang>.json",
}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="dev.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("doctor", help="check prerequisites")
    d.add_argument("--strict", action="store_true", help="exit 1 if a required tool is missing")
    d.add_argument("--write", action="store_true", help="write SETUP_NEEDED.md when something is missing")
    sub.add_parser("up", help="start the Docker Compose stack")
    sub.add_parser("down", help="stop the Docker Compose stack")
    sub.add_parser("ci", help="everything CI runs")
    sub.add_parser("secret-scan", help="look for committed keys")
    sub.add_parser("progress", help="roll ledgers up into PROGRESS.md")
    for name, help_text in DELEGATED.items():
        sub.add_parser(name, help=help_text)
    args, rest = parser.parse_known_args(argv)
    builtin = {
        "doctor": cmd_doctor, "up": cmd_up, "down": cmd_down, "ci": cmd_ci,
        "secret-scan": cmd_secret_scan, "progress": cmd_progress,
    }
    if args.cmd in builtin:
        return builtin[args.cmd](args, rest)
    return delegated(args.cmd, rest)


if __name__ == "__main__":
    sys.exit(main())
