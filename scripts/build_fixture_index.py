"""Build index of all recorded and documented fixtures."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = ROOT / "eval" / "fixtures"
INDEX_PATH = FIXTURES_DIR / "index.json"


def build_index():
    index_entries = []

    # 1. Sachet
    sachet_dir = FIXTURES_DIR / "sachet"
    for p in sorted(sachet_dir.glob("*.json")):
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        provenance = data.get("_provenance", "documented-sample")
        url = data.get("_source", data.get("source_url", "https://sachet.ndma.gov.in"))
        date = data.get("_recorded_at", data.get("sent", "2026-11-17"))
        rel_path = str(p.relative_to(ROOT)).replace("\\", "/")
        hazard = data.get("hazard", "")
        index_entries.append({
            "source": "sachet",
            "file": rel_path,
            "provenance": provenance,
            "date": date,
            "url": url,
            "hazard": hazard,
            "level": data.get("level", "yellow"),
        })

    # 2. Open-Meteo
    om_dir = FIXTURES_DIR / "open_meteo"
    for p in sorted(om_dir.glob("*.json")):
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        provenance = data.get("_provenance", "documented-sample")
        url = data.get("_source", "https://open-meteo.com")
        date = data.get("_recorded_at", "2026-11-17")
        rel_path = str(p.relative_to(ROOT)).replace("\\", "/")
        index_entries.append({
            "source": "open_meteo",
            "file": rel_path,
            "provenance": provenance,
            "date": date,
            "url": url,
        })

    # 3. AviationWeather
    av_dir = FIXTURES_DIR / "aviation"
    if av_dir.exists():
        for p in sorted(av_dir.glob("*.json")):
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
            provenance = data.get("_provenance", "live-recorded")
            url = data.get("_source", "https://aviationweather.gov")
            date = data.get("_recorded_at", "2026-11-17")
            rel_path = str(p.relative_to(ROOT)).replace("\\", "/")
            index_entries.append({
                "source": "aviationweather",
                "file": rel_path,
                "provenance": provenance,
                "date": date,
                "url": url,
                "station": data.get("station", ""),
            })

    # 4. IEM
    iem_dir = FIXTURES_DIR / "iem"
    if iem_dir.exists():
        for p in sorted(iem_dir.glob("*.json")):
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
            provenance = data.get("_provenance", "live-recorded")
            url = data.get("_source", "https://mesonet.agron.iastate.edu")
            date = data.get("_recorded_at", "2026-11-17")
            rel_path = str(p.relative_to(ROOT)).replace("\\", "/")
            index_entries.append({
                "source": "iem",
                "file": rel_path,
                "provenance": provenance,
                "date": date,
                "url": url,
                "station": data.get("station", ""),
            })

    # 5. IMD
    imd_dir = FIXTURES_DIR / "imd"
    for p in sorted(imd_dir.glob("*.json")):
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        provenance = data.get("_provenance", "documented-sample")
        url = data.get("_source", "https://api.imd.gov.in")
        date = data.get("_recorded_at", data.get("Date", "2026-11-17"))
        rel_path = str(p.relative_to(ROOT)).replace("\\", "/")
        index_entries.append({
            "source": "imd",
            "file": rel_path,
            "provenance": provenance,
            "date": date,
            "url": url,
        })

    with INDEX_PATH.open("w", encoding="utf-8") as f:
        json.dump(index_entries, f, indent=2, ensure_ascii=False)

    print(f"Built fixture index at {INDEX_PATH} with {len(index_entries)} entries.")


if __name__ == "__main__":
    build_index()
