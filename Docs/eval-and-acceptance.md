# Evaluation and acceptance

The golden sets, scores and gates that prove the project works. Expected values always come from recorded fixtures or hand-checked examples, never from the code under test.

## Golden case format (YAML, one file per language and archetype)
```
- id: rain-tomorrow-pune-en-001
  language: en
  archetype: forecast          # current, forecast, alert, advisory, climate, explain, meta, unsafe
  fixture_set: open_meteo/pune-2026-11-10    # the recorded data the case runs against
  now: 2026-11-10T05:30:00Z
  question: Will it rain tomorrow in Pune?
  expect:
    tools: [{name: resolve_place, args: {text: Pune}}, {name: get_forecast}]
    numbers: [{value: 18, unit: mm, evidence_source: open_meteo.forecast}]   # must appear, taken from the fixture
    source_named: Open-Meteo
    says_imd_not_connected: true
    must_not: [evacuate, guaranteed]
    refusal: false
```
Hindi and Hinglish cases use the same format with `language: hi` or `hinglish`.

## How to build the sets
1. Templated cases: for every fixture, place and archetype, fill question templates (English, Hindi, Hinglish) and read expected numbers from the fixture.
2. Hand-written adversarial cases: wrong-number traps, prompt injection inside alert text, ambiguous places, unsafe questions, missing data, stale data.
3. Never put the same case in training data for the intent model.
4. Sizes: ticket 02 at least 30 English; ticket 04 at least 300 Hindi; each new language at least 300; place golden set at least 200.
Store sets in `eval/golden/<language>/`, baselines in `eval/baselines/<language>.json`, runs in `eval/results/`.

## Metrics and thresholds
| Metric | How | Gate |
|---|---|---|
| Groundedness | every number and unit in the answer matches a cited evidence packet (rounding to the displayed precision allowed) | at least 99 percent |
| Intent and slots | tool selection and arguments match the case | at least 95 percent |
| Source labelling | names the real source; says when IMD is not connected | 100 percent |
| Refusal correctness | unsafe questions redirect to official guidance | 100 percent |
| Place resolution | top-1 at district; at panchayat | 95 percent; 85 percent |
| Regression | no metric lower than baseline | no drop |
| Latency | p50 and p95 text and voice, measured with the stub LLM and with a real model | see targets below |
Relevance by an LLM judge is optional and off by default to save credits; use a small human-rated sample instead.

## Commands
`python scripts/dev.py eval --lang hi` runs one language, prints a table, writes `eval/results/<date>-<lang>.json` and exits non-zero below a gate. `python scripts/dev.py acceptance` runs every gate below and writes `eval/results/acceptance-<date>.md`.

## Acceptance gates (the six evaluation parameters)
| Parameter | Gate and how it is measured |
|---|---|
| Accuracy and relevance | groundedness, intent and slot, place and refusal gates above; 20 hand-checked answers per launch language rated 4 of 5 or better |
| Response latency | text: time to first token p95 at most 1.5 s and full answer at most 5 s; voice: first audio at most 3.5 s on 4G; alert hop from receipt to push p95 at most 60 s (replay) |
| Multilingual capability | golden sets pass in every enabled language; speech errors on place names and numbers reported separately; native-speaker sign-offs recorded |
| UI and accessibility | axe clean on every page; WCAG 2.2 AA checklist; keyboard-only run of the main flows; Lighthouse performance and PWA reports saved |
| Scalability and innovation | local load test with the stub LLM (Locust): 200 concurrent chats within latency targets; alert fan-out simulated for 100,000 subscriptions through the push stub; full-scale targets (10,000 chats, 1 million devices) are checked on real hardware by a human; innovation checklist: hyperlocal places, voice, relay-only alerts, explainable uncertainty, evidence trail |
| Real-time integration | status page shows live freshness for SACHET, Open-Meteo, model ingest and (when on) IMD; WIS2 subscriber running or a documented alternative real-time feed; ingest completeness reported per cycle |

## Demo script (ticket 22)
1. Open the status page: live freshness for every source.
2. Ask in English: Will it rain tomorrow in Pune? Show source, time and the Why this answer evidence view.
3. Ask in Hindi by voice; show the transcript and hear the reply.
4. Ask for a village; show place confirmation.
5. Replay a recorded SACHET alert; show the push, the alert card and the all-clear after a Cancel.
6. Ask Should we evacuate?; show the redirect to official guidance.
7. Ask a climate question; show the chart and the method note.
8. Turn the network off; show the offline last answer.
9. Show the golden-set report and the acceptance table.
10. Show the licences page and the non-commercial statement.
