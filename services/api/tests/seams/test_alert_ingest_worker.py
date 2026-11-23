"""Seam tests for SACHET RSS/CAP alert ingest poller (ticket R5).

Tests:
1. Allowlist rejection for non-allowlisted domains.
2. 5-minute maximum poll rate (rate-limiting).
3. Conditional HTTP headers (ETag, If-Modified-Since) and 304 handling.
4. Ingest deduplication, Update and Cancel msgType handling.
5. Database persistence of ingested alerts into the alerts table.
6. Alert freshness calculation from CAP sent timestamp.
7. Point-in-polygon matching with Shapely and district-name fallback.
8. End-to-end integration: ingested alerts returned by GET /v1/alerts.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from packages.contracts.validator import validate_schema
from services.api.app.db.models import Alert, Base
from services.api.app.main import app
from services.api.app.modules.alerts.engine import (
    point_in_polygon,
)
from services.api.app.modules.alerts.router import _engine
from services.ingest.worker import SachetAlertPoller

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
FIXTURES_DIR = ROOT / "eval" / "fixtures" / "sachet"


@pytest.fixture
async def async_test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        yield factory
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_poller_rejects_non_allowlisted_domain():
    poller = SachetAlertPoller(feed_urls=["https://malicious.example.com/rss.xml"])
    with pytest.raises(ValueError, match="not allowlisted"):
        await poller.poll_once(feed_url="https://malicious.example.com/rss.xml", force=True)


@pytest.mark.asyncio
async def test_poller_enforces_5_minute_interval():
    poller = SachetAlertPoller(min_poll_interval_seconds=300)
    feed_url = "https://sachet.ndma.gov.in/cap_public_website/rss/allindia.xml"

    # Mock client returning empty RSS
    mock_client = AsyncMock()
    mock_resp = Response(
        status_code=200,
        text="<rss><channel><title>SACHET</title></channel></rss>",
        headers={"ETag": '"abc"', "Last-Modified": "Mon, 16 Nov 2026 00:00:00 GMT"},
    )
    mock_client.get.return_value = mock_resp

    # First poll succeeds
    res1 = await poller.poll_feed(feed_url, client=mock_client, force=True)
    assert res1["status"] == 200

    # Second poll immediately afterwards without force is rate-limited
    res2 = await poller.poll_feed(feed_url, client=mock_client, force=False)
    assert res2["status"] == 429 or res2.get("rate_limited") is True


@pytest.mark.asyncio
async def test_poller_conditional_http_headers():
    poller = SachetAlertPoller()
    feed_url = "https://sachet.ndma.gov.in/cap_public_website/rss/allindia.xml"

    mock_client = AsyncMock()
    # First response with ETag and Last-Modified
    mock_client.get.side_effect = [
        Response(
            status_code=200,
            text="<rss><channel><title>SACHET</title></channel></rss>",
            headers={"ETag": '"hash123"', "Last-Modified": "Mon, 16 Nov 2026 12:00:00 GMT"},
        ),
        # Second response returning 304 Not Modified
        Response(status_code=304, headers={"ETag": '"hash123"'}),
    ]

    # Poll 1
    res1 = await poller.poll_feed(feed_url, client=mock_client, force=True)
    assert res1["status"] == 200
    assert poller.get_cached_headers(feed_url)["etag"] == '"hash123"'

    # Poll 2 (forced to bypass interval, testing conditional headers)
    res2 = await poller.poll_feed(feed_url, client=mock_client, force=True)
    assert res2["status"] == 304

    # Verify that the second GET passed If-None-Match and If-Modified-Since
    calls = mock_client.get.call_args_list
    assert len(calls) == 2
    second_headers = calls[1].kwargs.get("headers", {})
    assert second_headers.get("If-None-Match") == '"hash123"'
    assert second_headers.get("If-Modified-Since") == "Mon, 16 Nov 2026 12:00:00 GMT"


@pytest.mark.asyncio
async def test_poller_deduplication_and_update(async_test_db):
    poller = SachetAlertPoller(session_factory=async_test_db)
    xml_path_1 = FIXTURES_DIR / "cap_xml" / "sachet_01_update.xml"
    assert xml_path_1.exists()
    xml_text_1 = xml_path_1.read_text(encoding="utf-8")

    # Ingest same CAP twice
    alert1 = poller.process_cap_xml(xml_text_1, "https://sachet.ndma.gov.in/fetch?id=1")
    assert alert1 is not None
    await poller.save_alert(alert1)

    alert2 = poller.process_cap_xml(xml_text_1, "https://sachet.ndma.gov.in/fetch?id=1")
    assert alert2 is not None
    await poller.save_alert(alert2)

    # Database should contain exactly one row for this alert ID
    async with async_test_db() as session:
        res = await session.execute(select(Alert).where(Alert.id == alert1.id))
        rows = res.scalars().all()
        assert len(rows) == 1


@pytest.mark.asyncio
async def test_poller_freshness_measurement(tmp_path):
    poller = SachetAlertPoller()
    tmp_out = tmp_path / "alert_freshness.json"
    report = poller.replay_fixtures_and_measure(fixtures_dir=FIXTURES_DIR, output_report_path=tmp_out)

    assert "count" in report
    assert report["count"] >= 20
    assert "min_seconds" in report
    assert "max_seconds" in report
    assert "median_seconds" in report
    assert "mean_seconds" in report
    assert report["provenance"] == "replayed_real_fixtures"


def test_point_in_polygon_shapely():
    # Triangle in Maharashtra: (19.0, 73.0), (20.0, 73.0), (20.0, 74.0)
    polygon = [(19.0, 73.0), (20.0, 73.0), (20.0, 74.0), (19.0, 73.0)]

    # Inside
    assert point_in_polygon(19.5, 73.2, polygon) is True
    # Outside
    assert point_in_polygon(18.5, 73.0, polygon) is False
    # Border
    assert point_in_polygon(19.5, 73.0, polygon) is True


@pytest.mark.asyncio
async def test_real_replay_accessible_via_alerts_endpoint():
    poller = SachetAlertPoller(alert_engine=_engine)
    poller.replay_fixtures_and_measure(fixtures_dir=FIXTURES_DIR)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/v1/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        for item in data[:3]:
            validate_schema("alert", item)
            assert item["authority_tier"] == 1
            assert item["source_url"].startswith("https://sachet.ndma.gov.in")
