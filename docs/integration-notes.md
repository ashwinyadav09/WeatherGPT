# Integration notes

Facts for calling outside systems. Items marked (verify) were not confirmed and must be checked against the source's own documentation; the conformance tests will catch differences. Cache first, back off on 429 and 5xx with tenacity, set timeouts (5 s data APIs, 10 s speech, 30 s LLM), and record every source in the licence register.

## SACHET (NDMA alerts), no key
- Country feed: `https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml`. State feeds: `rss_<state>.xml` in the same folder (for example `rss_karnataka.xml`).
- Each RSS item links to a CAP 1.2 XML file. Polygons are district-level and written as lat,lon pairs (GeoJSON wants lon,lat). The feed has no point query and no CORS, so fetch server-side.
- Parse with defusedxml. Handle msgType Alert, Update and Cancel through references; ignore status Test and Exercise in production. Accept only the sachet.ndma.gov.in host.
- Poll every 1 to 2 minutes with conditional requests if supported. Save at least 20 real CAP samples as fixtures. If no cyclone sample exists, add a synthetic one modelled on real CAP structure and label it provenance=synthetic.
- WMO Alert Hub (`https://www.alert-hub.org/`) also aggregates CAP feeds.

## Open-Meteo, no key (non-commercial, under 10,000 calls a day, CC BY 4.0)
- Forecast: `https://api.open-meteo.com/v1/forecast?latitude=..&longitude=..&hourly=temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,wind_speed_10m,wind_gusts_10m&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max&current=temperature_2m,precipitation&timezone=Asia%2FKolkata&forecast_days=10`. The response includes elevation.
- Archive (ERA5 and others): `https://archive-api.open-meteo.com/v1/archive`. Historical forecast: `https://historical-forecast-api.open-meteo.com/v1/forecast`. Previous runs: `https://previous-runs-api.open-meteo.com/v1/forecast` with variables such as `temperature_2m_previous_day1`.
- Geocoding: `https://geocoding-api.open-meteo.com/v1/search?name=..&language=hi&count=10`.
- Cache by place cell and hour; never call per keystroke. Attribute Open-Meteo in the app.

## IMD API (key pending)
- Reference with example responses: `https://api.imd.gov.in/public/api_reference.html`. Key-based access with JWT.
- About 28 endpoints: city forecast (7 day), district and station nowcasts, district and sub-division warnings, AWS and ARG observations, current weather, weather at your location (Mausamgram), river basin QPF, port warnings, sea area and coastal bulletins, fishermen warnings, cyclone track and cone, sun and moon, highway nowcasts, radar images, lightning, agromet advisory, seasonal forecast.
- Quirks to code for: colour codes are opposite between endpoints (nowcast 1 green to 4 red; district warnings 1 red to 4 green); times mix UTC, IST and HHmm; some payload field names contain typos. Parse each field with an explicit rule and test it.
- Free for non-commercial use only. Rate limits are unknown, so cache 15 minutes and back off.
- Until the key arrives: build adapters from the example responses, label fixtures documented-sample (or spec-only), keep IMD_ENABLED=false.

## LLM providers (OpenRouter and Groq, both OpenAI-compatible)
- Base URLs: `https://openrouter.ai/api/v1` and `https://api.groq.com/openai/v1`. POST `/chat/completions` with model, messages, tools, tool_choice and stream. Bearer key in the Authorization header. OpenRouter accepts optional HTTP-Referer and X-Title headers.
- OpenRouter lists models at `/models`; filter for tool support with the supported_parameters field (verify). On Groq, test a tool call to confirm a model supports tools.
- Handle: 429 (exponential backoff, then fall back to the other provider), a model that rejects tools (switch to the next candidate), malformed tool arguments (one repair attempt, then a templated answer), streaming drops (retry once).
- Model selection step: run the golden cases for tool calls (at least 30 English and 30 Hindi) on up to three candidate models for the main and fast roles, pick the cheapest that meets the thresholds, and write the result and reasons to `config/models.yaml`.

## Bhashini (speech and translation)
- Docs: `https://bhashini.gitbook.io/bhashini-apis/pre-requisites-and-onboarding`.
- Flow: register on the ULCA site, generate an API key, note the user ID. A config call with those returns the inference endpoint, an inference key and the service ids for each task and language. Then call the pipeline inference endpoint with that key. ASR takes base64 audio and a sampling rate; TTS returns base64 audio.
- Cache the config response; refresh it on 401 or 403. Send 16 kHz mono WAV for ASR. Timeout 10 s, then fall back to Sarvam.
- Language codes: hi, bn, ta, te, mr, gu, kn, ml, pa, or, en.

