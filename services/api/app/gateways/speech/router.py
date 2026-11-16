from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, Form, Response, UploadFile
from pydantic import BaseModel

from services.api.app.gateways.speech.gateway import SpeechGateway

router = APIRouter(prefix="/voice", tags=["voice"])
_gateway = SpeechGateway()


class SpeakRequest(BaseModel):
    text: str
    language: str = "hi"
    voice: str = "female"


@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = Form("hi"),
) -> Any:
    content = await audio.read()
    return await _gateway.transcribe(content, language=language)


@router.post("/speak")
async def speak_text(body: SpeakRequest) -> Response:
    audio_data = await _gateway.speak(body.text, language=body.language, voice=body.voice)
    return Response(content=audio_data, media_type="audio/wav")
