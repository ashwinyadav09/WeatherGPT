# 0006: Website only

**Status:** accepted (6 November 2026; the product owner said a website is enough)

**Context:** The first plan assumed an Android app. The product owner does not need one.

**Decision:** Build a responsive website that can be added to the home screen as a progressive web app: a service worker for offline cache and Web Push, microphone capture in the browser with audio sent to the backend for recognition, MapLibre for maps. No native apps.

**Consequences:** One front end to build and test, verifiable by browser agents and Playwright. Alerts use Web Push, which works in Chrome and Firefox; Safari on iPhone supports it only for sites added to the home screen (verify current behaviour). Browser audio formats differ, so the backend converts recordings before sending them to speech providers.
