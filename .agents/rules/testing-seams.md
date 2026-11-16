---
trigger: glob
globs: "**/tests/**, **/test_*.py, **/*.test.ts, **/*.test.tsx, **/*.spec.ts, eval/**"
description: Test at three seams through public interfaces, with expected values from independent sources.
---

# Testing at seams

Three seams carry the tests:
1. **Conversation API**: question in, grounded answer and evidence out.
2. **Alert pipeline**: official message in, notifications out.
3. **Adapter conformance**: one reusable suite that every external-system adapter passes, run on recorded fixtures.

- Test behaviour through the public interface; leave internals free to change.
- Go red first: watch the test fail for the right reason, then write the code. One test, then its code.
- Take expected values from dated fixtures or hand-checked examples, never from the code under test.
- Label every fixture with its provenance: live-recorded, documented-sample or spec-only. Call an adapter verified only when its conformance suite passes on live-recorded fixtures.
- Use real adapters with recorded fixtures; fake only what sits outside the process boundary.
- Live APIs are touched only by scheduled contract checks, never by CI.
- The grounding verifier is a pure function with a large input space; give it property tests at its own interface.
