# 15: Intent and slot model (optional ML training)

**What to build:** A small multilingual model labels each Hindi, English or code-mixed question with its type (current, forecast, alert, advisory, climate, explain, meta, unsafe) and pulls out place, time window, crop and units in milliseconds. The Conversation API uses it to route questions and falls back to the LLM when confidence is low.

**Blocked by:** 04

**Owner:** aman | **Reviewer:** ashwin

**Status:** ready-for-agent

- [ ] A labelled dataset of at least 3,000 utterances (drafted with an LLM, corrected by a person, including code-mixed and noisy speech-style text) exists, with a separate golden test set, built from the sources in the ML plan with licences recorded
- [ ] A fine-tuned small multilingual encoder reaches at least 95 percent intent accuracy and a stated slot F1 on the golden set
- [ ] A short report compares it with the LLM-only baseline on accuracy, latency and cost
- [ ] Low-confidence turns fall back to the LLM, with the confidence threshold tuned on held-out data
- [ ] The model version is recorded with each answer and a model card exists
- [ ] The model ships only if it matches the baseline's accuracy at lower latency
