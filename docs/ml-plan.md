# Models: what to use, what to train

## Short answer
Nothing has to be trained to ship the pilot. Pretrained models handle language, speech and retrieval, and official forecasts handle the weather. Training your own weather forecaster would be slower and less accurate than IMD, ECMWF and NOAA output, so do not. Two small models are worth training because they improve the product and give the project real ML content.

## Use as they are (no training)

| Job | Model or service | Notes |
|---|---|---|
| Understanding, tool calling, explaining | A tool-calling model through OpenRouter or Groq, chosen by golden-set results; Sarvam-30B or 105B as the Indic fallback | Facts come from tools, so no fine-tuning for facts |
| Speech to text | Bhashini ASR; Sarvam Saaras v3; AI4Bharat IndicConformer (open) | Test on place names and numbers first |
| Text to speech | Bhashini TTS; Sarvam Bulbul v3; AI4Bharat IndicF5 (open, 11 languages) | Tier A languages only for voice output |
| Translation | Bhashini; AI4Bharat IndicTrans2 (open); Sarvam-Translate | Alerts use vetted templates, not machine translation |
| Retrieval embeddings (advisory documents) | An open multilingual embedding model such as BGE-M3 or multilingual-e5 | Choose by a retrieval test on real advisories |
| Weather forecasts | IMD, ECMWF IFS and AIFS, NOAA GFS | Consumed, never retrained |

## Train these (recommended)

### 1. Intent and slot model (ticket 15)
- **Job:** classify each question (current, forecast, alert, advisory, climate, explain, meta, unsafe) and extract place, time window, crop and units, in Hindi, English and code-mixed text, in milliseconds and without an LLM call.
- **Why:** lower latency and cost, works offline, and gives a measurable accuracy number. The LLM stays for composing answers.
- **Model:** fine-tune a small multilingual encoder (for example MuRIL, IndicBERT or XLM-RoBERTa base) with a classification head and a token-tagging head.
- **Data:** 3,000 to 10,000 labelled utterances. Draft them with an LLM, correct them by hand, add code-mixed and noisy speech-style text, and hold out a golden test set.
- **Compute:** a free Colab or Kaggle GPU is enough.
- **Metrics:** intent accuracy and F1, slot F1; target at least 95 percent on the golden set; compare with an LLM-only baseline on accuracy, latency and cost.
- **Gate:** ship only if it matches the baseline's accuracy at lower latency; otherwise keep LLM routing.

### 2. Point-forecast bias correction (ticket 16)
- **Job:** reduce the systematic error of global model guidance (GFS, IFS, AIFS) at specific places for temperature, humidity, wind and rain occurrence. This is the classic model-output-statistics idea.
- **Model:** gradient-boosted trees (LightGBM or XGBoost) per variable and lead-time band. Inputs: raw forecast, lead time, hour, day of year, elevation, latitude and longitude, ensemble spread and recent error.
- **Data:** observations as targets: IMD AWS/ARG observations if IMD grants access (to verify), otherwise ERA5-Land or IMD gridded rainfall as a proxy. Forecast archive: dynamical.org Zarr archives (verify history length) or your own ingest logs accumulated over time.
- **Compute:** a CPU is enough.
- **Metrics:** MAE and RMSE for temperature; POD, FAR and CSI for rain events (for example 2.5 mm a day or more); a reliability diagram for rain probability. Compare with the raw model, persistence and climatology on a time-split hold-out with no leakage across time.
- **Gate:** use corrected values only where they beat the raw model on held-out data; label them model guidance; never override an official IMD forecast.

## Where to get the data

### Model 1: intent and slot

| Source | What it gives | Where | Terms |
|---|---|---|---|
| MASSIVE (Amazon) | Parallel intent and slot data in 51 languages, including Hindi, Bengali, Kannada, Malayalam, Tamil, Telugu and Urdu. Its weather domain has the weather_query intent with place and descriptor slots | Hugging Face: AmazonScience/massive (one config per locale, for example hi-IN) | CC BY 4.0 |
| Hinglish-TOP | About 10,000 human-annotated Hindi-English code-switched utterances plus about 170,000 machine-generated ones, derived from TOPv2 | Released with the CST5 paper (Agarwal et al.); follow the dataset link there | Check the licence before use |
| SLURP (optional) | The English source of MASSIVE, with audio | github.com/pswietojanski/slurp | Check the licence |
| Your own data | Alert, advisory, climate, explain, meta and unsafe questions in Hindi, English and Hinglish, which no public set covers | Draft with an LLM, then correct by hand | Yours |
| Place names for slot variety | District, block and village names | Government local-government directory lists, IMD station lists, OpenStreetMap | Check each |

