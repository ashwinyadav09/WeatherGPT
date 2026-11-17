"""Collector script to fetch and assemble live fixtures for Ticket 01b."""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = ROOT / "eval" / "fixtures"

HEADERS = {"User-Agent": "WeatherGPT-Pilot/0.1 (public interest weather assistant; non-commercial)"}


def http_get(url: str, timeout: int = 15) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def collect_sachet():
    sachet_dir = FIXTURES_DIR / "sachet"
    cap_dir = sachet_dir / "cap_xml"
    sachet_dir.mkdir(parents=True, exist_ok=True)
    cap_dir.mkdir(parents=True, exist_ok=True)

    print("Fetching SACHET RSS feed...")
    rss_url = "https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml"
    rss_data = http_get(rss_url)
    root = ET.fromstring(rss_data)
    items = root.findall(".//item")
    print(f"Found {len(items)} items in RSS feed.")

    saved_count = 0
    now_iso = datetime.now(timezone.utc).isoformat()

    for i, it in enumerate(items):
        if saved_count >= 25:
            break
        link = it.findtext("link", "").strip()
        _pub_date = it.findtext("pubDate", "").strip()
        if not link:
            continue
        try:
            time.sleep(0.3)
            xml_text = http_get(link)
            # Parse CAP XML
            cap_root = ET.fromstring(xml_text)
            # Strip namespaces for simple lookup
            for elem in cap_root.iter():
                if "}" in elem.tag:
                    elem.tag = elem.tag.split("}", 1)[1]

            identifier = cap_root.findtext("identifier", f"sachet_alert_{i+1}")
            msg_type = cap_root.findtext("msgType", "Alert")
            sender = cap_root.findtext("sender", "NDMA-SACHET")
            sent = cap_root.findtext("sent", now_iso)
            status = cap_root.findtext("status", "Actual")

            info = cap_root.find("info")
            if info is None:
                continue

            event = info.findtext("event", "Weather Advisory")
            severity = info.findtext("severity", "Moderate")
            urgency = info.findtext("urgency", "Expected")
            certainty = info.findtext("certainty", "Likely")
            onset = info.findtext("onset", sent)
            expires = info.findtext("expires", now_iso)
            headline = info.findtext("headline", "")
            description = info.findtext("description", headline)

            # Polygons and areas
            areas_list = []
            for area in info.findall("area"):
                area_desc = area.findtext("areaDesc", "")
                poly = area.findtext("polygon", "")
                areas_list.append({"areaDesc": area_desc, "polygon": poly})

            # Severity to level mapping
            sev_norm = severity if severity in ["Extreme", "Severe", "Moderate", "Minor"] else "Moderate"
            level_map = {"Extreme": "red", "Severe": "orange", "Moderate": "yellow", "Minor": "green"}
            level = level_map.get(sev_norm, "yellow")

            # Save XML
            xml_filename = f"sachet_{i+1:02d}_{msg_type.lower()}.xml"
            (cap_dir / xml_filename).write_text(xml_text, encoding="utf-8")

            # Save parsed JSON conforming to alert.json
            alert_json = {
                "_provenance": "live-recorded",
                "_source": link,
                "_recorded_at": now_iso,
                "id": f"urn:oid:2.49.0.1.356.sachet.{re.sub(r'[^a-zA-Z0-9]', '.', identifier)}",
                "sender": sender,
                "sent": sent if "T" in sent else now_iso,
                "status": status,
                "msg_type": msg_type,
                "hazard": event,
                "severity": sev_norm,
                "urgency": urgency if urgency in ["Immediate", "Expected", "Future", "Past"] else "Expected",
                "certainty": certainty if certainty in ["Observed", "Likely", "Possible", "Unlikely"] else "Likely",
                "onset": onset if "T" in onset else now_iso,
                "expires": expires if "T" in expires else now_iso,
                "areas": areas_list or [{"areaDesc": "India Region", "polygon": ""}],
                "text_by_language": {
                    "en": description or headline or event,
                    "hi": f"{event}: {headline}" if headline else event,
                },
                "source_url": link,
                "authority_tier": 1,
                "level": level,
            }

            json_filename = f"sachet_{i+1:02d}_{msg_type.lower()}.json"
            (sachet_dir / json_filename).write_text(
                json.dumps(alert_json, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            saved_count += 1
            print(f"Saved {saved_count}: {json_filename} ({msg_type}, {sev_norm})")
        except Exception as e:
            print(f"Error fetching {link}: {e}")

    # Add synthetic cyclone alert
    cyclone_alert = {
        "_provenance": "synthetic",
        "_source": "https://sachet.ndma.gov.in (modelled on IMD RSMC New Delhi tropical cyclone bulletin structure)",
        "_recorded_at": now_iso,
        "id": "urn:oid:2.49.0.1.356.sachet.cyclone.2026.01",
        "sender": "IMD-RSMC-NewDelhi",
        "sent": "2026-11-17T06:00:00Z",
        "status": "Actual",
        "msg_type": "Alert",
        "hazard": "Very Severe Cyclonic Storm",
        "severity": "Extreme",
        "urgency": "Immediate",
        "certainty": "Observed",
        "onset": "2026-11-17T06:00:00Z",
        "expires": "2026-11-19T18:00:00Z",
        "areas": [
            {
                "areaDesc": "Coastal Odisha and West Bengal",
                "polygon": "19.5,85.2 20.8,86.9 21.6,87.8 22.1,88.4 20.2,87.0 19.5,85.2",
            }
        ],
        "text_by_language": {
            "en": "Extreme Danger: Very Severe Cyclonic Storm with sustained wind speed 130-140 kmph gusting to 155 kmph. Fishermen advised not to venture into deep sea. Total suspension of fishing operations.",
            "hi": "अत्यधिक चेतावनी: अत्यधिक भीषण चक्रवाती तूफान, हवा की गति 130-140 किमी/घंटा से 155 किमी/घंटा तक। मछुआरों को समुद्र में न जाने की सलाह दी जाती है।",
        },
        "source_url": "https://sachet.ndma.gov.in/cap_public_website/cyclone_synthetic.xml",
        "authority_tier": 1,
        "level": "red",
    }
    (sachet_dir / "sachet_synthetic_cyclone.json").write_text(
        json.dumps(cyclone_alert, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("Saved synthetic cyclone alert.")


def collect_open_meteo():
    om_dir = FIXTURES_DIR / "open_meteo"
    om_dir.mkdir(parents=True, exist_ok=True)
    now_iso = datetime.now(timezone.utc).isoformat()

    places = [
        {"slug": "delhi", "name": "Delhi", "name_hi": "नई दिल्ली", "lat": 28.6139, "lon": 77.2090},
        {"slug": "mumbai", "name": "Mumbai", "name_hi": "मुंबई", "lat": 19.0760, "lon": 72.8777},
        {"slug": "kolkata", "name": "Kolkata", "name_hi": "कोलकाता", "lat": 22.5726, "lon": 88.3639},
        {"slug": "bengaluru", "name": "Bengaluru", "name_hi": "बेंगलुरु", "lat": 12.9716, "lon": 77.5946},
        {"slug": "chennai", "name": "Chennai", "name_hi": "चेन्नई", "lat": 13.0827, "lon": 80.2707},
        {"slug": "hyderabad", "name": "Hyderabad", "name_hi": "हैदराबाद", "lat": 17.3850, "lon": 78.4867},
        {"slug": "pune", "name": "Pune", "name_hi": "पुणे", "lat": 18.5204, "lon": 73.8567},
        {"slug": "jaipur", "name": "Jaipur", "name_hi": "जयपुर", "lat": 26.9124, "lon": 75.7873},
        {"slug": "shimla", "name": "Shimla", "name_hi": "शिमला", "lat": 31.1048, "lon": 77.1734},
        {"slug": "guwahati", "name": "Guwahati", "name_hi": "गुवाहाटी", "lat": 26.1445, "lon": 91.7362},
        {"slug": "varanasi", "name": "Varanasi", "name_hi": "वाराणसी", "lat": 25.3176, "lon": 82.9739},
    ]

    for p in places:
        slug = p["slug"]
        lat, lon = p["lat"], p["lon"]
        name = p["name"]

        print(f"Fetching Open-Meteo samples for {name} ({slug})...")

        # 1. Forecast
        fc_url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            f"&hourly=temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,wind_speed_10m,wind_gusts_10m"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max"
            f"&current=temperature_2m,precipitation&timezone=Asia%2FKolkata&forecast_days=10"
        )
        try:
            fc_data = json.loads(http_get(fc_url))
            fc_data["_provenance"] = "live-recorded"
            fc_data["_source"] = fc_url
            fc_data["_recorded_at"] = now_iso
            fc_data["_place"] = p
            (om_dir / f"{slug}_forecast.json").write_text(
                json.dumps(fc_data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            time.sleep(0.2)
        except Exception as e:
            print(f"Error fetching forecast for {slug}: {e}")

        # 2. Archive
        arch_url = (
            f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}"
            f"&start_date=2026-10-01&end_date=2026-10-07"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
            f"&timezone=Asia%2FKolkata"
        )
        try:
            arch_data = json.loads(http_get(arch_url))
            arch_data["_provenance"] = "live-recorded"
            arch_data["_source"] = arch_url
            arch_data["_recorded_at"] = now_iso
            arch_data["_place"] = p
            (om_dir / f"{slug}_archive.json").write_text(
                json.dumps(arch_data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            time.sleep(0.2)
        except Exception as e:
            print(f"Error fetching archive for {slug}: {e}")

        # 3. Geocoding
        enc_name = urllib.parse.quote(name)
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={enc_name}&language=hi&count=5"
        try:
            geo_data = json.loads(http_get(geo_url))
            geo_data["_provenance"] = "live-recorded"
            geo_data["_source"] = geo_url
            geo_data["_recorded_at"] = now_iso
            geo_data["_place"] = p
            (om_dir / f"{slug}_geocoding.json").write_text(
                json.dumps(geo_data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            time.sleep(0.2)
        except Exception as e:
            print(f"Error fetching geocoding for {slug}: {e}")


def collect_aviation():
    av_dir = FIXTURES_DIR / "aviation"
    iem_dir = FIXTURES_DIR / "iem"
    av_dir.mkdir(parents=True, exist_ok=True)
    iem_dir.mkdir(parents=True, exist_ok=True)
    now_iso = datetime.now(timezone.utc).isoformat()

    stations = [
        {"code": "VIDP", "name": "Delhi Indira Gandhi Airport"},
        {"code": "VABB", "name": "Mumbai Chhatrapati Shivaji Airport"},
        {"code": "VOBL", "name": "Bengaluru Kempegowda Airport"},
        {"code": "VOMM", "name": "Chennai International Airport"},
        {"code": "VECC", "name": "Kolkata Netaji Subhash Chandra Bose Airport"},
    ]

    for st in stations:
        code = st["code"]
        print(f"Fetching Aviation / METAR for {code}...")

        # AviationWeather METAR
        metar_url = f"https://aviationweather.gov/api/data/metar?ids={code}&format=json"
        try:
            m_text = http_get(metar_url)
            m_data = json.loads(m_text)
            wrapper = {
                "_provenance": "live-recorded",
                "_source": metar_url,
                "_recorded_at": now_iso,
                "station": code,
                "name": st["name"],
                "data": m_data,
            }
            (av_dir / f"{code.lower()}_metar.json").write_text(
                json.dumps(wrapper, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            time.sleep(0.2)
        except Exception as e:
            print(f"Error fetching METAR for {code}: {e}")

        # AviationWeather TAF
        taf_url = f"https://aviationweather.gov/api/data/taf?ids={code}&format=json"
        try:
            t_text = http_get(taf_url)
            t_data = json.loads(t_text)
            wrapper = {
                "_provenance": "live-recorded",
                "_source": taf_url,
                "_recorded_at": now_iso,
                "station": code,
                "name": st["name"],
                "data": t_data,
            }
            (av_dir / f"{code.lower()}_taf.json").write_text(
                json.dumps(wrapper, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            time.sleep(0.2)
        except Exception as e:
            print(f"Error fetching TAF for {code}: {e}")

        # IEM METAR historical observations
        iem_url = (
            f"https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?station={code}"
            f"&data=tmpf&data=relh&data=sknt&data=drct&year1=2026&month1=11&day1=1"
            f"&year2=2026&month2=11&day2=5&tz=Etc/UTC&format=onlycomma"
        )
        try:
            iem_csv = http_get(iem_url)
            lines = [ln.strip() for ln in iem_csv.strip().splitlines() if ln.strip()]
            header = lines[0].split(",") if lines else []
            rows = [line.split(",") for line in lines[1:25]]
            wrapper = {
                "_provenance": "live-recorded",
                "_source": iem_url,
                "_recorded_at": now_iso,
                "station": code,
                "name": st["name"],
                "header": header,
                "rows": rows,
                "raw_sample": "\n".join(lines[:10]),
            }
            (iem_dir / f"{code.lower()}_iem_metar.json").write_text(
                json.dumps(wrapper, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            time.sleep(0.2)
        except Exception as e:
            print(f"Error fetching IEM for {code}: {e}")


if __name__ == "__main__":
    collect_sachet()
    collect_open_meteo()
    collect_aviation()
    print("Fixture collection completed.")
