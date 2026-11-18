from __future__ import annotations

import re
from typing import Any

from services.api.app.evidence.models import PlaceModel
from services.api.app.modules.location.adapters.open_meteo_geocoding import OpenMeteoGeocodingAdapter
from services.api.app.modules.location.data import INDIA_PLACES, PLACES_BY_ID
from services.api.app.modules.location.normalization import (
    CANONICAL_ALIASES,
    extract_potential_place_tokens,
    normalize_text,
)

# Export SEED_PLACES for backward compatibility
SEED_PLACES = INDIA_PLACES

GPS_PATTERN = re.compile(r"(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)")

# Ambiguous place sets mapped by common normalized name
AMBIGUOUS_SETS: dict[str, list[str]] = {
    "bilaspur": ["bilaspur_cg", "bilaspur_hp"],
    "बिलासपुर": ["bilaspur_cg", "bilaspur_hp"],
    "aurangabad": ["aurangabad_mh", "aurangabad_bihar"],
    "औरंगाबाद": ["aurangabad_mh", "aurangabad_bihar"],
    "rampur": ["rampur_up", "rampur_hp"],
    "रामपुर": ["rampur_up", "rampur_hp"],
    "pratapgarh": ["pratapgarh_up", "pratapgarh_rj"],
    "प्रतापगढ़": ["pratapgarh_up", "pratapgarh_rj"],
    "hamirpur": ["hamirpur_up", "hamirpur_hp"],
    "हमीरपुर": ["hamirpur_up", "hamirpur_hp"],
}

# Saved place keywords mapping to canonical role
SAVED_PLACE_KEYWORDS: dict[str, str] = {
    "home": "home",
    "ghar": "home",
    "घर": "home",
    "farm": "farm",
    "khet": "farm",
    "खेत": "farm",
    "work": "work",
    "office": "work",
    "काम": "work",
    "दफ्तर": "work",
    "कार्यालय": "work",
}

DEFAULT_SAVED_PLACES: dict[str, PlaceModel] = {
    "home": PlaceModel(
        id="saved_home",
        kind="point",
        names={"en": "Home (Pune)", "hi": "घर (पुणे)"},
        lat=18.5204,
        lon=73.8567,
        elevation=560.0,
        state="Maharashtra",
        district="Pune",
    ),
    "farm": PlaceModel(
        id="saved_farm",
        kind="point",
        names={"en": "Farm (Baramati)", "hi": "खेत (बारामती)"},
        lat=18.1517,
        lon=74.5774,
        elevation=538.0,
        state="Maharashtra",
        district="Pune",
    ),
    "work": PlaceModel(
        id="saved_work",
        kind="point",
        names={"en": "Work (Mumbai)", "hi": "दफ्तर (मुंबई)"},
        lat=19.0760,
        lon=72.8777,
        elevation=14.0,
        state="Maharashtra",
        district="Mumbai City",
    ),
}


