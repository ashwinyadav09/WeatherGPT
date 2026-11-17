# Troubleshooting

When a command or test fails: read the whole error, find the row below, apply the fix, and re-run the narrowest check. After three different failed attempts, write a blocker note and move on (see AUTOPILOT.md).

## Setup and environment
| Symptom | Likely cause | Fix |
|---|---|---|
| `docker: command not found` or daemon not running | Docker not installed or not started | Run `python scripts/dev.py doctor`; list it in SETUP_NEEDED.md; continue with parts that do not need Docker (unit tests, front end) |
| `make: command not found` (Windows) | No make | Use `python scripts/dev.py <command>` instead |
| Port already in use (5432, 6379, 8000, 5173) | Another process | Stop it, or change the host port in docker-compose.override.yml |
| Python is not 3.12 | Wrong interpreter | Use `py -3.12` or pyenv; build inside Docker |
| `npm ERR! ERESOLVE` | Peer dependency conflict | Pin compatible versions; use `--legacy-peer-deps` only as a last resort and note it |
| Playwright browsers missing | Not installed | `npx playwright install --with-deps chromium` (on Windows omit `--with-deps`) |
| CRLF line-ending errors in scripts | Windows checkout | `.gitattributes` forces LF; run `git add --renormalize .` |
| `eccodes` or `cfgrib` import errors | GRIB library missing on host | Run the work inside the worker container; never install on the host |
| Out of memory in ingest | Whole globe loaded | Subset the India box (lat 6 to 38, lon 68 to 98) and the needed variables first; open Zarr lazily |

## Database and services
| Symptom | Likely cause | Fix |
|---|---|---|
| API starts before Postgres is ready | No health wait | Add a healthcheck and `depends_on: condition: service_healthy` |
| `extension "postgis" does not exist` | Wrong image | Use postgis/postgis and `CREATE EXTENSION IF NOT EXISTS postgis` in the first migration |
| Alembic: multiple heads | Two branches added migrations | `alembic merge heads`, rename in order, re-run migrations; see docs/team.md migration rule |
| Async SQLAlchemy errors on lazy load | Implicit IO | Use `selectinload` or explicit queries |
| Redis connection refused in tests | Service not up | Use the Compose test profile or a fake only at the process boundary |

## Calling outside systems
| Symptom | Likely cause | Fix |
|---|---|---|
| 429 Too Many Requests | Rate limit | Cache by place cell and hour; exponential backoff; for Open-Meteo stay under the free limits |
| SSL or timeout errors to Indian government sites | Slow or odd certificates | Retry with a longer timeout; do not disable verification globally; if a host needs a CA bundle, add it in the image |
| SACHET XML parse error | Namespace or encoding | Use defusedxml with namespace maps; decode as UTF-8; log the item URL |
| CAP polygon in the wrong place | lat,lon read as lon,lat | Swap when converting to GeoJSON; add a geometry test |
| IMD colour appears inverted | Endpoint ordering differs | Use the explicit per-endpoint mapping and its test |
| LLM says tools are unsupported | Model lacks tool calling | Switch to the next candidate model in config/models.yaml |
| LLM returns malformed tool arguments | Weak model | One repair attempt, then the templated answer; consider a stronger model |
| Streaming stops midway | Provider drop | Retry once; fall back to the other provider |
| Bhashini 401 or 403 | Stale config key | Refresh the pipeline config and retry once |
| Speech provider slow | Remote latency | Timeout and fall back to the second provider |
| Open-Meteo returns nulls | Variable not available for the model | Choose another variable or model; handle null explicitly |

## Browser and front end
| Symptom | Likely cause | Fix |
|---|---|---|
| Microphone permission never appears | Not HTTPS or localhost | Serve over HTTPS or use localhost |
| Recorded audio rejected by ASR | webm or mp4 format | Convert with ffmpeg to 16 kHz mono WAV on the server |
| Push never arrives | Not HTTPS, no service worker, expired subscription | Check registration, permission and VAPID keys; delete on 404 or 410 |
| CORS errors in dev | API origin differs | Use the Vite proxy or set ALLOWED_ORIGINS |
| Hindi text shows boxes | Font missing | Load Noto Sans Devanagari subset and set the lang attribute |
| Stale content after deploy | Old service worker | Bump the cache version; show the update prompt |
| Flaky Playwright tests | Timing | Wait on roles or network idle, not sleeps; freeze time |
| Axe contrast failures | Token pair too low | Adjust the token, not the test |

## Tests and evals
| Symptom | Likely cause | Fix |
|---|---|---|
| Tests pass locally, fail in CI | Missing service, env var or timezone | Reproduce in a clean container; set TZ=UTC; use recorded fixtures only |
| Golden set drops | Prompt, model or glossary change | Diff the failing cases; revert the last change; fix and re-run |
| Date-dependent failures | Real clock used | Inject the clock; use the `now` in the case |
| Expected value copied from code output | Tautological test | Take it from the fixture instead |

## Git and GitHub
| Symptom | Likely cause | Fix |
|---|---|---|
| Push rejected (non-fast-forward) | Branch behind | `git fetch` then `git rebase origin/main`; then `git push --force-with-lease` on your own branch only |
| Push to main rejected | Branch protection | Open a pull request instead |
| `gh` not found or not logged in | Not set up | Continue locally; write the PR text to `.scratch/weathergpt/pr/<branch>.md`; note it under human-only steps |
| Merge conflict | Parallel edits | Use the resolve-merge-conflicts skill; rerun tests afterwards |
| Secret committed by mistake | Key in a file | Rotate the key at once, remove it from history with the secret-scan guidance in docs/team.md, tell Ashwin |
| CI red on a docs-only change | Lint rules | Run `python scripts/dev.py lint` and fix |
