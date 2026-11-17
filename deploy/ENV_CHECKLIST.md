# Production Deployment Environment Checklist (Human Step)

Before executing `deploy/deploy.sh` on the production VM, ensure every item on this checklist is verified.

> **CRITICAL NOTE**: Per project security rules, **never** commit `.env.production` or actual secret values to Git.

## Environment Variables Checklist

| Variable | Required? | Source / Description | Checked? |
|---|---|---|---|
| `ENV` | Yes | Set to `production` | [ ] |
| `TZ` | Yes | Set to `Asia/Kolkata` | [ ] |
| `PUBLIC_BASE_URL` | Yes | `https://weathergpt.in` | [ ] |
| `ALLOWED_ORIGINS` | Yes | `https://weathergpt.in` | [ ] |
| `DB_PASSWORD` | Yes | High-entropy random password (32+ characters) | [ ] |
| `ADMIN_TOKEN` | Yes | Secret token for Admin Console (`/v1/admin/`) | [ ] |
| `GROQ_API_KEY` | Optional / Recommended | API key from Groq Console for Llama 3.3 / 3.1 | [ ] |
| `OPENROUTER_API_KEY` | Optional / Fallback | OpenRouter API key for fallback LLM routing | [ ] |
| `BHASHINI_ULCA_API_KEY` | Optional | Bhashini ULCA key for Indian language voice TTS/ASR | [ ] |
| `SARVAM_API_KEY` | Optional | Sarvam AI API subscription key | [ ] |
| `VAPID_PUBLIC_KEY` | Yes | Web Push VAPID public key | [ ] |
| `VAPID_PRIVATE_KEY` | Yes | Web Push VAPID private key | [ ] |
| `IMD_ENABLED` | Yes | Set to `false` until official IMD API key arrives | [ ] |
| `IMD_API_KEY` | No | Leave blank until `team/status.md` says yes | [ ] |

## VM Security & Network Hardening
- [ ] Inbound Ports 80 (HTTP) and 443 (HTTPS) open to internet.
- [ ] Port 22 (SSH) restricted to authorized admin IP or bastion host.
- [ ] Ports 5432 (PostgreSQL) and 6379 (Redis) **NOT** exposed to public internet (bound to Docker internal bridge only).
- [ ] DNS A records for `weathergpt.in` and `api.weathergpt.in` pointing to the VM public IP.
