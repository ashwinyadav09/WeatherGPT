from __future__ import annotations

import datetime as dt
import json
import time
from pathlib import Path
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()

ROOT = Path(__file__).resolve().parents[5]
FIXTURES_DIR = ROOT / "eval" / "fixtures" / "aviation"


class AviationWeatherAdapter:
    """Adapter for AviationWeather.gov METAR and TAF data with strict caching and rate limiting."""

    def __init__(
        self,
        base_url: str = "https://aviationweather.gov/api/data",
        client: httpx.AsyncClient | None = None,
        cache_ttl_seconds: int = 300,  # 5 minutes
    ) -> None:
        self.base_url = base_url
        self._client = client
        self.cache_ttl_seconds = cache_ttl_seconds
        self._metar_cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._taf_cache: dict[str, tuple[float, dict[str, Any]]] = {}

        # Rate limiting state: max 100 req/min overall, max 1 req/min per station endpoint
        self._recent_requests: list[float] = []
        self._station_last_request: dict[str, float] = {}

    def _check_rate_limit(self, station: str, endpoint: str) -> bool:
        """Enforces AviationWeather.gov limits: <=100 req/min global, <=1 req/min per endpoint."""
        now = time.time()
        # Clean timestamps older than 60s
        self._recent_requests = [t for t in self._recent_requests if now - t < 60.0]
        if len(self._recent_requests) >= 100:
            logger.warning("aviation_global_rate_limit_reached", count=len(self._recent_requests))
            return False

        station_key = f"{endpoint}:{station.upper()}"
        last_req = self._station_last_request.get(station_key, 0.0)
        if now - last_req < 60.0:
            logger.info("aviation_endpoint_rate_limited_using_cache", station=station, endpoint=endpoint)
            return False

        self._recent_requests.append(now)
        self._station_last_request[station_key] = now
        return True

    async def get_metar(self, station: str) -> dict[str, Any]:
        """Fetches METAR with cache-first and rate-limit guard, falling back to recorded fixtures."""
        station = station.strip().upper()
        now = time.time()

        # 1. Check cache
        if station in self._metar_cache:
            cached_at, cached_data = self._metar_cache[station]
            if now - cached_at < self.cache_ttl_seconds:
                res = dict(cached_data)
                res["is_cached"] = True
                return res

        # 2. Check rate limit
        can_call = self._check_rate_limit(station, "metar")

        # 3. Call upstream if allowed
        if can_call:
            url = f"{self.base_url}/metar?ids={station}&format=json"
            try:
                if self._client:
                    resp = await self._client.get(url, timeout=5.0)
                    resp.raise_for_status()
                    data = resp.json()
                else:
                    async with httpx.AsyncClient(timeout=5.0) as cli:
                        resp = await cli.get(url)
                        resp.raise_for_status()
                        data = resp.json()

                if data and isinstance(data, list) and len(data) > 0:
                    raw_ob = data[0].get("rawOb", "")
                    obs_time_epoch = data[0].get("obsTime")
                    obs_dt = (
                        dt.datetime.fromtimestamp(obs_time_epoch, dt.timezone.utc)
                        if obs_time_epoch
                        else dt.datetime.now(dt.timezone.utc)
                    )
                    parsed = {
                        "raw": raw_ob,
                        "station": station,
                        "time_utc": obs_dt.isoformat(),
                        "source": "AviationWeather.gov (NOAA)",
                        "is_cached": False,
                    }
                    self._metar_cache[station] = (now, parsed)
                    return parsed
            except Exception as e:
                logger.warning("aviation_metar_upstream_failed", station=station, error=str(e))

        # 4. Fallback: Return existing stale cache if present
        if station in self._metar_cache:
            _, stale_data = self._metar_cache[station]
            res = dict(stale_data)
            res["is_cached"] = True
            return res

        # 5. Fallback: Load recorded fixture
        fix = self._load_fixture(station)
        if fix and "metar" in fix:
            res = dict(fix["metar"])
            res["is_cached"] = True
            res["source"] = "WeatherGPT Aviation Fixture (Documented Sample)"
            self._metar_cache[station] = (now, res)
            return res

        raise ValueError(f"No METAR available for station '{station}'")

    async def get_taf(self, station: str) -> dict[str, Any]:
        """Fetches TAF with cache-first and rate-limit guard, falling back to recorded fixtures."""
        station = station.strip().upper()
        now = time.time()

        # 1. Check cache
        if station in self._taf_cache:
            cached_at, cached_data = self._taf_cache[station]
            if now - cached_at < (self.cache_ttl_seconds * 3):  # TAF cached longer
                res = dict(cached_data)
                res["is_cached"] = True
                return res

        # 2. Check rate limit
        can_call = self._check_rate_limit(station, "taf")

        # 3. Call upstream if allowed
        if can_call:
            url = f"{self.base_url}/taf?ids={station}&format=json"
            try:
                if self._client:
                    resp = await self._client.get(url, timeout=5.0)
                    resp.raise_for_status()
                    data = resp.json()
                else:
                    async with httpx.AsyncClient(timeout=5.0) as cli:
                        resp = await cli.get(url)
                        resp.raise_for_status()
                        data = resp.json()

                if data and isinstance(data, list) and len(data) > 0:
                    raw_taf = data[0].get("rawTAF", "")
                    issue_time = dt.datetime.now(dt.timezone.utc)
                    valid_from = issue_time
                    valid_to = issue_time + dt.timedelta(hours=30)
                    parsed = {
                        "raw": raw_taf,
                        "station": station,
                        "issue_time_utc": issue_time.isoformat(),
                        "valid_from": valid_from.isoformat(),
                        "valid_to": valid_to.isoformat(),
                        "source": "AviationWeather.gov (NOAA)",
                        "is_cached": False,
                    }
                    self._taf_cache[station] = (now, parsed)
                    return parsed
            except Exception as e:
                logger.warning("aviation_taf_upstream_failed", station=station, error=str(e))

        # 4. Fallback: Return stale cache
        if station in self._taf_cache:
            _, stale_data = self._taf_cache[station]
            res = dict(stale_data)
            res["is_cached"] = True
            return res

        # 5. Fallback: Load recorded fixture
        fix = self._load_fixture(station)
        if fix and "taf" in fix:
            res = dict(fix["taf"])
            res["is_cached"] = True
            res["source"] = "WeatherGPT Aviation Fixture (Documented Sample)"
            self._taf_cache[station] = (now, res)
            return res

        raise ValueError(f"No TAF available for station '{station}'")

    def _load_fixture(self, station: str) -> dict[str, Any] | None:
        """Loads documented fixture from eval/fixtures/aviation/ if available."""
        fix_path = FIXTURES_DIR / f"{station.lower()}_sample.json"
        if fix_path.exists():
            try:
                with fix_path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("failed_to_load_aviation_fixture", station=station, error=str(e))
        return None
