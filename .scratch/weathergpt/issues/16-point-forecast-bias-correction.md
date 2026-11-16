# 16: Point-forecast bias correction (optional ML training)

**What to build:** A trained correction makes the model-guidance point forecasts closer to observations at specific places, is evaluated honestly against the raw model, and is used only where it wins.

**Blocked by:** 07

**Owner:** aman | **Reviewer:** ashwin

**Status:** ready-for-agent

- [ ] Training data is assembled from the sources in the ML plan, with licences recorded: a forecast archive plus observation targets (IMD AWS/ARG observations if access is granted, otherwise ERA5-Land or IMD gridded rainfall)
- [ ] A time-split evaluation reports MAE and RMSE for temperature and POD, FAR and CSI for rain events, against the raw model, persistence and climatology baselines
- [ ] A rain-probability reliability diagram is produced
- [ ] The corrected value is used only for the variables and lead times where it beats the raw model on held-out data
- [ ] Corrected output is labelled as model guidance and never overrides an official forecast
- [ ] The model version and training window are recorded with each served value
