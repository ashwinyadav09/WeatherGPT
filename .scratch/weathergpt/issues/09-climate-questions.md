# 09: Climate questions

**What to build:** A user can ask how a month or season compares with the long-term normal for their place and get an anomaly, a percentile, counts of days above a threshold or a simple trend, with the dataset, period and resolution named and caveats stated.

**Blocked by:** 07

**Owner:** aman | **Reviewer:** ashwin

**Status:** ready-for-agent

- [ ] Climatology is precomputed for India on the same grid as the model store
- [ ] The ClimateService returns normals, anomalies, percentiles, threshold counts and simple trends with method notes
- [ ] Every answer names dataset, period and resolution and warns on short or inhomogeneous records
- [ ] An independent notebook agrees with the service on at least 20 cases
- [ ] The LLM runs no free-form code against data
- [ ] Golden cases for this question type pass
