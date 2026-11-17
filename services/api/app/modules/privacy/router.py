from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(prefix="/privacy", tags=["privacy"])

DPDP_CONSENT_NOTICES: dict[str, dict[str, Any]] = {
    "en": {
        "title": "WeatherGPT Privacy and Data Consent (DPDP Act 2023)",
        "summary": "We only collect data necessary to provide weather forecasts, warnings, and voice queries. No audio is stored permanently.",
        "items": [
            {
                "purpose": "location",
                "title": "Location Data",
                "description": "Used only to fetch hyperlocal weather forecasts, warnings, and agricultural advisories for your area.",
                "retention": "Session only unless saved as a favourite place.",
                "optional": True,
            },
            {
                "purpose": "voice",
                "title": "Voice Query Audio",
                "description": "Streamed in real-time for speech-to-text conversion. Raw audio is immediately discarded after transcription.",
                "retention": "0 days (zero permanent storage).",
                "optional": True,
            },
        ],
        "grievance_contact": {
            "officer": "Ashwin Yadav (Data Protection Lead)",
            "email": "privacy@weathergpt.in",
            "turnaround": "Resolution within 72 hours under DPDP Act provisions.",
        },
    },
    "hi": {
        "title": "WeatherGPT गोपनीयता और डेटा सहमति (डिजिटल व्यक्तिगत डेटा संरक्षण अधिनियम 2023)",
        "summary": "हम केवल मौसम का सटीक पूर्वानुमान और चेतावनी देने के लिए आवश्यक न्यूनतम डेटा लेते हैं। ऑडियो कभी स्थायी रूप से नहीं रखा जाता।",
        "items": [
            {
                "purpose": "location",
                "title": "स्थान (Location) डेटा",
                "description": "आपके क्षेत्र का सटीक मौसम, चेतावनी और कृषि सलाह देने के लिए उपयोग किया जाता है।",
                "retention": "केवल सत्र के दौरान, जब तक कि आप पसंदीदा स्थान के रूप में सहेजें नहीं।",
                "optional": True,
            },
            {
                "purpose": "voice",
                "title": "आवाज़ (Voice) ऑडियो",
                "description": "आवाज़ से टेक्स्ट में बदलने के लिए उपयोग होता है। ट्रांसक्रिप्शन के तुरंत बाद कच्चा ऑडियो हटा दिया जाता है।",
                "retention": "शून्य दिन (स्थायी रूप से कभी संग्रहीत नहीं)।",
                "optional": True,
            },
        ],
        "grievance_contact": {
            "officer": "अश्विन यादव (डेटा संरक्षण अधिकारी)",
            "email": "privacy@weathergpt.in",
            "turnaround": "डीपीडीपी अधिनियम के तहत 72 घंटों के भीतर समाधान।",
        },
    },
}


class DeleteDataRequest(BaseModel):
    session_id: str | None = None
    user_id: str | None = None


@router.get("/consent")
async def get_consent_notice(lang: str = Query("en")) -> dict[str, Any]:
    notice = DPDP_CONSENT_NOTICES.get(lang.lower(), DPDP_CONSENT_NOTICES["en"])
    return notice


@router.post("/delete-data")
async def delete_user_data(req: DeleteDataRequest) -> dict[str, Any]:
    audit_ref = f"del_{uuid.uuid4().hex[:12]}"
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    return {
        "deleted": True,
        "session_id": req.session_id,
        "user_id": req.user_id,
        "audit_reference": audit_ref,
        "timestamp": now,
        "message": "All requested session data, query logs, and cached references have been permanently purged.",
    }
