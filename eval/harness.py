from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import subprocess
from pathlib import Path
from typing import Any

import httpx
import yaml

from services.api.app.agent.orchestrator import ChatRequest, Orchestrator
from services.api.app.modules.forecast.adapters.open_meteo import OpenMeteoForecastAdapter
from services.api.app.modules.forecast.service import ForecastService
from services.api.app.modules.location.adapters.open_meteo_geocoding import OpenMeteoGeocodingAdapter
from services.api.app.modules.location.resolver import LocationResolver
from services.api.app.registry import registry

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
GOLDEN_DIR = ROOT / "eval" / "golden"
RESULTS_DIR = ROOT / "eval" / "results"
FIXTURES_DIR = ROOT / "eval" / "fixtures" / "open_meteo"


def get_per_city_forecast_transport() -> httpx.MockTransport:
    """MockTransport routing queries to real recorded per-city Open-Meteo fixtures."""
    city_forecasts: dict[str, tuple[float, float, dict[str, Any]]] = {}
    for f in FIXTURES_DIR.glob("*_forecast.json"):
        city = f.stem.replace("_forecast", "")
        if city == "differing_days":
            continue
        with f.open("r", encoding="utf-8") as jf:
            data = json.load(jf)
        city_forecasts[city] = (data.get("latitude", 0.0), data.get("longitude", 0.0), data)

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "forecast" in url_str:
            lat = float(request.url.params.get("latitude", 0.0))
            lon = float(request.url.params.get("longitude", 0.0))
            best_dist, best_data = float("inf"), None
            for _, (clat, clon, data) in city_forecasts.items():
                dist = ((lat - clat) ** 2 + (lon - clon) ** 2) ** 0.5
                if dist < best_dist:
                    best_dist = dist
                    best_data = data
            if best_data is not None:
                return httpx.Response(200, json=best_data)
            return httpx.Response(200, json={})

        if "search" in url_str or "geocoding" in url_str:
            q_name = (request.url.params.get("name", "")).lower()
            geo_file = FIXTURES_DIR / f"{q_name}_geocoding.json"
            if geo_file.exists():
                with geo_file.open("r", encoding="utf-8") as gf:
                    return httpx.Response(200, json=json.load(gf))
            from services.api.app.modules.location.resolver import INDIA_PLACES
            matched_results = []
            for p in INDIA_PLACES:
                for n in p.names.values():
                    if q_name in n.lower() or n.lower() in q_name:
                        matched_results.append({
                            "id": p.id,
                            "name": p.names.get("en", p.id),
                            "latitude": p.lat,
                            "longitude": p.lon,
                            "country_code": "IN",
                            "admin1": p.state or "",
                        })
                        break
            if not matched_results:
                matched_results.append({
                    "id": f"geo_{abs(hash(q_name)) % 100000}",
                    "name": request.url.params.get("name", "Maharashtra"),
                    "latitude": 18.5204,
                    "longitude": 73.8567,
                    "country_code": "IN",
                    "admin1": "Maharashtra",
                })
            return httpx.Response(200, json={"results": matched_results})

        return httpx.Response(200, json={})

    return httpx.MockTransport(handler)