class LocationResolver:
    def __init__(self, geocoder: OpenMeteoGeocodingAdapter | None = None) -> None:
        self.geocoder = geocoder or OpenMeteoGeocodingAdapter()

    async def search(self, query: str, language: str = "en") -> list[PlaceModel]:
        """Search places by text query, using local database and alias expansion."""
        norm_q = normalize_text(query)
        if not norm_q:
            return []

        # Check for direct alias
        if norm_q in CANONICAL_ALIASES:
            canonical_id = CANONICAL_ALIASES[norm_q]
            if canonical_id in PLACES_BY_ID:
                return [PLACES_BY_ID[canonical_id]]

        # Search in INDIA_PLACES
        matches: list[PlaceModel] = []
        for p in INDIA_PLACES:
            for lang_code, name in p.names.items():
                norm_name = normalize_text(name)
                if norm_name == norm_q or norm_q in norm_name:
                    matches.append(p)
                    break

        if matches:
            return matches

        # Fallback to geocoder if online
        try:
            return await self.geocoder.search(query=query, language=language)
        except Exception:
            return []

    async def resolve(
        self,
        text: str,
        language: str = "en",
        hint: str | None = None,
        saved_places: dict[str, PlaceModel] | None = None,
    ) -> dict[str, Any]:
        """Resolve a conversational query, GPS coordinate or place name into a grounded PlaceModel."""
        clean_text = text.strip()
        norm_text = normalize_text(clean_text)

        # 1. GPS coordinates check
        gps_match = GPS_PATTERN.search(clean_text)
        if gps_match:
            lat = float(gps_match.group(1))
            lon = float(gps_match.group(2))
            gps_place = PlaceModel(
                id=f"gps_{lat:.4f}_{lon:.4f}",
                kind="point",
                names={"en": f"Location ({lat:.2f}, {lon:.2f})", "hi": f"स्थान ({lat:.2f}, {lon:.2f})"},
                lat=lat,
                lon=lon,
                elevation=None,
                state=None,
                district=None,
            )
            return {
                "places": [gps_place],
                "ambiguous": False,
                "clarification_question": None,
                "resolved_place": gps_place,
            }

        # 2. Saved place check (home, farm, work, घर, खेत, काम)
        active_saved = saved_places or DEFAULT_SAVED_PLACES
        for word in norm_text.split():
            if word in SAVED_PLACE_KEYWORDS:
                role = SAVED_PLACE_KEYWORDS[word]
                if role in active_saved:
                    place = active_saved[role]
                    return {
                        "places": [place],
                        "ambiguous": False,
                        "clarification_question": None,
                        "resolved_place": place,
                    }

        # 3. Check for ambiguous places (e.g. Bilaspur, Aurangabad, Rampur)
        tokens = extract_potential_place_tokens(clean_text)
        ambiguous_key = None
        for t in tokens:
            if t in AMBIGUOUS_SETS:
                ambiguous_key = t
                break

        if ambiguous_key:
            candidate_ids = AMBIGUOUS_SETS[ambiguous_key]
            candidates = [PLACES_BY_ID[cid] for cid in candidate_ids if cid in PLACES_BY_ID]

            # If a hint or state is provided in query or hint parameter, disambiguate directly
            state_hint = (hint or "").lower()
            resolved_candidate = None

            for c in candidates:
                c_state = (c.state or "").lower()
                c_district = (c.district or "").lower()
                if (
                    (state_hint and (state_hint in c_state or state_hint in c_district))
                    or c_state in norm_text
                    or (c_state == "himachal pradesh" and any(k in norm_text for k in ["hp", "himachal", "हिमाचल"]))
                    or (c_state == "chhattisgarh" and any(k in norm_text for k in ["cg", "chhattisgarh", "छत्तीसगढ़"]))
                    or (c_state == "maharashtra" and any(k in norm_text for k in ["mh", "maharashtra", "महाराष्ट्र"]))
                    or (c_state == "bihar" and any(k in norm_text for k in ["bihar", "बिहार"]))
                    or (c_state == "uttar pradesh" and any(k in norm_text for k in ["up", "uttar pradesh", "उत्तर प्रदेश"]))
                    or (c_state == "rajasthan" and any(k in norm_text for k in ["rj", "rajasthan", "राजस्थान"]))
                ):
                    resolved_candidate = c
                    break

            if resolved_candidate:
                return {
                    "places": [resolved_candidate],
                    "ambiguous": False,
                    "clarification_question": None,
                    "resolved_place": resolved_candidate,
                }

            # Generate exactly one clarifying question
            cand_names_en = [f"{c.names.get('en', c.id)} in {c.state}" for c in candidates]
            cand_names_hi = [f"{c.names.get('hi', c.names.get('en', ''))} ({c.state})" for c in candidates]

            if language == "hi":
                q = f"क्या आपका मतलब {' या '.join(cand_names_hi)} है?"
            else:
                q = f"Did you mean {' or '.join(cand_names_en)}?"

            return {
                "places": candidates,
                "ambiguous": True,
                "clarification_question": q,
                "resolved_place": candidates[0],  # Default to first candidate
            }

        # 4. Check for alias match
        for t in tokens:
            if t in CANONICAL_ALIASES:
                cid = CANONICAL_ALIASES[t]
                if cid in PLACES_BY_ID:
                    place = PLACES_BY_ID[cid]
                    return {
                        "places": [place],
                        "ambiguous": False,
                        "clarification_question": None,
                        "resolved_place": place,
                    }

        # 5. Exact and substring match in INDIA_PLACES
        matched: list[PlaceModel] = []
        for t in tokens:
            for p in INDIA_PLACES:
                for name in p.names.values():
                    norm_name = normalize_text(name)
                    if norm_name == t or t == norm_name:
                        if p not in matched:
                            matched.append(p)
                        break

        # If not exact match on tokens, search substring
        if not matched:
            for p in INDIA_PLACES:
                for name in p.names.values():
                    norm_name = normalize_text(name)
                    if norm_name in norm_text or norm_text in norm_name:
                        if p not in matched:
                            matched.append(p)
                        break

        # If still no match, fallback to geocoder or default Pune
        if not matched:
            try:
                geocoded = await self.geocoder.search(query=clean_text, language=language)
                if geocoded:
                    matched = geocoded
            except Exception:
                pass

        resolved = matched[0] if matched else PLACES_BY_ID["pune"]

        return {
            "places": matched or [resolved],
            "ambiguous": len(matched) > 1 and matched[0].kind == matched[1].kind,
            "clarification_question": None,
            "resolved_place": resolved,
        }

    async def get_by_id(self, place_id: str) -> PlaceModel | None:
        """Retrieve place model by stable ID."""
        if place_id in PLACES_BY_ID:
            return PLACES_BY_ID[place_id]
        if place_id in DEFAULT_SAVED_PLACES:
            return DEFAULT_SAVED_PLACES[place_id]
        return None