## Sarvam (primary speech provider and Indic AI) (ADR 0012, docs.sarvam.ai)
- Base URL: `https://api.sarvam.ai`, auth header: `api-subscription-key: <SARVAM_API_KEY>`.
- Speech-to-Text (ASR):
  - Endpoint: `POST https://api.sarvam.ai/speech-to-text`
  - Content-Type: `multipart/form-data`
  - Parameters:
    - `file`: WAV audio bytes (16 kHz 16-bit mono PCM recommended, formats: wav, mp3, aac, flac).
    - `model`: `saaras:v3`
    - `language_code`: BCP-47 with region subtag: `hi-IN`, `bn-IN`, `ta-IN`, `te-IN`, `mr-IN`, `gu-IN`, `kn-IN`, `ml-IN`, `pa-IN`, `od-IN`, `en-IN`, or `unknown`.
  - Response: `{"transcript": str, "confidence": float, "words": [...]}`.
- Text-to-Speech (TTS):
  - Endpoint: `POST https://api.sarvam.ai/text-to-speech`
  - Content-Type: `application/json`
  - Parameters:
    - `inputs`: list of text strings (max 2,500 characters per request).
    - `target_language_code`: `hi-IN`, `bn-IN`, `ta-IN`, `te-IN`, `mr-IN`, `gu-IN`, `kn-IN`, `ml-IN`, `pa-IN`, `od-IN`, `en-IN`.
    - `speaker`: `meera` (female default), `arvind` (male), `pavithra`, `amol`, `amartya`.
    - `pitch`: 0 (-1.0 to 1.0).
    - `pace`: 1.0 (0.5 to 2.0).
    - `loudness`: 1.5 (0.5 to 2.0).
    - `speech_sample_rate`: 16000 (options: 8000, 16000, 22050).
    - `enable_preprocessing`: true.
    - `model`: `bulbul:v3`.
  - Response: `{"audios": ["<base64_encoded_audio>"]}`.
- Translation:
  - Endpoint: `POST https://api.sarvam.ai/translate`
  - Content-Type: `application/json`
  - Parameters: `input` (str), `source_language_code` (`en-IN`), `target_language_code` (`hi-IN`), `model` (`mayura:v1`), `mode` (`formal` or `code-mixed`).
  - Response: `{"translated_text": str}`.

## Web Push
- Generate a VAPID key pair once. The browser registers a service worker, asks permission (after explaining why), and sends its PushSubscription to POST /v1/push/subscribe. The worker sends with pywebpush; payload under about 4 KB; set a TTL and urgency high for red alerts.
- Delete a subscription when the push service answers 404 or 410. Push needs HTTPS (localhost is fine for development). Safari on iPhone supports it only for sites added to the home screen (verify).

## Model data
- ECMWF open data (no key): the `ecmwf-opendata` Python client; IFS and AIFS at 0.25 degrees, cycles 00, 06, 12, 18 UTC, GRIB2. Check the client's README for the AIFS model names (verify). Subset to the India box (about lat 6 to 38, lon 68 to 98) and the needed variables before converting to Zarr.
- GFS history and latest (no key): dynamical.org Zarr at `https://data.dynamical.org/noaa/gfs/forecast/latest.zarr`, or `s3://dynamical-noaa-gfs` with anonymous access. Open with xarray and subset the India box first. CC BY 4.0 attribution.
- Run GRIB work only inside the worker container.

## Observations and history
- IEM METAR archive (no key): `https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py` with parameters station, data (tmpf, relh, sknt, drct and so on), year1 to day2, tz=Etc/UTC, format=onlycomma. Indian airports are in network IN__ASOS. Little quality control; METAR rain is unreliable.
- AviationWeather.gov (no key): `https://aviationweather.gov/api/data/metar?ids=VIDP&format=json`, and taf and airsigmet endpoints. At most 100 requests a minute and one a minute per thread per endpoint.
- IMD gridded data: daily rainfall 0.25 degrees from 1901 and temperature 1 degree from 1951, binary files from IMD Pune; the server can be unavailable at times.
- ERA5: Open-Meteo archive (no key) or Copernicus CDS (free key, `cdsapi`).

## Place names
- GeoNames dumps (`https://download.geonames.org/export/dump/`: IN.zip and alternateNamesV2.zip) give Indian places with coordinates and names in Indic scripts (CC BY 4.0, verify). Build the seed gazetteer from them and fall back to Open-Meteo geocoding for misses.
