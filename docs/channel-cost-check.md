# Channel Cost, Feasibility & Regulatory Check (Ticket 13)

## Objective
Evaluate additional channels (WhatsApp, Telegram, SMS, IVR) for delivering grounded WeatherGPT answers and relay-only severe weather alerts for a non-commercial, public-interest pilot in India.

## Comparison Matrix

| Dimension | WhatsApp Business | SMS (India DLT) | IVR (Voice Hotline) | **Telegram Bot API** (Selected) |
| :--- | :--- | :--- | :--- | :--- |
| **Platform Cost** | $0.005–$0.015 / conversation + BSP fee | ₹0.12–₹0.25 / SMS + ₹5k–₹10k DLT reg. | ₹0.75–₹1.50 / minute + DID rental | **₹0.00 (100% Free)** |
| **Per-Message / Turn Cost** | ~₹0.40–₹1.20 per 24-hr session | ~₹0.15–₹0.30 per 160-char segment | ~₹1.00 per 1-minute call | **₹0.00 (Zero marginal cost)** |
| **Setup & Regulatory Gate** | Meta Business Verification, credit card required | TRAI DLT registration, Entity ID, Header, Template approval | Telecom operator SIP trunk / virtual number | **Instant bot creation via @BotFather (No red tape)** |
| **Alert Push Capability** | Template pre-approval mandatory; fees apply | 160-char limit; strict DLT transactional route | Robocall restrictions during quiet hours | **Instant markdown/HTML alert broadcast; free** |
| **Location Sharing** | Yes (Native WhatsApp location pin) | Lat/lon typing required (poor UX) | DTMF keypad or spoken PIN code | **Native GPS location attachment support** |
| **Consent & Opt-Out** | Opt-in policy; opt-out keyword | STOP keyword mandated | Press 9 to unsubscribe | **Built-in `/start` consent and `/stop` opt-out** |
| **Sustainability in Pilot** | Unaffordable without commercial sponsor | Recurring telco costs | Unsustainable without telephony grant | **100% Sustainable within open, free pilot rules** |

## Channel Selection Decision: Telegram Bot API
1. **Zero Marginal & Infrastructure Cost**: Telegram imposes no message fees, conversation fees, or platform licensing costs.
2. **Regulatory Simplicity**: Does not require commercial TRAI DLT filings or Meta Business credit lines, which are unavailable for this non-monetized pilot.
3. **Rich Interactivity**: Supports native GPS location sharing, structured formatting (bold, links, evidence citations), inline keyboards, and low-latency push alerts.
4. **Consent-First Architecture**: Explicit opt-in via `/start` with an itemized consent notice; immediate opt-out with `/stop`.
5. **Relay-Only Compliance**: Push alerts are formatted directly from official vetted templates without LLM rewriting, complying strictly with ADR 0001 and `.agents/rules/alerts-relay-only.md`.
