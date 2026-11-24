#!/usr/bin/env python3
"""Record real data per city from Open-Meteo and SACHET APIs (Ticket R20.3).

Calls live APIs:
- Open-Meteo Geocoding: https://geocoding-api.open-meteo.com/v1/search
- Open-Meteo Forecast: https://api.open-meteo.com/v1/forecast
- NDMA SACHET: https://sachet.ndma.gov.in/cap_public_website/FetchAllAlertDetails

Stores raw responses under:
- eval/recordings/open_meteo/<city>/<timestamp>_forecast.json
- eval/recordings/open_meteo/<city>/<timestamp>_geocoding.json
- eval/recordings/sachet/<timestamp>_alerts.json

Generates MANIFEST.json recording:
- url
- parameters
- request_hash
- status_code
- retrieved_at
- bytes
- sha256
- file
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
RECORDINGS_DIR = ROOT / "eval" / "recordings"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("record_fixtures")

# Target cities representing diverse climate zones and all 7 languages covering all golden cases
CITY_SLUGS = [
    "agra", "ahmedabad", "ahmednagar", "amravati", "amritsar", "anantapur", "asansol", "baharampur",
    "baramati", "bardhaman", "bengaluru", "bhopal", "bhubaneswar", "chandigarh", "chennai",
    "coimbatore", "cuddalore", "cuttack", "darjeeling", "dehradun", "delhi", "dhule", "dindigul",
    "durgapur", "erode", "guntur", "guwahati", "howrah", "hyderabad", "indore",
    "jaipur", "jalgaon", "jalpaiguri", "kadapa", "kanchipuram", "kanpur", "karimnagar",
    "khammam", "kharagpur", "kochi", "kolhapur", "kolkata", "krishnanagar", "kurnool",
    "lucknow", "ludhiana", "madurai", "malda", "midnapore", "mumbai", "murshidabad",
    "nagpur", "nanded", "nashik", "nellore", "nizamabad", "patna", "pune",
    "rajahmundry", "rajkot", "ranchi", "salem", "sangli", "santiniketan", "satara",
    "shillong", "shimla", "siliguri", "solapur", "srinagar", "surat", "thane",
    "thanjavur", "thiruvananthapuram", "thoothukudi", "tiruchirappalli", "tirunelveli",
    "tirupati", "tiruppur", "vadodara", "varanasi", "vellore", "vijayawada",
    "visakhapatnam", "warangal",
]


def compute_request_hash(
    url_or_request: str | httpx.Request,
    params: dict[str, Any] | None = None,
) -> str:
    """Compute deterministic sha256 hash for an HTTP request URL and query parameters."""
    if isinstance(url_or_request, httpx.Request):
        url = url_or_request.url
    else:
        url = httpx.URL(url_or_request)

    base_url = str(url.copy_with(query=None)).rstrip("/")
    all_params: dict[str, Any] = {}
    for k, v in url.params.multi_items():
        all_params[k] = v
    if params:
        for k, v in params.items():
            all_params[k] = str(v)

    norm_items: list[tuple[str, str]] = []
    for k in sorted(all_params.keys()):
        val = str(all_params[k])
        try:
            fval = float(val)
            val = f"{fval:.4f}"
        except ValueError:
            if k.lower() in ("name", "q", "query"):
                val = val.strip().lower()
        norm_items.append((k, val))

    serialized = json.dumps({"url": base_url, "params": norm_items}, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def record_response(
    url: str,
    params: dict[str, Any] | None,
    output_path: Path,
    content: bytes,
    status_code: int = 200,
) -> dict[str, Any]:
    """Write raw response bytes and return manifest entry."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(content)

    sha256_hash = hashlib.sha256(content).hexdigest()
    req_hash = compute_request_hash(url, params)
    now_utc = dt.datetime.now(dt.timezone.utc).isoformat()
    rel_to_recordings = str(output_path.relative_to(RECORDINGS_DIR)).replace("\\", "/")
    rel_to_root = str(output_path.relative_to(ROOT)).replace("\\", "/")

    return {
        "url": url,
        "parameters": params or {},
        "request_hash": req_hash,
        "status_code": status_code,
        "retrieved_at": now_utc,
        "bytes": len(content),
        "sha256": sha256_hash,
        "file": rel_to_recordings,
        "path": rel_to_root,
    }


def record_open_meteo_city(
    client: httpx.Client,
    city_slug: str,
    city_name: str,
    lat: float,
    lon: float,
    timestamp_str: str,
) -> list[dict[str, Any]]:
    """Record geocoding and forecast API responses for a single city."""
    records: list[dict[str, Any]] = []
    city_dir = RECORDINGS_DIR / "open_meteo" / city_slug

    # 1. Geocoding API
    geo_url = "https://geocoding-api.open-meteo.com/v1/search"
    geo_params: dict[str, Any] = {"name": city_name, "count": 5, "language": "en"}
    resp_geo = client.get(geo_url, params=geo_params)
    resp_geo.raise_for_status()

    geo_file = city_dir / f"{timestamp_str}_geocoding.json"
    rec_geo = record_response(
        url=geo_url,
        params=geo_params,
        output_path=geo_file,
        content=resp_geo.content,
        status_code=resp_geo.status_code,
    )
    records.append(rec_geo)

    # 2. Forecast API
    fc_url = "https://api.open-meteo.com/v1/forecast"
    fc_params: dict[str, Any] = {
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "current": "temperature_2m,precipitation",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max",
        "timezone": "Asia/Kolkata",
        "forecast_days": 7,
    }
    resp_fc = client.get(fc_url, params=fc_params)
    resp_fc.raise_for_status()

    fc_file = city_dir / f"{timestamp_str}_forecast.json"
    rec_fc = record_response(
        url=fc_url,
        params=fc_params,
        output_path=fc_file,
        content=resp_fc.content,
        status_code=resp_fc.status_code,
    )
    records.append(rec_fc)

    # Write city-specific manifest
    city_manifest_file = city_dir / "MANIFEST.json"
    city_manifest_file.write_text(json.dumps(records, indent=2), encoding="utf-8")

    return records


