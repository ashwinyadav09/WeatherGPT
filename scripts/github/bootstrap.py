#!/usr/bin/env python3
"""Set up the GitHub side of WeatherGPT: labels, milestones, issues, CODEOWNERS, branch protection, invites.

Usage
  python scripts/github/bootstrap.py --dry-run                 preview everything, change nothing
  python scripts/github/bootstrap.py                           labels, milestones, issues, CODEOWNERS
  python scripts/github/bootstrap.py --protect --invite        also protect main and invite the team

Needs the GitHub CLI (gh), logged in with 'gh auth login', and team/members.csv filled in with GitHub
usernames. Safe to re-run: it skips what already exists. Writes team/issue-map.json.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ISSUES = ROOT / ".scratch" / "weathergpt" / "issues"
TEAM = ROOT / "team"
CODEOWNERS = ROOT / ".github" / "CODEOWNERS"
TICKET_ID = r"\d{2}[a-c]?"

LABELS = [
    ("ticket", "0E8A16", "A tracer-bullet ticket"),
    ("status:ready", "1D76DB", "Ready to start"),
    ("status:blocked", "B60205", "Waiting on something"),
    ("status:in-progress", "FBCA04", "Being worked on"),
    ("status:in-review", "5319E7", "Pull request open"),
    ("status:done", "0E8A16", "Merged"),
    ("owner:ashwin", "BFD4F2", "Owned by Ashwin"),
    ("owner:aman", "BFD4F2", "Owned by Aman"),
    ("owner:pradeep", "BFD4F2", "Owned by Pradeep"),
    ("needs:ashwin", "C5DEF5", "Needs a change in Ashwin's area"),
    ("needs:aman", "C5DEF5", "Needs a change in Aman's area"),
    ("needs:pradeep", "C5DEF5", "Needs a change in Pradeep's area"),
    ("needs:imd-key", "F9D0C4", "Waits for the IMD API key"),
    ("contract", "D93F0B", "Changes shared contracts"),
    ("human-only", "FEF2C0", "An agent cannot do this"),
    ("optional", "EDEDED", "Optional or later work"),
    ("bug", "D73A4A", "Something is broken"),
] + [(f"wave:{n}", "C2E0C6", f"Build wave {n}") for n in range(8)]


def sh(args, dry, input_text=None, check=True):
    line = "$ " + " ".join(args)
    if dry:
        print("[dry-run] " + line)
        return ""
    result = subprocess.run(args, input=input_text, capture_output=True, text=True)
    if result.returncode != 0:
        if check:
            raise RuntimeError(f"{line}\n{(result.stderr or result.stdout).strip()}")
        return None
    return result.stdout.strip()


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_tickets():
    tickets = {}
    for p in sorted(ISSUES.glob("*.md")):
        m = re.match(rf"^({TICKET_ID})-", p.name)
        if not m:
            continue
        body = p.read_text(encoding="utf-8")
        title = re.sub(rf"^#\s*{TICKET_ID}:\s*", "", body.splitlines()[0]).strip()
        tickets[m.group(1)] = {"title": title, "body": body}
    return tickets


def blockers_of(body: str, known) -> list:
    for line in body.splitlines():
        if line.startswith("**Blocked by:**"):
            return [t for t in re.findall(rf"\b{TICKET_ID}\b", line) if t in known]
    return []


def link_blockers(body: str, idmap: dict) -> str:
    out = []
    for line in body.splitlines():
        if line.startswith("**Blocked by:**"):
            line = re.sub(rf"\b{TICKET_ID}\b", lambda m: f"#{idmap[m.group(0)]}" if m.group(0) in idmap else m.group(0), line)
        out.append(line)
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", help="OWNER/REPO (default: the repository of the current folder)")
    ap.add_argument("--dry-run", action="store_true", help="print what would happen, change nothing")
    ap.add_argument("--protect", action="store_true", help="protect the main branch")
    ap.add_argument("--invite", action="store_true", help="invite team members as collaborators")
    ap.add_argument("--skip-issues", action="store_true", help="do not create issues")
    args = ap.parse_args()
    dry = args.dry_run

    if not dry and not shutil.which("gh"):
        print("The GitHub CLI (gh) is not installed. Install it and run 'gh auth login', or use --dry-run.")
        return 1
    if not dry and subprocess.run(["gh", "auth", "status"], capture_output=True).returncode != 0:
        print("gh is not logged in. Run 'gh auth login' first.")
        return 1

    repo = args.repo
    if not repo:
        repo = sh(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"], dry) or "OWNER/REPO"
    print(f"Repository: {repo}")

    members = {r["name"].lower(): r["github"].strip() for r in read_csv(TEAM / "members.csv")}
    missing = [n for n, h in members.items() if not h]
    if missing:
        print("Warning: no GitHub username in team/members.csv for: " + ", ".join(missing))
    assignments = read_csv(TEAM / "assignments.csv")
    tickets = load_tickets()

    # labels
    print("\nLabels")
    for name, color, desc in LABELS:
        sh(["gh", "label", "create", name, "--repo", repo, "--color", color, "--description", desc, "--force"], dry)

    # milestones
    print("\nMilestones")
    existing_ms = set()
    if not dry:
        out = sh(["gh", "api", f"repos/{repo}/milestones?state=all", "--paginate", "-q", ".[].title"], dry, check=False) or ""
        existing_ms = {ln.strip() for ln in out.splitlines() if ln.strip()}
    waves = sorted({r["wave"] for r in assignments}, key=int)
    for w in waves:
        title = f"Wave {w}"
        if title in existing_ms:
            print(f"  exists: {title}")
            continue
        sh(["gh", "api", f"repos/{repo}/milestones", "-f", f"title={title}", "-f", f"description=Build wave {w}"], dry)

    idmap = {}
    if not args.skip_issues:
        print("\nIssues")
        existing = {}
        if not dry:
            out = sh(["gh", "issue", "list", "--repo", repo, "--state", "all", "--limit", "500", "--json", "number,title"], dry, check=False)
            if out:
                existing = {i["title"]: i["number"] for i in json.loads(out)}
        known = set(tickets)
        counter = 0
        for row in assignments:
            t = row["ticket"]
            if t not in tickets:
                print(f"  skip {t}: no ticket file")
                continue
            title = f"{t}: {tickets[t]['title']}"
            if title in existing:
                idmap[t] = existing[title]
                print(f"  exists: #{existing[title]} {title}")
                continue
            owner, reviewer = row["owner"].lower(), row["reviewer"].lower()
            blockers = blockers_of(tickets[t]["body"], known)
            labels = ["ticket", f"owner:{owner}", f"wave:{row['wave']}", "status:blocked" if blockers else "status:ready"]
            if row["kind"] == "key":
                labels.append("needs:imd-key")
            if row["kind"] in ("optional", "later"):
                labels.append("optional")
            body = tickets[t]["body"].rstrip() + (
                f"\n\n---\nOwner: {owner} | Reviewer: {reviewer} | Wave {row['wave']} | Effort {row['effort']} | Kind {row['kind']}\n"
                "Work in a branch named ticket/<NN>-<slug>. See docs/team.md.\n"
            )
            with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as tmp:
                tmp.write(body)
                tmp_path = tmp.name
            cmd = ["gh", "issue", "create", "--repo", repo, "--title", title, "--body-file", tmp_path, "--milestone", f"Wave {row['wave']}"]
            for lab in labels:
                cmd += ["--label", lab]
            if members.get(owner):
                cmd += ["--assignee", members[owner]]
            url = sh(cmd, dry)
            if dry:
                counter += 1
                idmap[t] = 1000 + counter
            else:
                m = re.search(r"/issues/(\d+)", url or "")
                if m:
                    idmap[t] = int(m.group(1))
                    print(f"  created: #{idmap[t]} {title}")

        # second pass: turn ticket numbers in 'Blocked by' lines into issue links
        print("\nLinking blockers")
        for row in assignments:
            t = row["ticket"]
            if t not in idmap or t not in tickets:
                continue
            owner, reviewer = row["owner"].lower(), row["reviewer"].lower()
            body = link_blockers(tickets[t]["body"], idmap).rstrip() + (
                f"\n\n---\nOwner: {owner} | Reviewer: {reviewer} | Wave {row['wave']} | Effort {row['effort']} | Kind {row['kind']}\n"
                "Work in a branch named ticket/<NN>-<slug>. See docs/team.md.\n"
            )
            with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as tmp:
                tmp.write(body)
                tmp_path = tmp.name
            sh(["gh", "issue", "edit", str(idmap[t]), "--repo", repo, "--body-file", tmp_path], dry)
        if not dry:
            (TEAM / "issue-map.json").write_text(json.dumps(idmap, indent=2), encoding="utf-8")
            print("Wrote team/issue-map.json")

    # CODEOWNERS
    print("\nCODEOWNERS")
    text = CODEOWNERS.read_text(encoding="utf-8")
    new_lines = []
    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            new_lines.append(line)
            continue
        for name in ("ashwin", "aman", "pradeep"):
            token = f"@GH_{name.upper()}"
            handle = members.get(name, "")
            line = line.replace(token, f"@{handle}" if handle else "")
        new_lines.append(re.sub(r"\s{2,}$", "", re.sub(r"(\S)\s+$", r"\1", line)))
    new_text = "\n".join(new_lines) + "\n"
    if new_text != text:
        if dry:
            print("[dry-run] would update .github/CODEOWNERS with the GitHub usernames")
        else:
            CODEOWNERS.write_text(new_text, encoding="utf-8")
            print("Updated .github/CODEOWNERS. Commit and push it through a pull request.")
    else:
        print("No change (fill the github column in team/members.csv first).")

    # branch protection
    if args.protect:
        print("\nBranch protection")
        rules = {
            "required_status_checks": {"strict": True, "contexts": ["ci"]},
            "enforce_admins": False,
            "required_pull_request_reviews": {"required_approving_review_count": 1, "dismiss_stale_reviews": True},
            "restrictions": None,
            "allow_force_pushes": False,
            "allow_deletions": False,
            "required_linear_history": True,
        }
        try:
            sh(["gh", "api", "-X", "PUT", f"repos/{repo}/branches/main/protection", "--input", "-"], dry, input_text=json.dumps(rules))
            print("main is protected: pull request, one approval, green 'ci' check, linear history.")
        except RuntimeError as err:
            print("Could not protect main automatically (private repositories on free plans cannot).")
            print(str(err).splitlines()[-1])
            print("Manual: Settings > Branches > Add rule for main > require a pull request with 1 approval, require the 'ci' status check, block force pushes.")

    # invites
    if args.invite:
        print("\nInvites")
        me = sh(["gh", "api", "user", "-q", ".login"], dry, check=False) or ""
        for name, handle in members.items():
            if not handle or handle.lower() == me.lower():
                continue
            try:
                sh(["gh", "api", "-X", "PUT", f"repos/{repo}/collaborators/{handle}", "-f", "permission=push"], dry)
                print(f"  invited {handle}")
            except RuntimeError as err:
                print(f"  could not invite {handle}: {str(err).splitlines()[-1]}")

    print("\nDone. Next: commit the CODEOWNERS and issue map through a pull request, then each person runs their kickoff prompt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
