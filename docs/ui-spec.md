# UI spec

The website is mobile-first, voice-first and calm. Read this before building any page. Pages live as features: each feature owns its folder, its route file and its translation namespace, so features never edit each other's files.

## Principles
- One answer per screen: a headline, one key number, an icon, the source and time.
- Voice first: a large microphone button beside the text box; every answer can be heard.
- Official alerts and model guidance look and sound different. Alerts use the alert colours with an icon and words; model guidance is neutral with a dashed border and the label Model guidance. Never use alert colours for anything else.
- Never colour alone: pair colour with an icon and a word.
- Honest states: say when data is old, offline or when an official IMD forecast is not connected.

## Tokens
Fonts: Noto Sans and Noto Sans Devanagari (self-hosted subsets), system-ui fallback. Base text 18 px, line height 1.5, minimum touch target 48 px, radius 12 px, spacing scale 4, 8, 12, 16, 24, 32. Light and dark themes through prefers-color-scheme.

| Token | Value | Use |
|---|---|---|
| alert-green | background #1B7F3B, text #FFFFFF | no warning |
| alert-yellow | background #F2C200, text #1A1A1A | watch: stay aware |
| alert-orange | background #E8710A, text #1A1A1A | alert: be prepared |
| alert-red | background #C62828, text #FFFFFF | warning: take action |
| guidance | border dashed 2 px in slate #475569, background #F1F5F9 (dark: #1E293B) | model guidance |
| focus | 3 px outline #1F5FBF with 2 px offset | keyboard focus |

Contrast of every text and background pair is checked by the axe tests; fix the token, not the test.

## Navigation
Mobile: bottom bar with Ask, Alerts, Places, More. Desktop: the same items in a top bar. Content column at most 720 px wide, centred.

## Pages
1. **Ask (home).** Location chip (current place), language switch showing native names, thread of answer cards, suggestion chips (for example Will it rain tomorrow? and आज बारिश होगी?), text box, microphone button, send button.
2. **Answer card.** Headline, key value and icon, source line (Source: name, issued time, valid until), Details (hourly strip), actions: Listen, Share, Helpful or not, Why this answer? (shows evidence packets). When IMD is off, a muted line: Official IMD forecast is not connected yet.
3. **Alerts.** Active official alerts for saved places: card with level badge (colour, icon, word), hazard, place, sender line (Issued by IMD via SACHET), issued and valid times, What officials advise (expandable, cited), Listen. Severity filter. Empty state: No official alerts for your places. Notification permission is asked only after a short explanation.
4. **Places.** Saved places (Home, Farm, Work), search, use my location, set default, remove.
5. **Forecast detail.** 36-hour strip, 10-day list, a table of values with units, source labels, and official versus model comparison when both exist.
6. **Climate.** Question prompts plus simple charts (anomaly against normal, percentile) drawn as accessible SVG with a text summary.
7. **More.** Settings (language, voice, text size, data saver, notifications with severity and quiet hours; red always gets through), Sources and licences, Privacy and consent, Install, About.
8. **Sources and licences.** Table from the licence register; states that this is a non-commercial public-interest project.
9. **Privacy and consent.** Itemised notice in English and Hindi, toggles for location and voice, Delete my data.
10. **Status.** Public read-only: freshness per source, last ingest, alert latency, recent errors (no personal data).
11. **Admin** (token): glossary and alert templates with audit log.

## Wireframes
```
Ask                                   Answer card
+--------------------------------+    +--------------------------------+
| WeatherGPT          [हिं | EN]  |    | Rain likely tomorrow           |
| Place: Pune  v                 |    | 18 mm        [rain icon]       |
|                                |    | Source: Open-Meteo (model      |
|  [answer cards...]             |    |   data) | issued 05:30 IST     |
|                                |    | Official IMD forecast is not   |
| (Will it rain tomorrow?)       |    |   connected yet                |
| +---------------------+ [mic]  |    | [Listen] [Share] [Why?]        |
| | Type your question  |        |    +--------------------------------+
| +---------------------+        |
| Ask | Alerts | Places | More   |    Alert card
+--------------------------------+    +--------------------------------+
                                      | [ORANGE icon] Orange: Heavy    |
                                      | rain in Pune district          |
                                      | Issued by IMD via SACHET       |
                                      | 10:30 to 18:30 IST             |
                                      | What officials advise  v       |
                                      | [Listen]                       |
                                      +--------------------------------+
```

## Voice interaction
Hold or tap the microphone: idle, listening (level meter and timer), processing, answer. A transcript always shows. When a place name is uncertain: Did you mean {place}? with Yes and No buttons (and voice). Fall back to typing on any failure. No audio is stored by default. Microphone use needs HTTPS or localhost.

## States
Loading: skeleton plus Fetching official data. Partial: banner naming the source that failed. Offline: last saved answer with its timestamp and You are offline. Error: plain message plus Retry. Permission denied: explain and show the typed alternative.

## Accessibility
WCAG 2.2 AA. Keyboard reachable in a logical order; visible focus; aria-live for new answers and alerts; labels on every control; lang attribute on text in each language; text zoom to 200 percent without loss; reduced-motion respected; captions or transcripts for audio. Automated axe checks on every page, plus a manual screen-reader checklist with NVDA and TalkBack.

## PWA
Manifest (name, icons, standalone display, theme colour). Service worker: precache the app shell, cache last answers and forecasts with timestamps (stale-while-revalidate, bounded age), offline page, push and notification-click handlers, update prompt. Install button on More.

## Performance budget
Initial JavaScript under 200 KB gzipped, largest contentful paint under 2.5 s on simulated 4G, no layout shift from fonts (preload subsets), images avoided in favour of SVG icons.

## Copy seeds
Starting strings live in `seeds/i18n/ui.en.json` and `ui.hi.json`. Hindi is a draft until a native speaker signs off (human step).
