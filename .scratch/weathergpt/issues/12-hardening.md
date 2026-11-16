# 12: Hardening

**What to build:** The pilot holds up under load, passes accessibility and security review, and can be deployed repeatably with a visible cost per query.

**Blocked by:** 05, 06, 07, 08, 09, 10, 20, 21

**Owner:** ashwin | **Reviewer:** aman

**Status:** ready-for-agent

- [ ] Load tests meet the targets: 10,000 concurrent chats, 1,000 concurrent voice sessions, and a simulated alert fan-out to one million devices within five minutes
- [ ] The prompt-injection suite and a security review pass
- [ ] A WCAG 2.2 AA audit (automated axe checks plus screen-reader tests with NVDA and TalkBack in Chrome) passes, including on a low-end Android phone
- [ ] A DPDP checklist is complete: itemised consent in the user's language, deletion path, breach runbook, grievance contact
- [ ] A cost dashboard shows cost per 1,000 text queries and per voice minute
- [ ] Kubernetes manifests, backups and a blue-green deploy path exist
- [ ] Load, regression and evaluation gates are re-run after tickets 17 to 19 land, so they cover the IMD adapters
