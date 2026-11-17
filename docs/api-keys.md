# APIs and keys

## The short version
- **Three keys matter:** the IMD API (applied for, pending), Bhashini (Indian-language speech and translation) and one LLM (you already have Groq and OpenRouter). Do Bhashini now; it is self-service.
- **Optional, recommended:** Sarvam (stronger Indic speech and a fallback LLM) and the Copernicus climate data service (ERA5, for climatology and model training).
- **No key needed:** SACHET alert feeds, ECMWF open data, NOAA GFS, AviationWeather.gov and Open-Meteo's free non-commercial tier.
- **Self-generated:** a Web Push (VAPID) key pair.
- Keep every key on the server in environment variables. Browser code never sees a key.

## Required for the full pilot

The IMD key is applied for and pending (14 November 2026). The build does not wait for it: Open-Meteo is the first forecast source and SACHET carries IMD's warnings until it arrives.

| Need | Service | Key | How to get it | Cost and limits |
|---|---|---|---|---|
| Official forecasts, nowcasts, warnings, panchayat forecasts, agromet advisories | IMD API platform (api.imd.gov.in) | Yes (JWT) | Register on the portal. IMD's API document tells organisations to contact its nodal officer (Dr. Sankar Nath, Sc-E, sankar.nath@imd.gov.in, as listed in that document; confirm it is current). State the non-commercial, public-interest purpose and your team or college. | Free for non-commercial use per IMD's RTI reply (see the research report); production or commercial use needs IMD's agreement |
| Official alerts | NDMA SACHET RSS feeds (CAP 1.2) | No | Public feeds per country and per state | Free; reuse terms to confirm |
| LLM (understand, call tools, explain) | Groq and/or OpenRouter (both OpenAI-compatible) | Yes (you already have both) | Create keys in each dashboard; set the base URL and key in the environment | Check each provider's free-tier limits and data policy before sending real users' text; free models may log prompts. Pick models that support tool calling and test Hindi on the golden set. Keep model IDs in configuration. |
| Indian-language speech (ASR, TTS) and translation | Bhashini | Yes: user ID and API key; the inference key comes back from a pipeline-config call | Register at bhashini.gov.in/ulca, confirm your email, log in, open My Profile, generate an API key and note the user ID | Free to register; check quotas and terms for production; reliability and latency vary, so keep a fallback |
| Hosting | One India-region VM, a domain, TLS (Let's Encrypt) | No API key | Any provider | VM and domain cost |

Use at least one LLM. Sarvam's chat models can serve as the Indic fallback if Hindi quality on the golden set is weak.

## Best suited for this project

| Function | Best pick | Why | Backup |
|---|---|---|---|
| India forecasts and warnings | IMD API | Authoritative and hyperlocal (panchayat level) | None |
| Alerts | SACHET plus the IMD warning APIs | Source of record for official alerts | None |
| Global model guidance | ECMWF open data (IFS and AIFS, 0.25 degrees) | Strongest open global skill; no key; CC-BY-4.0 | NOAA GFS as a second opinion; Open-Meteo for prototyping |
| Climate and history | ERA5 through the Copernicus CDS (free key) | Long, consistent record for normals and training data | Open-Meteo archive (no key, non-commercial); IMD gridded data once access is confirmed |
| LLM | OpenRouter for the main model and Groq for fast routing turns, both through one OpenAI-compatible adapter | You already have both keys; OpenRouter reaches many models with one key and Groq is very fast, which helps the latency target | Sarvam-30B or 105B as the Indic fallback; Gemini if you add a key; open weights later for offline use |
| Speech | Bhashini first; Sarvam Saaras (speech to text) and Bulbul v3 (text to speech) as the quality fallback | Bhashini is free and covers 22 languages; Sarvam adds quality and streaming | AI4Bharat open models self-hosted later |
| Maps | MapLibre GL JS with self-hosted Protomaps tiles | No key and no per-view cost | MapTiler free tier (key) |
| Place search | Photon or Nominatim self-hosted on an India extract, plus the government local-government directory for district, block and panchayat lists | No key and no rate-limit surprises | Public Nominatim for light testing only |
| Browser alerts | Web Push with your own VAPID keys | No vendor needed | Email or Telegram later |

## What it costs
- Nearly everything above is free to start. Likely spend: a VM, a domain, and LLM or TTS use beyond free credits.
- Sarvam gives signup credits (the newest docs say 100 rupees, other pages say 1,000; check the dashboard). Speech to text is about 30 rupees per hour of audio and Bulbul v3 about 30 rupees per 10,000 characters. Prices have changed several times, so confirm before budgeting.

## Where each key is first needed

| Ticket | Needs |
|---|---|
| 01a, 01b | Example env file; live samples from SACHET and Open-Meteo (no key); IMD fixtures from documented samples |
| 02 | LLM key (Open-Meteo needs none) |
| 03 | Place data |
| 04 | LLM key |
| 05 | SACHET feeds (no key), VAPID keys |
| 06 | Bhashini, Sarvam (second provider) |
| 07 | ECMWF and GFS (no key) |
| 09 | Copernicus key or the Open-Meteo archive |
| 10 | None (curated guidance) |
| 14 | AviationWeather.gov (no key) |
| 17, 18, 19 | IMD key |

## Key handling
- Use environment variables or a secret manager; commit only `.env.example`, with names and no values.
- Keep keys server-side; the browser talks to your backend, never to a provider.
- Use one key per environment, rotate any key that leaks, and set provider usage alerts.
- Respect limits: Open-Meteo free tier under 10,000 calls a day; AviationWeather.gov 100 requests a minute. Cache first.
