# 08: Real-time integration showcase

**What to build:** A status dashboard shows, live, how fresh every data source is, whether each model cycle was ingested completely, and how fast alerts travel, including a WIS2 subscription that receives real notifications.

**Blocked by:** 07

**Owner:** aman | **Reviewer:** ashwin

**Status:** ready-for-agent

- [ ] A WIS2 subscriber receives notifications from a Global Broker for India-relevant observation or product topics; if India publishes too little, a documented alternative real-time feed takes its place
- [ ] The dashboard shows freshness per source, ingest completeness per model cycle, and alert hop latency
- [ ] Freshness targets are visible: IMD warnings polled at least every 5 minutes, model fields queryable within 30 minutes of publication
- [ ] Injected delays show up correctly on the dashboard
- [ ] A subscription-uptime test runs and its result is recorded
