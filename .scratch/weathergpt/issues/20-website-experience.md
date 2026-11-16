# 20: Website experience (PWA, offline, data saver, sharing, privacy)

**What to build:** The site installs to the home screen, shows the last answers when offline, has a data-saver mode, lets users share an answer, and has the Sources and licences, Privacy and consent (with delete-my-data), Settings and first-run language picker pages from docs/ui-spec.md.

**Blocked by:** 02

**Owner:** pradeep | **Reviewer:** ashwin

**Status:** ready-for-agent

- [ ] Manifest and service worker: installable, shell precached, last answers and forecasts cached with timestamps (stale-while-revalidate, bounded age), an offline page and an update prompt
- [ ] Data-saver mode skips optional requests and audio autoplay
- [ ] Share creates a link and an image card
- [ ] The Sources and licences page reads the licence register and states the non-commercial purpose
- [ ] The Privacy page has itemised consent in English and Hindi (drafts until signed off, human step), toggles for location and voice, and a working Delete my data
- [ ] A first-run language picker speaks the language names (browser speech or pre-rendered audio)
- [ ] Settings: language, voice, text size, data saver, notification severity and quiet hours (red always passes)
- [ ] axe checks pass on every page, and Lighthouse performance and PWA reports are saved and meet the performance budget in docs/ui-spec.md
