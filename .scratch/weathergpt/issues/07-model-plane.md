# 07: Model plane

**What to build:** WeatherGPT ingests GFS and ECMWF IFS/AIFS on schedule, answers point forecasts from them with full provenance, shows disagreement with the official forecast, and keeps answering, clearly labelled, when IMD's service is down or not yet connected. While the IMD key is pending, this is the main independent source next to Open-Meteo.

**Blocked by:** 01a, 01b

**Owner:** aman | **Reviewer:** ashwin

**Status:** ready-for-agent

- [ ] Scheduled ingest of GFS and ECMWF IFS/AIFS into a model-output store with model, cycle and lead-time provenance
- [ ] Both sources pass the same adapter conformance suite
- [ ] Point forecasts use interpolation and elevation correction and agree with an independent extraction library within a stated tolerance
- [ ] Ensemble spread feeds the uncertainty phrasing
- [ ] Material disagreement with the official forecast is shown with both labelled
- [ ] A fallback drill (IMD adapter forced down using fixtures) returns a labelled model-guidance answer
- [ ] Attribution appears in the app, and any Open-Meteo use stays inside its free limits through caching
