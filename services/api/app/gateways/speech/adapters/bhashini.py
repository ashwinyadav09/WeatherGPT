from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

import httpx
import structlog

from services.api.app.gateways.speech.tts_normalizer import normalize_for_tts

logger = structlog.get_logger()

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
ASR_FIXTURE_PATH = ROOT / "eval" / "fixtures" / "bhashini" / "asr_sample.json"
TTS_FIXTURE_PATH = ROOT / "eval" / "fixtures" / "bhashini" / "tts_sample.json"


class BhashiniSpeechAdapter:
    """Bhashini ULCA speech adapter for Indian languages (ASR & TTS)."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.user_id = os.getenv("BHASHINI_USER_ID", "")
        self.api_key = os.getenv("BHASHINI_API_KEY", "")
        self.pipeline_endpoint = os.getenv(
            "BHASHINI_PIPELINE_ENDPOINT",
            "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline",
        )
        self.inference_endpoint = os.getenv(
            "BHASHINI_INFERENCE_ENDPOINT",
            "https://dhruva-api.bhashini.gov.in/services/inference/pipeline",
        )
        self.inference_api_key = os.getenv("BHASHINI_INFERENCE_API_KEY", "")
        self.client = client
        self.pipeline_id = "64392f96daac500b55c543d6"
        self._cached_service_ids: dict[str, str] = {}

    async def _get_client(self) -> httpx.AsyncClient:
        return self.client or httpx.AsyncClient(timeout=10.0)

    async def transcribe(self, audio_bytes: bytes, language: str = "hi") -> dict[str, Any]:
        """Transcribe speech audio into text using Bhashini ASR."""
        if not self.user_id or not self.api_key:
            # Documented fixture mode for offline / test runs
            if ASR_FIXTURE_PATH.exists():
                with ASR_FIXTURE_PATH.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    pipeline_resp = data.get("pipelineResponse", [])
                    if pipeline_resp and "output" in pipeline_resp[0]:
                        text = pipeline_resp[0]["output"][0].get("source", "")
                        return {
                            "text": text,
                            "language": language,
                            "confidence": 0.95,
                            "provider": "bhashini",
                            "provenance": data.get("_provenance", "documented-sample"),
                        }
            return {
                "text": "कल पुणे में बारिश होगी क्या?",
                "language": language,
                "confidence": 0.95,
                "provider": "bhashini",
                "provenance": "stub",
            }

        audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
        headers = {
            "Authorization": self.inference_api_key or self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "pipelineTasks": [
                {
                    "taskType": "asr",
                    "config": {
                        "language": {"sourceLanguage": language},
                        "serviceId": self._cached_service_ids.get(f"asr_{language}", "ai4bharat/conformer-hi"),
                        "audioFormat": "wav",
                        "samplingRate": 16000,
                    },
                }
            ],
            "inputData": {
                "audio": [{"audioContent": audio_b64}],
            },
        }

        client = await self._get_client()
        try:
            resp = await client.post(self.inference_endpoint, json=payload, headers=headers)
            if resp.status_code in (401, 403):
                logger.warning("bhashini_auth_expired", status=resp.status_code)
                # Refresh pipeline config once per troubleshooting guide
                await self._refresh_pipeline_config(client)
                headers["Authorization"] = self.inference_api_key
                resp = await client.post(self.inference_endpoint, json=payload, headers=headers)

            resp.raise_for_status()
            res_json = resp.json()
            out_text = res_json["pipelineResponse"][0]["output"][0]["source"]
            return {
                "text": out_text,
                "language": language,
                "confidence": 0.95,
                "provider": "bhashini",
                "provenance": "live",
            }
        finally:
            if not self.client:
                await client.aclose()

    async def speak(self, text: str, language: str = "hi", voice: str = "female") -> bytes:
        """Synthesize text into natural spoken speech using Bhashini TTS."""
        natural_text = normalize_for_tts(text, language=language)

        if not self.user_id or not self.api_key:
            if TTS_FIXTURE_PATH.exists():
                with TTS_FIXTURE_PATH.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    pipeline_resp = data.get("pipelineResponse", [])
                    if pipeline_resp and "audio" in pipeline_resp[0]:
                        b64_audio = pipeline_resp[0]["audio"][0].get("audioContent", "")
                        return base64.b64decode(b64_audio)
            # Fallback valid WAV
            return b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"

        headers = {
            "Authorization": self.inference_api_key or self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "pipelineTasks": [
                {
                    "taskType": "tts",
                    "config": {
                        "language": {"sourceLanguage": language},
                        "serviceId": self._cached_service_ids.get(f"tts_{language}", "ai4bharat/indic-tts-hi"),
                        "gender": voice,
                        "samplingRate": 16000,
                    },
                }
            ],
            "inputData": {
                "input": [{"source": natural_text}],
            },
        }

        client = await self._get_client()
        try:
            resp = await client.post(self.inference_endpoint, json=payload, headers=headers)
            if resp.status_code in (401, 403):
                await self._refresh_pipeline_config(client)
                headers["Authorization"] = self.inference_api_key
                resp = await client.post(self.inference_endpoint, json=payload, headers=headers)

            resp.raise_for_status()
            res_json = resp.json()
            audio_b64 = res_json["pipelineResponse"][0]["audio"][0]["audioContent"]
            return base64.b64decode(audio_b64)
        finally:
            if not self.client:
                await client.aclose()

    async def _refresh_pipeline_config(self, client: httpx.AsyncClient) -> None:
        """Refreshes the pipeline configuration from ULCA."""
        headers = {
            "userID": self.user_id,
            "ulcaApiKey": self.api_key,
            "Content-Type": "application/json",
        }
        body = {
            "pipelineTasks": [
                {"taskType": "asr", "config": {"language": {"sourceLanguage": "hi"}}},
                {"taskType": "tts", "config": {"language": {"sourceLanguage": "hi"}}},
            ],
            "pipelineRequestConfig": {"pipelineId": self.pipeline_id},
        }
        resp = await client.post(self.pipeline_endpoint, json=body, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        ep = data.get("pipelineInferenceAPIEndPoint", {})
        self.inference_endpoint = ep.get("inferenceApiKey", {}).get("name", self.inference_endpoint)
        self.inference_api_key = ep.get("inferenceApiKey", {}).get("value", self.api_key)
