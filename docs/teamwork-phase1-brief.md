# WeatherGPT: /teamwork Phase 1 brief

Optional: use this only if you choose /teamwork (paid plans). The recommended path is the normal agent with your kickoff prompt in team/prompts. Paste this into /teamwork. It states what to build; architecture lives in AGENTS.md, the rules and docs/adr/.

## Scope and objectives
Build a pilot of WeatherGPT: a grounded, multilingual, voice-first weather assistant for India (non-commercial). Hindi and English first. A responsive website installable as a progressive web app. Pilot users in Uttar Pradesh and Maharashtra; the data layer covers all of India. The IMD API key is pending: build IMD adapters behind a flag against documented samples, use Open-Meteo as the first forecast source, and name the real source in every answer. Read `.scratch/weathergpt/SPEC.md` for the spec and `.scratch/weathergpt/issues/` for tickets 01a to 22 (15 and 16 are optional ML tickets; 17 to 19 wait for the IMD key) with their blocking edges.

## Requirements and independent verification
1. Grounded answers: every number traces to an evidence packet and passes the verifier. *Check:* golden set plus adversarial wrong-number cases built from recorded fixtures.
2. Places: district, block and panchayat names in Indic scripts resolve correctly. *Check:* place golden set (95 percent top-1 at district level, 85 percent at panchayat level).
3. Hindi and English: intent and slot accuracy of at least 95 percent on 300-case golden sets. *Check:* the eval command (`python scripts/dev.py eval --lang hi`); native-speaker sign-off (human step).
4. Relay-only alerts: SACHET and IMD alerts matched to saved places, pushed within 60 seconds at p95, never touched by an LLM. *Check:* replay of at least 10 recorded real alerts with hop timestamps; a test asserting no LLM call in the alert path.
5. Voice: push-to-talk in Hindi with first audio within 3.5 seconds at p95 on 4G. *Check:* WER harness on at least 100 utterances; instrumented timing runs.
6. Model plane and fallback: GFS and ECMWF ingested with provenance; the app falls back to model guidance when IMD is down. *Check:* comparison with an independent extraction library; fallback drill using fixtures.
7. Integration visibility: a status dashboard shows freshness for every source and alert latency. *Check:* dashboard values match injected delays.
8. Climate: normals, anomalies and percentiles for a place and period. *Check:* an independent notebook agrees on at least 20 cases.
9. Advisories: IMD agromet advice summarised with citation for wheat and rice, plus official heat and cold-wave guidance. *Check:* scenario tests; domain reviewer sign-off (human step).
10. Non-functional: load, accessibility (WCAG 2.2 AA), security and cost targets from the spec. *Check:* load tests, accessibility audit, prompt-injection suite, cost dashboard.
11. Trained models (optional tickets 15 and 16): an intent-and-slot model and a point-forecast bias correction, each used only if it beats its baseline on held-out data. *Check:* golden-set comparison with the LLM-only baseline; time-split evaluation against the raw model and climatology.
12. IMD integration (tickets 17 to 19, after the key arrives): IMD adapters verified against live responses. *Check:* conformance suite on live-recorded fixtures; a written list of differences from the documented samples.

## Acceptance criteria
Every ticket's acceptance boxes ticked; golden-set thresholds met; verifier passes; CI green; licence register complete.

## Working directory
The repository root that contains this pack.

## Integrity mode
Use development while exploring and demo for graded demonstrations. Use benchmark only for isolated algorithm tasks.

## Prove it for real
Exercise real code on recorded fixtures, build answers from evidence, use official APIs and feeds, and keep alert text in vetted templates.
