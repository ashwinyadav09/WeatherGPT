---
trigger: always_on
description: Non-commercial product; attribution and rate-limit rules for every data source.
---

# Licensing and attribution

- Keep the product non-commercial: no ads, payments, paid tiers or resale of source data. If that changes, stop and raise it, because the IMD and Open-Meteo terms assume non-commercial use.
- Attribute every source in the app and API: IMD, NDMA SACHET, ECMWF (CC-BY-4.0), dynamical.org (CC BY 4.0), Open-Meteo (CC BY 4.0), OpenStreetMap (ODbL).
- Stay inside limits: Open-Meteo free tier under 10,000 calls a day, 5,000 an hour and 600 a minute; AviationWeather.gov 100 requests a minute and one a minute per thread per endpoint. Cache first.
- Use official APIs and feeds; leave pages that forbid scraping alone.
- Record every source in the licence register with terms, limits and attribution text; show it on the app's Licences screen.
