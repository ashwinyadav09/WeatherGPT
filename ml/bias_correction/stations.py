"""Station metadata and coordinates for bias correction (Ticket R11).

Selected 12 primary Indian airport stations across distinct agro-climatic zones
with verified ICAO identifiers and coordinates matching IEM METAR metadata.
"""
from __future__ import annotations

from typing import TypedDict


class StationMeta(TypedDict):
    id: str
    name: str
    lat: float
    lon: float
    elev: float
    state: str
    zone: str


STATIONS: list[StationMeta] = [
    {"id": "VIDP", "name": "Delhi (Indira Gandhi Intl)", "lat": 28.5665, "lon": 77.1031, "elev": 237.0, "state": "Delhi", "zone": "Northern Plains"},
    {"id": "VABB", "name": "Mumbai (Chhatrapati Shivaji Intl)", "lat": 19.0887, "lon": 72.8679, "elev": 14.0, "state": "Maharashtra", "zone": "West Coast"},
    {"id": "VOBL", "name": "Bengaluru (Kempegowda Intl)", "lat": 13.1979, "lon": 77.7063, "elev": 915.0, "state": "Karnataka", "zone": "South Deccan"},
    {"id": "VOMM", "name": "Chennai (Meenambakkam Intl)", "lat": 12.9900, "lon": 80.1693, "elev": 16.0, "state": "Tamil Nadu", "zone": "East Coast"},
    {"id": "VECC", "name": "Kolkata (Netaji Subhash Intl)", "lat": 22.6547, "lon": 88.4467, "elev": 5.0, "state": "West Bengal", "zone": "Eastern Plains"},
    {"id": "VOHS", "name": "Hyderabad (Rajiv Gandhi Intl)", "lat": 17.2403, "lon": 78.4294, "elev": 617.0, "state": "Telangana", "zone": "Central Deccan"},
    {"id": "VIJP", "name": "Jaipur (Jaipur Intl)", "lat": 26.8242, "lon": 75.8122, "elev": 385.0, "state": "Rajasthan", "zone": "Semi-Arid Northwest"},
    {"id": "VABP", "name": "Bhopal (Raja Bhoj)", "lat": 23.2875, "lon": 77.3378, "elev": 524.0, "state": "Madhya Pradesh", "zone": "Central Plateau"},
    {"id": "VAPO", "name": "Pune (Pune Intl)", "lat": 18.5822, "lon": 73.9197, "elev": 592.0, "state": "Maharashtra", "zone": "Western Ghats Leeward"},
    {"id": "VEBS", "name": "Bhubaneswar (Biju Patnaik Intl)", "lat": 20.2444, "lon": 85.8178, "elev": 42.0, "state": "Odisha", "zone": "East Coast"},
    {"id": "VAAH", "name": "Ahmedabad (SVP Intl)", "lat": 23.0772, "lon": 72.6347, "elev": 58.0, "state": "Gujarat", "zone": "Western Plains"},
    {"id": "VANP", "name": "Nagpur (Dr. Babasaheb Ambedkar Intl)", "lat": 21.0922, "lon": 79.0583, "elev": 315.0, "state": "Maharashtra", "zone": "Central India"},
]

STATIONS_BY_ID = {s["id"]: s for s in STATIONS}
