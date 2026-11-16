# 0002: Consume national and global model output; do not compete with it

**Status:** accepted (6 November 2026)

**Context:** IMD runs a 6 km global model (BharatFS) and publishes village-level forecasts. ECMWF and NOAA publish open global output.

**Decision:** IMD products are primary for India. WeatherGPT ingests GFS and ECMWF IFS/AIFS itself as independent guidance, ensembles, fallback and climatology support, through one model-output contract with an adapter per source. Partner-supplied WRF output can join through the same contract; WeatherGPT does not run WRF in the pilot.

**Consequences:** No HPC is needed. The value sits in integration, explanation and fallback. Disagreements between sources are shown, never silently averaged.
