# 21: Admin console

**What to build:** A token-protected admin area where an editor can change glossary terms and alert templates per language, with versions, an audit log and a required reviewer name, so wording stays vetted.

**Blocked by:** 05

**Owner:** ashwin | **Reviewer:** pradeep

**Status:** ready-for-agent

- [ ] Admin pages and API endpoints for glossary and alert templates, protected by the admin token and never reachable without it
- [ ] Every change writes an audit entry (who, what, when, before, after) and creates a version that can be rolled back
- [ ] A template cannot go live without a recorded reviewer name (the human sign-off)
- [ ] Changes take effect without a restart, and tests cover role protection and the audit log
