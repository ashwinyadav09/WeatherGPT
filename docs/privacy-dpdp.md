# Digital Personal Data Protection (DPDP) Act Compliance & Checklist

## Overview
WeatherGPT is built as a public-interest weather pilot adhering strictly to the **Digital Personal Data Protection Act, 2023 (DPDP Act)** of India.

## DPDP Compliance Checklist
- [x] **Notice and Consent**: Itemised, bilingual (English & Hindi) clear consent notices presented prior to collecting location or voice data (`GET /v1/privacy/consent`).
- [x] **Purpose Limitation**: Personal data is collected strictly for the stated purpose (weather forecast, official alert relay).
- [x] **Data Minimisation**: No permanent storage of raw voice recordings. Audio is processed ephemeral-in-memory and discarded immediately upon transcription.
- [x] **Right to Erasure / Deletion Path**: Users can immediately delete any query history, session identifiers, or stored place preferences via `POST /v1/privacy/delete-data`.
- [x] **Grievance Redressal**: Explicit grievance redressal mechanism with named Data Protection Officer and 72-hour turnaround time.
- [x] **No Commercial Exploitation or Ad Tracking**: No third-party ad networks, tracking pixels, or monetisation cookies.

## Data Protection Officer & Grievance Contact
- **Officer**: Ashwin Yadav (Data Protection Lead)
- **Email**: `privacy@weathergpt.in`
- **Address**: WeatherGPT Public Pilot, Pune / New Delhi, India
- **Response SLA**: Initial response within 24 hours, resolution within 72 hours.

## Personal Data Breach Runbook
In the event of an identified security incident or data breach:
1. **Detection & Containment (< 1 hour)**:
   - Identify affected components (API, database, Redis cache).
   - Revoke compromised tokens/keys immediately (`ADMIN_TOKEN`, provider keys).
   - Isolate affected network pods/instances.
2. **Assessment (< 6 hours)**:
   - Determine nature, volume, and categories of data impacted.
   - Confirm whether any encrypted session identifiers or location logs were accessed.
3. **Regulatory & User Notification (< 24 hours)**:
   - Notify Data Protection Board of India (DPBI) per statutory format.
   - Notify affected data principals via in-app banner and registered push notifications with plain-language advice.
4. **Remediation & Post-Incident Review (< 72 hours)**:
   - Patch root cause and verify via automated penetration & security scans.
   - Publish incident post-mortem in public transparency log.
