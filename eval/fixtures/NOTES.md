# Fixtures & Integration Notes (Spike Findings)

This document records the empirical behaviors, real field names, units, time zones, quirks, and rate limits observed across external data feeds for WeatherGPT.

---

## 1. NDMA SACHET (CAP Alerts)

- **Feed URLs**:
  - All-India RSS feed: `https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml`
  - State RSS feeds: `https://sachet.ndma.gov.in/cap_public_website/rss/rss_<state>.xml`
- **Protocol**: CAP 1.2 XML wrapped in RSS item links (`https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile?identifier=<id>`).
- **Observed Field Names & Quirks**:
  - `cap:identifier`: Often prefixed with state code, e.g. `IN-1794853111405010_10`.
  - `cap:msgType`: Observed values: `Alert`, `Update`, `Cancel`. Real feeds frequently use `Update` referencing prior notices via `cap:references`.
  - `cap:sent`, `cap:effective`, `cap:onset`, `cap:expires`: Formatted as ISO 8601 with timezone offset `+05:30` (IST), e.g. `2026-11-16T23:53:24+05:30`.
  - `cap:polygon`: Written as `lat,lon` pairs separated by whitespace (GeoJSON coordinates require `[lon, lat]`).
  - `cap:severity`: `Extreme`, `Severe`, `Moderate`, `Minor`, `Unknown`.
  - Multilingual text: Headline and description are typically in English and local state language.
- **Rate Limits & Caching**:
  - No API key required.
  - Server does not provide CORS headers; ingestion must occur in the backend service worker.
  - Recommended poll frequency: 1 to 2 minutes with conditional HTTP headers (`If-Modified-Since` / `ETag`).

---

## 2. Open-Meteo

- **Endpoints**:
  - Forecast: `https://api.open-meteo.com/v1/forecast`
  - Historical Archive: `https://archive-api.open-meteo.com/v1/archive`
  - Geocoding: `https://geocoding-api.open-meteo.com/v1/search`
- **Observed Field Names & Units**:
  - Temperatures: `temperature_2m`, `temperature_2m_max`, `temperature_2m_min` in degrees Celsius (°C).
  - Precipitation: `precipitation`, `precipitation_sum` in millimetres (mm).
  - Probability: `precipitation_probability`, `precipitation_probability_max` in percent (0–100%).
  - Wind: `wind_speed_10m`, `wind_gusts_10m` in km/h.
  - Elevation: Returned in metres as `elevation`.
  - Time format: ISO 8601 strings without UTC offset when `timezone=Asia/Kolkata` is requested (e.g. `2026-11-17T14:00`). UTC offset seconds provided as `utc_offset_seconds: 19800`.
- **Geocoding**:
  - Query parameter `language=hi` returns Hindi names in the `name` or `admin1` fields.
- **Rate Limits & Attribution**:
  - Non-commercial free tier limit: 10,000 calls/day, 5,000 calls/hour, 600 calls/minute.
  - Attribution: "Weather data by Open-Meteo.com under CC BY 4.0".
  - Cache forecast data by location cell for 15–30 minutes; geocoding for 30 days.

---

## 3. AviationWeather.gov & IEM METAR Archive

- **AviationWeather.gov**:
  - Endpoints: `https://aviationweather.gov/api/data/metar?ids=<ICAO>&format=json` and `/taf`.
  - Units: Temperatures in °C, wind direction in degrees, wind speed in knots, visibility in statute miles or metres.
  - Observed rate limits: Maximum 100 requests/minute, at most 1 request/minute per thread per endpoint.
  - Indian aerodromes: `VIDP` (Delhi), `VABB` (Mumbai), `VOBL` (Bengaluru), `VOMM` (Chennai), `VECC` (Kolkata).
- **IEM (Iowa Environmental Mesonet) ASOS Archive**:
  - URL: `https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py`
  - Indian stations network: `IN__ASOS`.
  - Format: Comma-separated values (CSV) with columns: `station,valid,tmpf,dwpf,relh,drct,sknt,p01i,alti,mslp,vsby,gust,skyc1...`
  - Units: Default IEM returns Fahrenheit (`tmpf`) and knots (`sknt`), UTC timestamps (`valid`). Conversion to °C and km/h required.
  - Note: METAR rainfall reports are often uncalibrated or missing; do not rely on METAR as a primary precipitation source.

---

## 4. IMD API (Documented Reference Analysis)

- **Reference URL**: `https://api.imd.gov.in/public/api_reference.html`
- **Access Protocol**: Key-based access using JWT Bearer authentication (key pending per ADR 0007).
- **Endpoint Groups**:
  1. *Public Forecasts & Warnings*:
     - City forecast 7 days (`/city-forecast`)
     - District nowcast 3-hour (`/nowcast-district`)
     - Station nowcast (`/nowcast-station`)
     - District warnings 5-day (`/warnings-district`)
     - Sub-division warnings (`/warnings-subdivision`)
     - Mausamgram WRF time-series (`/mausamgram`)
  2. *Surface Observations*:
     - AWS automated weather stations (`/aws-data`)
     - ARG automated rain gauges (`/arg-data`)
     - Current weather observatory reports (`/current-weather`)
  3. *Marine & Coastal*:
     - Port warnings (`/port-warning`)
     - Sea area bulletins (`/sea-area-bulletin`)
     - Fishermen warnings (`/fishermen-warning`)
  4. *Severe Weather & Specialized*:
     - Cyclone track and cone (`/cyclone-track`)
     - River basin QPF (`/river-basin-qpf`)
     - Highway nowcasts (`/highway-nowcast`)
     - Agromet district advisory (`/agromet`)
     - Seasonal / long range outlook (`/seasonal-forecast`)
- **Quirks & Irregularities to Code For**:
  - *Color inversion*: Nowcast colour codes range from 1 (Green) to 4 (Red), whereas district warning codes range from 1 (Red) to 4 (Green) in legacy documentation. All adapters must normalize to canonical levels: `green`, `yellow`, `orange`, `red`.
  - *Mixed timestamp representations*: Endpoints mix UTC ISO strings (`2026-11-17T06:00:00Z`), IST strings (`2026-11-17 14:30:00 IST`), and 4-digit military time (`1430`).
  - *Field naming variations*: AWS uses `rain_fall_last_hour_mm`, ARG uses `rainfall_today_mm`, city forecast uses `Rainfall_mm`.
  - *Provenance labels*: All mock/fixture data are strictly labelled `documented-sample` (or `spec-only` where published examples are missing).

---

## 5. GeoNames India Seed

- **Dataset**: Built under GeoNames CC BY 4.0 licence from Indian place dumps (`IN.txt`, `alternateNamesV2.txt`).
- **Storage**: `seeds/places/geonames_india_seed.json` with rebuild automation in `scripts/build_geonames_seed.py`.
- **Fields**: Stable ID, English name, localized Indic script names (Hindi, Marathi, Bengali, Tamil, Telugu, Kannada, Gujarati, Punjabi, Urdu, Odia, Assamese), geographic coordinates, elevation, state, district, kind, population.