def record_sachet(client: httpx.Client, timestamp_str: str) -> list[dict[str, Any]]:
    """Record SACHET alerts feed and individual CAP XML documents."""
    records: list[dict[str, Any]] = []
    sachet_dir = RECORDINGS_DIR / "sachet"

    feed_url = "https://sachet.ndma.gov.in/cap_public_website/FetchAllAlertDetails"
    try:
        resp = client.get(feed_url)
        resp.raise_for_status()
        alerts_file = sachet_dir / f"{timestamp_str}_alerts.json"
        rec = record_response(
            url=feed_url,
            params={},
            output_path=alerts_file,
            content=resp.content,
            status_code=resp.status_code,
        )
        records.append(rec)

        # Parse alerts to download individual XML documents
        try:
            alerts_data = resp.json()
            if isinstance(alerts_data, list):
                for alert in alerts_data[:5]:  # Capture up to 5 live alerts
                    identifier = alert.get("identifier")
                    if identifier:
                        xml_url = f"https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile?identifier={identifier}"
                        try:
                            xml_resp = client.get(xml_url)
                            if xml_resp.status_code == 200:
                                xml_file = sachet_dir / f"{timestamp_str}_{identifier}.xml"
                                rec_xml = record_response(
                                    url=xml_url,
                                    params={"identifier": str(identifier)},
                                    output_path=xml_file,
                                    content=xml_resp.content,
                                    status_code=xml_resp.status_code,
                                )
                                records.append(rec_xml)
                        except Exception as exc:
                            logger.warning("Could not fetch XML for alert %s: %s", identifier, exc)
        except Exception as parse_err:
            logger.warning("Could not parse SACHET alerts JSON: %s", parse_err)

    except Exception as exc:
        logger.error("Failed to record SACHET feed: %s", exc)

    # Write sachet-specific manifest
    if records:
        sachet_manifest_file = sachet_dir / "MANIFEST.json"
        sachet_manifest_file.write_text(json.dumps(records, indent=2), encoding="utf-8")

    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record live Open-Meteo and SACHET fixtures per city")
    parser.add_argument("--cities", nargs="*", help="Optional specific city slugs to record")
    args = parser.parse_args(argv)

    from services.api.app.modules.location.data import PLACES_BY_ID

    target_slugs = args.cities or CITY_SLUGS
    timestamp_str = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    logger.info("Recording live data for %d cities at %s...", len(target_slugs), timestamp_str)
    all_records: list[dict[str, Any]] = []
    failed_cities: list[tuple[str, str]] = []

    with httpx.Client(timeout=30.0) as client:
        # 1. Record Open-Meteo per city
        for slug in target_slugs:
            if slug not in PLACES_BY_ID:
                logger.warning("City slug '%s' not found in PLACES_BY_ID, skipping.", slug)
                failed_cities.append((slug, "Unknown city slug"))
                continue

            place = PLACES_BY_ID[slug]
            city_name = place.names.get("en", slug.capitalize())
            logger.info("Recording %s (%s) at (%.4f, %.4f)...", city_name, slug, place.lat, place.lon)

            try:
                city_records = record_open_meteo_city(
                    client=client,
                    city_slug=slug,
                    city_name=city_name,
                    lat=place.lat,
                    lon=place.lon,
                    timestamp_str=timestamp_str,
                )
                all_records.extend(city_records)
                time.sleep(1)  # Respect rate limits
            except Exception as exc:
                logger.error("Failed recording for city '%s': %s", slug, exc)
                failed_cities.append((slug, str(exc)))

        # 2. Record SACHET
        logger.info("Recording SACHET live feed...")
        sachet_records = record_sachet(client, timestamp_str)
        all_records.extend(sachet_records)

    # 3. Write top-level MANIFEST.json
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    top_manifest = RECORDINGS_DIR / "MANIFEST.json"
    manifest_map: dict[str, dict[str, Any]] = {}
    if top_manifest.exists():
        try:
            existing = json.loads(top_manifest.read_text(encoding="utf-8"))
            if isinstance(existing, list):
                for item in existing:
                    req_h = item.get("request_hash")
                    if req_h:
                        manifest_map[req_h] = item
        except Exception as e:
            logger.warning("Could not read existing top manifest: %s", e)
    for rec in all_records:
        manifest_map[rec["request_hash"]] = rec

    final_records = list(manifest_map.values())
    top_manifest.write_text(json.dumps(final_records, indent=2), encoding="utf-8")
    logger.info("Wrote %d entries to %s", len(final_records), top_manifest)

    if failed_cities:
        logger.warning("Excluded %d failed cities:", len(failed_cities))
        for slug, reason in failed_cities:
            logger.warning("  - %s: %s", slug, reason)

    print(f"\n[DONE] Successfully recorded {len(all_records)} fixtures across {len(target_slugs) - len(failed_cities)} cities.")
    return 0 if not failed_cities else 1


if __name__ == "__main__":
    sys.exit(main())
