# 03: Places real people say

**What to build:** A user can name a district, block, village or gram panchayat in an Indic script or a common transliteration, or use GPS or a saved place, and get the forecast for that exact place from the current forecast source. When a name is ambiguous the site asks one question.

**Blocked by:** 01a, 01c

**Owner:** pradeep | **Reviewer:** ashwin

**Status:** ready-for-agent

- [ ] The LocationResolver handles district, block, panchayat, GPS and saved places (home, farm, work)
- [ ] Indic-script and transliterated names resolve to the same place
- [ ] A place golden set of at least 200 cases reaches 95 percent top-1 at district level and 85 percent at panchayat level
- [ ] Ambiguous names (for example one that exists in several states) trigger exactly one clarifying question
- [ ] Every place carries coordinates, so any forecast source can serve it
- [ ] Ticket 02's Ask flow switches to the full resolver once both tickets are merged (whoever merges second makes the switch)
- [ ] Saved places persist on the device, with an optional account later
