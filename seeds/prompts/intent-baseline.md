# Intent and slot baseline (LLM prompt)

Classify the user's message and extract slots. Return JSON only:

{"intent": "...", "slots": {"place": null, "time_window": {"label": null, "start": null, "end": null}, "crop": null, "variable": null, "unit": null, "severity": null}, "language": "en", "confidence": 0.0}

Intents
- current: conditions now
- forecast: a future time or period (point, period or threshold)
- alert: warnings or alerts for a place
- advisory: advice for crops, fishing, heat or cold
- climate: history, normals, anomalies, trends
- explain: what a term or colour means, or why the weather is as it is
- meta: where the data comes from, how accurate it is
- unsafe: asks whether to evacuate, medical or legal advice, or similar decisions
- other: not about weather or official advisories

Slots: place (as written), time_window (label such as tomorrow, with start and end if explicit), crop (wheat, rice and so on), variable (rain, temperature, wind, humidity), unit (if requested), severity (if mentioned).

Examples
- "Will it rain tomorrow in Pune?" -> forecast; place Pune; time_window tomorrow; variable rain; language en
- "कल नागपुर में बारिश होगी क्या?" -> forecast; place नागपुर; time_window कल; variable rain; language hi
- "kal Jaipur mein barish hogi kya?" -> forecast; place Jaipur; time_window kal; variable rain; language hinglish
- "Is there any warning for my area?" -> alert; place null
- "गेहूं में सिंचाई कब करूं?" -> advisory; crop गेहूं
- "How does May rainfall compare with normal in Nashik?" -> climate; place Nashik; time_window May; variable rain
- "What does an orange alert mean?" -> explain
- "Where does this forecast come from?" -> meta
- "Should we evacuate?" -> unsafe
