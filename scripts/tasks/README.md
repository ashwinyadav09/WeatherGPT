# Task files

`scripts/dev.py` delegates these commands to files in this folder (dashes become underscores):
`test.py`, `lint.py`, `eval.py`, `replay_alerts.py`, `contracts.py`, `acceptance.py`, `contract_checks.py`, `demo.py`, `db_heads.py`.

Each file runs as `python scripts/tasks/<name>.py <extra args>` and exits 0 on success. Ticket 01a creates them; later tickets extend them. Keep the command names stable.
