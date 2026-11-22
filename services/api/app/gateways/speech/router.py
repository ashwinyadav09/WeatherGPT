from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel

from services.api.app.gateways.speech.exceptions import ProviderNotConfigured
from services.api.app.gateways.speech.gateway import SpeechGateway

router = APIRouter(prefix="/voice", tags=["voice"])
_gateway = SpeechGateway()


class SpeakRequest(BaseModel):
    text: str
    language: str = "hi"
    voice: str = "female"


@router.get("/health")
async def voice_health() -> dict[str, Any]:
    """Health check for voice provider status."""
    is_live = _gateway.is_live()
    return {
        "status": "ok" if is_live else "unavailable",
        "provider": "sarvam",
        "configured": is_live,
        "languages": ["hi", "bn", "ta", "te", "mr", "gu", "kn", "ml", "pa", "or", "en"],
    }


@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = Form("hi"),
) -> Any:
    content = await audio.read()
    try:
        return await _gateway.transcribe(content, language=language)
    except ProviderNotConfigured as e:
        raise HTTPException(
            status_code=503,
            detail=str(e) or "Voice provider is not configured. Please set SARVAM_API_KEY.",
        ) from e


@router.post("/speak")
async def speak_text(body: SpeakRequest) -> Response:
    try:
        audio_data = await _gateway.speak(body.text, language=body.language, voice=body.voice)
        return Response(content=audio_data, media_type="audio/wav")
    except ProviderNotConfigured as e:
        raise HTTPException(
            status_code=503,
            detail=str(e) or "Voice provider is not configured. Please set SARVAM_API_KEY.",
        ) from e
