"""SACHET CAP Alert Ingest Poller and Worker for WeatherGPT.

Relays official alerts from NDMA SACHET RSS feeds and CAP 1.2 XML files.
Follows truthfulness and security rules:
- Strictly relay official alerts; keep LLM out of the alert path.
- Enforce allowlist: only sachet.ndma.gov.in is accepted.
- Enforce 5-minute maximum poll rate (min_poll_interval_seconds = 300).
- Use HTTP conditional requests (ETag and If-Modified-Since).
- Deduplicate by CAP identifier; handle Update and Cancel.
- Store alerts in database alerts table and AlertEngine.
- Measure alert freshness: time elapsed from CAP sent timestamp to ingest.
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import logging
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.contracts.validator import validate_schema  # noqa: E402
from services.api.app.evidence.models import AlertModel  # noqa: E402
from services.api.app.modules.alerts.engine import AlertEngine  # noqa: E402
from services.api.app.modules.alerts.router import _engine as global_alert_engine  # noqa: E402
from services.api.app.modules.alerts.sachet_adapter import SachetCAPAdapter  # noqa: E402

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

DEFAULT_SACHET_RSS = "https://sachet.ndma.gov.in/cap_public_website/rss/allindia.xml"
DEFAULT_MIN_POLL_INTERVAL = 300  # 5 minutes in seconds


def get_git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, cwd=str(ROOT)).strip()
    except Exception:
        return "unknown"


class SachetAlertPoller:
    """Poller for NDMA SACHET RSS and CAP 1.2 XML alert feeds."""

    def __init__(
        self,
        feed_urls: list[str] | None = None,
        min_poll_interval_seconds: int = DEFAULT_MIN_POLL_INTERVAL,
        adapter: SachetCAPAdapter | None = None,
        alert_engine: AlertEngine | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self.feed_urls = feed_urls or [DEFAULT_SACHET_RSS]
        self.min_poll_interval_seconds = min_poll_interval_seconds
        self.adapter = adapter or SachetCAPAdapter()
        self.alert_engine = alert_engine if alert_engine is not None else global_alert_engine
        self.session_factory = session_factory
        # Cache per feed_url: {"etag": str | None, "last_modified": str | None, "last_poll": float}
        self.headers_cache: dict[str, dict[str, Any]] = {}

    def get_cached_headers(self, feed_url: str) -> dict[str, str]:
        entry = self.headers_cache.get(feed_url, {})
        res: dict[str, str] = {}
        if entry.get("etag"):
            res["etag"] = entry["etag"]
        if entry.get("last_modified"):
            res["last_modified"] = entry["last_modified"]
        return res

    def is_url_allowed(self, url: str) -> bool:
        return self.adapter.is_sender_allowed(url)

    async def fetch_feed(
        self,
        feed_url: str,
        client: httpx.AsyncClient | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Fetch RSS feed with rate-limiting and conditional headers."""
        if not self.is_url_allowed(feed_url):
            raise ValueError(f"URL is not allowlisted: {feed_url}")

        now_ts = time.time()
        cache_entry = self.headers_cache.setdefault(feed_url, {})
        last_poll = cache_entry.get("last_poll", 0.0)

        if not force and (now_ts - last_poll) < self.min_poll_interval_seconds:
            elapsed = now_ts - last_poll
            logger.warning(
                "Rate limit: %s was polled %.1fs ago (min interval %ds)",
                feed_url,
                elapsed,
                self.min_poll_interval_seconds,
            )
            return {
                "status": 429,
                "rate_limited": True,
                "message": f"Poll interval must be at least {self.min_poll_interval_seconds}s",
                "feed_url": feed_url,
            }

        headers: dict[str, str] = {}
        if cache_entry.get("etag"):
            headers["If-None-Match"] = cache_entry["etag"]
        if cache_entry.get("last_modified"):
            headers["If-Modified-Since"] = cache_entry["last_modified"]

        t0 = time.perf_counter()
        if client:
            resp = await client.get(feed_url, headers=headers)
        else:
            async with httpx.AsyncClient(timeout=15.0) as default_client:
                resp = await default_client.get(feed_url, headers=headers)
        latency_ms = (time.perf_counter() - t0) * 1000.0
        cache_entry["last_poll"] = time.time()

        logger.info(
            "Fetched feed %s -> status %d (%.1f ms)",
            feed_url,
            resp.status_code,
            latency_ms,
        )

        if resp.status_code == 304:
            return {
                "status": 304,
                "latency_ms": latency_ms,
                "feed_url": feed_url,
                "text": "",
                "headers": dict(resp.headers),
            }

        if resp.status_code == 200:
            if "ETag" in resp.headers:
                cache_entry["etag"] = resp.headers["ETag"]
            if "Last-Modified" in resp.headers:
                cache_entry["last_modified"] = resp.headers["Last-Modified"]

        return {
            "status": resp.status_code,
            "latency_ms": latency_ms,
            "feed_url": feed_url,
            "text": resp.text,
            "headers": dict(resp.headers),
        }

    def process_cap_xml(self, xml_text: str, source_url: str) -> AlertModel | None:
        """Parse CAP XML, validate schema, and return AlertModel."""
        parsed = self.adapter.parse(xml_text=xml_text, source_url=source_url)
        if parsed is None:
            return None
        clean = {k: v for k, v in parsed.items() if not k.startswith("_")}
        validate_schema("alert", clean)
        return AlertModel(**clean)

    async def save_alert(
        self,
        alert: AlertModel,
        session: AsyncSession | None = None,
    ) -> None:
        """Store alert in AlertEngine and database alerts table."""
        self.alert_engine.ingest_alert(alert)

        if session:
            await self.alert_engine.save_alert_to_db(alert, session)
        elif self.session_factory:
            async with self.session_factory() as sess:
                await self.alert_engine.save_alert_to_db(alert, sess)

    async def poll_feed(
        self,
        feed_url: str,
        client: httpx.AsyncClient | None = None,
        force: bool = False,
        session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Poll feed, retrieve new CAP items, store alerts, and measure freshness."""
        res = await self.fetch_feed(feed_url=feed_url, client=client, force=force)
        if res.get("status") != 200:
            return res

        rss_text = res.get("text", "")
        items = self.adapter.fetch_rss_items(rss_text)
        ingested_alerts: list[AlertModel] = []
        freshness_records: list[float] = []

        now_utc = dt.datetime.now(dt.timezone.utc)

        for item in items:
            link = item.get("link", "")
            if not self.is_url_allowed(link):
                logger.warning("Skipping non-allowlisted CAP item: %s", link)
                continue

            t0 = time.perf_counter()
            if client:
                xml_resp = await client.get(link)
            else:
                async with httpx.AsyncClient(timeout=15.0) as default_client:
                    xml_resp = await default_client.get(link)
            xml_latency_ms = (time.perf_counter() - t0) * 1000.0

            if xml_resp.status_code != 200:
                logger.warning("Failed to fetch CAP XML %s: HTTP %d", link, xml_resp.status_code)
                continue

            logger.info("Fetched CAP XML %s (%.1f ms)", link, xml_latency_ms)
            alert = self.process_cap_xml(xml_resp.text, source_url=link)
            if alert:
                await self.save_alert(alert, session=session)
                ingested_alerts.append(alert)

                sent_dt = alert.sent if isinstance(alert.sent, dt.datetime) else dt.datetime.fromisoformat(str(alert.sent).replace("Z", "+00:00"))
                freshness_sec = max(0.0, (now_utc - sent_dt).total_seconds())
                freshness_records.append(freshness_sec)
                logger.info(
                    "Alert %s ingested (hazard=%s, level=%s, freshness=%.1fs)",
                    alert.id,
                    alert.hazard,
                    alert.level,
                    freshness_sec,
                )

        return {
            "status": 200,
            "feed_url": feed_url,
            "latency_ms": res.get("latency_ms", 0.0),
            "alerts_count": len(ingested_alerts),
            "freshness_records": freshness_records,
        }

    async def poll_once(
        self,
        feed_url: str | None = None,
        client: httpx.AsyncClient | None = None,
        force: bool = False,
        session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Poll the specified feed or all configured feeds once."""
        urls = [feed_url] if feed_url else self.feed_urls
        results = []
        for url in urls:
            r = await self.poll_feed(url, client=client, force=force, session=session)
            results.append(r)
        return {
            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
            "results": results,
            "total_alerts": sum(r.get("alerts_count", 0) for r in results),
        }

    def replay_fixtures_and_measure(
        self,
        fixtures_dir: Path | None = None,
        output_report_path: Path | None = None,
    ) -> dict[str, Any]:
        """Replay recorded real fixtures from eval/fixtures/sachet/ and measure freshness."""
        f_dir = fixtures_dir or (ROOT / "eval" / "fixtures" / "sachet")
        if not f_dir.exists():
            raise FileNotFoundError(f"Fixtures directory not found: {f_dir}")

        json_files = sorted(f_dir.glob("*.json"))
        replayed_alerts: list[AlertModel] = []
        freshness_list: list[float] = []
        alert_details: list[dict[str, Any]] = []

        now_utc = dt.datetime.now(dt.timezone.utc)

        for jf in json_files:
            try:
                with jf.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                clean = {k: v for k, v in data.items() if not k.startswith("_")}
                validate_schema("alert", clean)
                alert = AlertModel(**clean)
                self.alert_engine.ingest_alert(alert)
                replayed_alerts.append(alert)

                sent_dt = alert.sent if isinstance(alert.sent, dt.datetime) else dt.datetime.fromisoformat(str(alert.sent).replace("Z", "+00:00"))
                # Measure freshness: elapsed time from CAP sent time to current ingest availability
                freshness_sec = max(0.0, (now_utc - sent_dt).total_seconds())
                freshness_list.append(freshness_sec)

                alert_details.append({
                    "id": alert.id,
                    "fixture_file": jf.name,
                    "sender": alert.sender,
                    "hazard": alert.hazard,
                    "severity": alert.severity,
                    "level": alert.level,
                    "sent": sent_dt.isoformat(),
                    "freshness_seconds": round(freshness_sec, 2),
                })
            except Exception as exc:
                logger.warning("Error replaying fixture %s: %s", jf.name, exc)

        if not freshness_list:
            raise ValueError(f"No valid alert fixtures found in {f_dir}")

        stats = {
            "git_sha": get_git_sha(),
            "measured_at": now_utc.isoformat(),
            "provenance": "replayed_real_fixtures",
            "fixtures_directory": str(f_dir.relative_to(ROOT) if f_dir.is_relative_to(ROOT) else f_dir),
            "count": len(replayed_alerts),
            "min_seconds": round(min(freshness_list), 2),
            "max_seconds": round(max(freshness_list), 2),
            "median_seconds": round(statistics.median(freshness_list), 2),
            "mean_seconds": round(statistics.mean(freshness_list), 2),
            "alerts": alert_details,
        }

        out_path = output_report_path or (ROOT / "reports" / "alert_freshness.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as out_f:
            json.dump(stats, out_f, indent=2)

        logger.info(
            "Replayed %d fixtures. Freshness min=%.1fs, median=%.1fs, max=%.1fs. Written to %s",
            len(replayed_alerts),
            stats["min_seconds"],
            stats["median_seconds"],
            stats["max_seconds"],
            out_path,
        )
        return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="WeatherGPT SACHET Alert Ingest Poller")
    parser.add_argument("--once", action="store_true", help="Poll once and exit")
    parser.add_argument("--replay", action="store_true", help="Replay real fixtures and measure freshness")
    parser.add_argument("--feed-url", type=str, default=DEFAULT_SACHET_RSS, help="SACHET RSS feed URL")
    parser.add_argument("--interval", type=int, default=DEFAULT_MIN_POLL_INTERVAL, help="Poll interval in seconds")
    args = parser.parse_args()

    poller = SachetAlertPoller(
        feed_urls=[args.feed_url],
        min_poll_interval_seconds=args.interval,
    )

    if args.replay:
        print("Replaying real fixtures from eval/fixtures/sachet/...")
        stats = poller.replay_fixtures_and_measure()
        print(f"Replay complete: {stats['count']} alerts processed.")
        print(f"Freshness stats: min={stats['min_seconds']}s, median={stats['median_seconds']}s, max={stats['max_seconds']}s")
        print("Report written to reports/alert_freshness.json")
        return 0

    if args.once:
        print(f"Polling SACHET feed {args.feed_url} once...")
        res = asyncio.run(poller.poll_once(feed_url=args.feed_url, force=True))
        print("Poll completed:", json.dumps(res, indent=2))
        return 0

    print(f"Starting SACHET poller loop (interval {args.interval}s)...")
    while True:
        try:
            res = asyncio.run(poller.poll_once(feed_url=args.feed_url))
            print(f"[{dt.datetime.now().isoformat()}] Polled feed: {res}")
        except Exception as exc:
            logger.error("Polling error: %s", exc)
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
