from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import pytest

from packages.contracts.validator import validate_schema
from services.api.app.agent.orchestrator import ChatRequest, Orchestrator
from services.api.app.agent.tools import search_knowledge
from services.api.app.modules.advisory.rag import RagEngine

ROOT = Path(__file__).resolve().parents[4]
KNOWLEDGE_DIR = ROOT / "seeds" / "knowledge"


def test_sources_csv_integrity():
    """Verify that sources.csv exists and sha256 checksums match knowledge files."""
    sources_file = KNOWLEDGE_DIR / "sources.csv"
    assert sources_file.exists(), "seeds/knowledge/sources.csv missing"

    with sources_file.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) >= 5
    for row in rows:
        fpath = KNOWLEDGE_DIR / row["filename"]
        assert fpath.exists(), f"File {row['filename']} listed in sources.csv not found"
        computed_hash = hashlib.sha256(fpath.read_bytes()).hexdigest()
        assert computed_hash == row["sha256"], f"Checksum mismatch for {row['filename']}"


def test_rag_engine_loading_and_retrieval():
    """Verify RagEngine loads corpus chunks and performs BM25, Dense, and Hybrid search."""
    rag = RagEngine(knowledge_dir=KNOWLEDGE_DIR)
    assert len(rag.chunks) >= 15

    # BM25 search
    bm25_res = rag.search_bm25("extreme heatwave precautions and drinking water", top_k=3)
    assert len(bm25_res) >= 1
    assert "heatwave" in bm25_res[0][0].chunk_id.lower()

    # Dense search
    dense_res = rag.search_dense("hypothermia and warm clothing in cold weather", top_k=3)
    assert len(dense_res) >= 1
    assert "coldwave" in dense_res[0][0].chunk_id.lower()

    # Hybrid search
    hybrid_res = rag.search("What is the 30-30 lightning safety rule?", mode="hybrid", top_k=3)
    assert len(hybrid_res) >= 1
    assert "flood_cyclone_safety" in hybrid_res[0][0].chunk_id.lower()


def test_rag_out_of_domain_fallback():
    """Verify that out-of-domain query triggers fallback with official helplines."""
    rag = RagEngine(knowledge_dir=KNOWLEDGE_DIR)
    evidence = rag.search_as_evidence("Which stocks should I purchase on Wall Street today?", lang="en")
    assert len(evidence) == 1
    top_pkt = evidence[0]
    val_map = {v["variable"]: v["value"] for v in top_pkt["values"]}
    assert val_map.get("chunk_id") == "no_official_guidance"
    assert "112" in str(val_map.get("guidance"))
    assert "1077" in str(val_map.get("guidance"))


@pytest.mark.asyncio
async def test_search_knowledge_tool():
    """Verify search_knowledge tool returns EvidencePackets conforming to contract."""
    packets = await search_knowledge("extreme heat precautions and ORS", lang="en")
    assert len(packets) >= 1
    p0 = packets[0]
    assert p0.authority_tier == 4
    val_map = {v.variable: v.value for v in p0.values}
    assert "chunk_id" in val_map
    assert "guidance" in val_map
    assert "ndma_heatwave" in str(val_map["chunk_id"])


@pytest.mark.asyncio
async def test_orchestrator_advisory_flow_with_rag():
    """Verify orchestrator routes an advice query to search_knowledge and emits trace."""
    orchestrator = Orchestrator()
    req = ChatRequest(
        session_id="test_rag_orch",
        text="What are the essential precautions during extreme heatwave in Delhi?",
        language="en",
    )

    events = [e async for e in orchestrator.handle_chat_stream(req)]
    event_names = [e["event"] for e in events]
    assert "meta" in event_names
    assert "evidence" in event_names
    assert "card" in event_names
    assert "trace" in event_names
    assert "done" in event_names

    trace_e = [e for e in events if e["event"] == "trace"][0]["data"]
    validate_schema("trace_event", trace_e)
    assert trace_e["intent"] == "advisory"
    assert any(t["name"] == "search_knowledge" for t in trace_e["tools"])

    token_text = "".join(e["data"]["text"] for e in events if e["event"] == "token")
    assert len(token_text) > 0
    # The answer should cite the chunk ID
    assert "[" in token_text and "]" in token_text
