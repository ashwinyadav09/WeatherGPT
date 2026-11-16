---
name: add-data-source
description: Add or change an adapter for an external data source (IMD, SACHET, WIS2, GFS, ECMWF, METAR, climate archives). Use when a ticket introduces a new feed or API, or when an upstream format changes.
---

# Add a data source

1. Record dated fixtures from live samples of the source. If a key is pending, build fixtures from the example responses in the source's documentation, label them documented-sample, and record live fixtures once the key arrives. Done when the fixtures replay offline.
2. Add the source to the licence register: terms, limits, attribution text. Done when the Licences screen lists it.
3. Write the conformance test for the adapter and watch it go red.
4. Implement the adapter so it returns evidence packets with the right authority tier. Map codes, units and time zones explicitly. Done when the conformance suite is green.
5. Add a freshness check and a metric for the source. Done when the status dashboard shows it.
6. Add one scheduled contract check for the job that touches the live API.

Done means: conformance green, fixtures replay, licence entry present, freshness metric visible.
