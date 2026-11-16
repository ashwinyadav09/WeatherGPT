# 22: Demo, docs and deployment pack

**What to build:** Everything needed to show and run the finished project: seeded demo data with a scripted demo that shows each evaluation parameter, developer and operator documentation, a deployment guide and scripts for one India-region VM, and a single acceptance command that reports every gate.

**Blocked by:** 12, 20, 21

**Owner:** ashwin | **Reviewer:** aman

**Status:** ready-for-agent

- [ ] Demo data and a scripted demo that follows the demo script in docs/eval-and-acceptance.md
- [ ] A developer README, an architecture diagram (mermaid) and a runbook (restarts, backups, key rotation, source outages)
- [ ] A deployment guide and scripts: Compose production profile with Caddy TLS, backups and an environment checklist; nothing is deployed (human step)
- [ ] `python scripts/dev.py acceptance` prints a pass or fail table for every gate and stores the output
- [ ] HANDOFF.md written: what works, what is stubbed, what each human-only step needs