How to build the set:
1. Take MASSIVE's weather examples as in-domain seeds and map its labels to this project's labels.
2. Draft your own intents with an LLM: 3,000 to 10,000 questions across Hindi, English and Hinglish, with real place names, crops and date phrases.
3. Add Romanised Hindi and code-mixed variants, plus speech-recognition-style noise.
4. Correct a large share by hand.
5. Write the golden test set separately (at least 300 per language, ideally with native speakers) so it never overlaps training data.

### Model 2: point-forecast bias correction

| Role | Source | Where | Terms |
|---|---|---|---|
| Past forecasts, quick start | Open-Meteo Historical Forecast, Previous Runs and Single Runs APIs | api.open-meteo.com, no key. The archive starts in 2021; previous-run data generally starts in January 2024, with GFS 2 m temperature from March 2021 | Free for non-commercial use under 10,000 calls a day; CC BY 4.0 attribution; self-hostable |
| Past forecasts, full control | dynamical.org NOAA GFS forecast archive (Zarr, 0.25 degrees, forecasts from 1 May 2021) | data.dynamical.org/noaa/gfs/forecast/latest.zarr, or s3://dynamical-noaa-gfs with no account; open with xarray | CC BY 4.0 |
| Past forecasts, from now on | Your own ingest from ticket 07 | Your object store | Yours |
| Station truth | Iowa Environmental Mesonet METAR archive, network IN__ASOS (well over 100 Indian airports): hourly temperature, humidity, wind | mesonet.agron.iastate.edu download portal; R package riem | Free; little quality control; METAR rain is unreliable, so skip it |
| Rain truth | IMD gridded daily rainfall, 0.25 degrees, 1901 to present | Binary files from IMD Pune; R package imdR, or read the files directly in Python | IMD terms; cite IMD |
| Gridded proxy truth | ERA5 and ERA5-Land | Open-Meteo Historical Weather API (no key) or the Copernicus CDS (free key) | Attribution; Open-Meteo is non-commercial |
| Best truth | IMD AWS/ARG station observations | Ask IMD in the same request as the API key | To verify |
| Static features | Elevation and coordinates | Open-Meteo elevation, station metadata | Attribution |

How to build the set:
1. Pick 15 to 20 stations in Uttar Pradesh and Maharashtra plus the major cities; extend later.
2. For each forecast time, pair the forecast (with its lead time) with the observation at the valid time.
3. Start with 2 m temperature and wind; add rain occurrence using IMD gridded rainfall, and score it at the grid-cell scale because a point and a 0.25 degree cell differ.
4. Split by time, never at random: for example train 2021 to 2024, validate 2025, test 2026. Weather models change versions, so record the model version and retrain after major upgrades.
5. About 100 stations over 5 years of hourly rows fits on a laptop, and LightGBM trains in minutes.

### Rules for every dataset
Record each dataset in a manifest (name, date pulled, URL, licence, checksum) and add it to the licence register. Keep scripts and the manifest in the repository, not the raw data. Follow each licence's attribution rule.

## Later and optional
- **Rain-probability calibration** from ensemble spread (isotonic or logistic), after model 2.
- **Weather-domain speech adaptation** for place names and crops, only if baseline errors on place names are high. Try hotword biasing and lexicons first; it needs consented audio.
- **Small open-weights model fine-tune** (QLoRA on a model of 3 billion parameters or fewer, using tool-calling traces from the golden set) for an offline or sovereign tier.
- **Radar nowcasting** (ConvLSTM or U-Net) is a research track that needs radar archives and heavy compute; skip it for the pilot.

## Do not train
- A weather forecasting model from scratch.
- An LLM to memorise weather facts; facts come from tools.
- Anything that writes alerts.

## Good practice
Version datasets and models, record training-data sources and licences, evaluate on time-split sets, log the model version with every answer, and keep a model card for each trained model.
