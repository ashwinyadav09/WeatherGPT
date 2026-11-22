# Order of work: waves and lanes

Lanes run in parallel. A ticket starts when its blockers are merged to main (see each ticket's Blocked by line); pre-work that needs no blockers can start earlier (see docs/AUTOPILOT.md, Section 2).

| Wave | Ashwin | Aman | Pradeep |
|---|---|---|---|
| 0 | 01a Platform skeleton | 01b Fixtures and spikes | 01c Web shell |
| 1 | 02 Will it rain tomorrow? | 05 Alerts v1 | 03 Places real people say |
| 2 | 04 Hindi text | 07 Model plane | 20 Website experience |
| 3 | 21 Admin console | 08 Real-time showcase, 09 Climate | 06 Voice v1 (Hindi) |
| 4 | 17 (parked: IMD out of scope) | 15 Intent model, 16 Bias correction (optional) | 10 Advisories v1, 11 Language waves |
| 5 | 18 (parked: IMD out of scope) | 13 Extra channels (later) | 19 (parked: IMD out of scope), 14 Aviation and smart city (later) |
| 6 | 12 Hardening | | |
| 7 | 22 Demo, docs and deployment pack | | |

Note: IMD is out of scope (ADR 0011). Tickets 17, 18, 19 are parked. Answers name the real source that answered (e.g., Open-Meteo, NDMA SACHET) without disclaimers about services not in scope.
If a person's next ticket is not ready, they follow the help tasks in docs/AUTOPILOT.md, Section 2.