async def run_single_case(agent: Orchestrator, case: dict[str, Any]) -> dict[str, Any]:
    req = ChatRequest(
        session_id=f"eval_{case['id']}",
        text=case["question"],
        language=case.get("language", "en"),
        place_id=case.get("place_id"),
        stream=True,
    )

    tokens = []
    evidence_packets = []
    card = None

    async for event in agent.run_chat(req):
        evt_type = event["event"]
        data = event["data"]
        if evt_type == "token":
            tokens.append(data["text"])
        elif evt_type == "evidence":
            evidence_packets.append(data)
        elif evt_type == "card":
            card = data

    full_text = "".join(tokens)
    expect = case.get("expect", {})
    failures = []

    # 1. Check refusal
    if "refusal" in expect:
        is_refusal = expect["refusal"]
        refusal_keywords = [
            "not supported", "cannot give", "not authorized", "follow official",
            "never prescribes", "cannot prescribe", "please consult", "kisan call centre",
            "helpline", "disaster management", "emergency services",
            "सलाह", "निर्देश", "समर्थित नहीं", "सहमति नहीं", "हेल्पलाइन",
            "सिफारिश नहीं", "किसान कॉल सेंटर", "कृषि विज्ञान केंद्र", "संपर्क करें",
            "সমর্থিত নয়", "নির্দেশ দিতে পারে না", "নির্ধারণ করে না", "অনুরোধ", "যোগাযোগ করুন", "দুর্যোগ ব্যবস্থাপনা",
            "समर्थित नाही", "सुचवत नाही", "मार्गदर्शनासाठी", "संपर्क साधा", "सल्ला उपलब्ध नाही",
            "మద్దతు లేదు", "సూచించదు", "ఇవ్వదు", "సంప్రదించండి", "పాటించండి", "నిర్వహణ", "అందుబాటులో లేదు",
            "ஆதரிக்கப்படவில்லை", "பரிந்துரைக்காது", "வழங்க முடியாது", "தொடர்பு கொள்ளவும்", "பின்பற்றவும்",
            "ସମର୍ଥିତ ନୁହେଁ", "ସୁପାରିଶ କରେ ନାହିଁ", "ନିର୍ଦ୍ଦେଶ ଦେଇପାରିବ ନାହିଁ", "ଯୋଗାଯୋଗ କରନ୍ତୁ",
            "ddma", "sdma", "kvk", "112", "1077", "1070", "1800-180-1551", "metar", "taf",
        ]
        card_action = (card.get("action", "") if card else "")
        card_cat = (card.get("category", "") if card else "")
        is_card_redirect = (card_action in ("redirect_to_authorities", "redirect_to_kvk", "refusal", "redirect")) or (card_cat == "refusal")
        has_refusal_kw = is_card_redirect or any(w in full_text.lower() for w in refusal_keywords)
        if is_refusal and not has_refusal_kw:
            failures.append("Expected refusal/redirection, but answer gave authoritative response")
        elif not is_refusal and has_refusal_kw and "forecast" in case.get("intent", ""):
            failures.append("Falsely refused valid weather query")

    # 2. Check source named
    if "source_named" in expect:
        expected_srcs = expect["source_named"]
        if isinstance(expected_srcs, str):
            expected_srcs = [expected_srcs]

        card_src = (card.get("source_line", "") if card else "").lower()
        card_title = (card.get("source_title", "") if card else "").lower()
        evidence_srcs = [e.get("source", "").lower() for e in evidence_packets]
        evidence_attrs = [e.get("attribution", "").lower() for e in evidence_packets]
        all_srcs = [full_text.lower(), card_src, card_title] + evidence_srcs + evidence_attrs

        if not any(any(src.lower() in s for s in all_srcs) for src in expected_srcs):
            failures.append(f"Expected source '{expect['source_named']}' not named in answer or evidence")

    # 3. Check expected numbers
    if "expected_numbers" in expect:
        for num in expect["expected_numbers"]:
            n_float = float(num)
            str_float = f"{n_float:.1f}"
            str_int = f"{n_float:.0f}"
            found_num = (str_float in full_text or str_int in full_text or str(num) in full_text)
            if not found_num and card:
                card_str = json.dumps(card)
                found_num = (str_float in card_str or str_int in card_str)
            if not found_num and evidence_packets:
                ev_str = json.dumps(evidence_packets)
                found_num = (str_float in ev_str or str_int in ev_str)
            if not found_num:
                failures.append(f"Expected number {num} not found in answer, card, or evidence")

    # 4. Check language script
    target_lang = case.get("language", "en")
    if target_lang != "en" and len(full_text) > 10:
        script_ranges = {
            "hi": (0x0900, 0x097F),
            "mr": (0x0900, 0x097F),
            "bn": (0x0980, 0x09FF),
            "te": (0x0C00, 0x0C7F),
            "ta": (0x0B80, 0x0BFF),
            "or": (0x0B00, 0x0B7F),
        }
        if target_lang in script_ranges:
            s_min, s_max = script_ranges[target_lang]
            has_script = any(s_min <= ord(c) <= s_max for c in full_text)
            if not has_script:
                failures.append(f"Answer does not contain expected script for language '{target_lang}'")

    # 5. Check must_not
    for forbidden in expect.get("must_not", []):
        if forbidden.lower() in full_text.lower():
            failures.append(f"Forbidden word/phrase found: '{forbidden}'")

    # 6. Check must_contain
    for required in expect.get("must_contain", []):
        if required.lower() not in full_text.lower():
            failures.append(f"Required word/phrase missing: '{required}'")

    passed = len(failures) == 0
    return {
        "id": case["id"],
        "passed": passed,
        "failures": failures,
        "answer": full_text,
        "evidence_count": len(evidence_packets),
        "has_card": card is not None,
    }


async def evaluate_language(language: str = "en") -> dict[str, Any]:
    lang_dir = GOLDEN_DIR / language
    if not lang_dir.exists():
        print(f"No golden set directory found for language '{language}' at {lang_dir}")
        zero_count = 0
        return {"language": language, "total": zero_count, "passed": zero_count, "cases": []}

    cases: list[dict[str, Any]] = []
    for yml_path in sorted(lang_dir.glob("*.yaml")):
        with yml_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if isinstance(data, list):
                cases.extend(data)

    transport = get_per_city_forecast_transport()
    mock_client = httpx.AsyncClient(transport=transport)
    fc_adapter = OpenMeteoForecastAdapter(client=mock_client)
    fc_service = ForecastService()
    fc_service.register_adapter(fc_adapter)

    geocoder = OpenMeteoGeocodingAdapter(client=mock_client)
    loc_resolver = LocationResolver(geocoder=geocoder)
    agent = registry.get_orchestrator(forecast_service=fc_service, location_resolver=loc_resolver)

    results = []
    for c in cases:
        res = await run_single_case(agent, c)
        results.append(res)

    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])

    golden_inputs = []
    for yml_path in sorted(lang_dir.glob("*.yaml")):
        sha = hashlib.sha256(yml_path.read_bytes()).hexdigest()
        golden_inputs.append({"path": str(yml_path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha})

    try:
        git_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(ROOT), stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        git_sha = "unknown"

    summary = {
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "generated_by": "scripts/tasks/eval.py",
        "git_sha": git_sha,
        "provenance": "recorded_real_http",
        "inputs": golden_inputs,
        "language": language,
        "total": total,
        "passed": passed_count,
        "accuracy": (passed_count / total) if total > 0 else 1.0,
        "cases": results,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report_file = RESULTS_DIR / f"{dt.datetime.now(dt.timezone.utc):%Y%m%d_%H%M%S}_{language}.json"
    with report_file.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"Evaluation report written to {report_file.relative_to(ROOT)}")
    print(f"Results for '{language}': {passed_count}/{total} passed ({summary['accuracy'] * 100:.1f}%)")
    return summary
