# 01c: Web shell

**What to build:** A runnable website shell that follows docs/ui-spec.md: React, TypeScript and Vite, installable as a PWA, with routing where each feature registers its own routes, design tokens (including alert colours), English and Hindi translation scaffolding with one namespace per feature, a small component library, mock API responses from the contract, and test tooling. The Ask page exists as a placeholder that talks to the mocks.

**Blocked by:** None (can start immediately; use the mock API until the contracts from ticket 01a merge, then switch to them)

**Owner:** pradeep | **Reviewer:** ashwin

**Status:** ready-for-agent

- [ ] The Vite, React and TypeScript project builds and runs; the unit test command and the end-to-end command pass
- [ ] Feature registration: each feature folder owns its routes file and its translation namespace, so adding a feature edits no shared file
- [ ] Design tokens, light and dark themes, Noto Sans and Noto Sans Devanagari fonts, and the base layout and navigation from the spec
- [ ] Components: button, card, chip, alert badge (colour, icon and word), source line, skeleton, error banner, offline banner, microphone button
- [ ] i18n with English and Hindi from the seeds, a language switch showing native names, and lang attributes set
- [ ] A mock API server returning the contract shapes (chat events, places, alerts) for development and tests
- [ ] Playwright and axe are set up and the shell passes axe; a Dockerfile builds the production bundle
- [ ] A PWA manifest and a minimal service worker (full behaviour comes in ticket 20)
