# 01b: Fixtures and spikes

**What to build:** Recorded, dated, labelled data so that every other ticket can be built and tested offline: live samples from SACHET, Open-Meteo, AviationWeather.gov and the IEM METAR archive; a GeoNames place seed; and IMD fixtures built from the example responses in IMD's published API reference while the key is pending. A notes file records what each source really returns and its quirks.

**Blocked by:** None (can start immediately; works in the fixtures folder and docs only)

**Owner:** aman | **Reviewer:** ashwin

**Status:** ready-for-agent

- [ ] At least 20 real CAP samples from SACHET feeds (country and several states), including Update and Cancel examples if present, each stored with its source URL and date, plus a synthetic cyclone-style sample modelled on real structure and labelled provenance=synthetic
- [ ] Open-Meteo forecast, archive and geocoding samples for at least 10 Indian places, including places with Hindi names, recorded with the request URL and date
- [ ] AviationWeather.gov METAR and TAF samples for at least 5 Indian aerodromes, and IEM METAR samples for 5 stations
- [ ] A GeoNames India seed (names including Hindi and other Indic names, coordinates) built under its licence, with a script that rebuilds it
- [ ] IMD fixtures from the example responses in IMD's API reference, one per endpoint that has an example, labelled documented-sample (spec-only where none exists), with a list of which endpoints fall in each group
- [ ] A fixture index (source, file, provenance, date, URL) and a loader that tests can use; every fixture file carries a provenance label
- [ ] A notes file records real field names, units, time zones, quirks and rate limits observed
- [ ] No fixture contains a key or personal data
