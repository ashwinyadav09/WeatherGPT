from __future__ import annotations

import csv
import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from rank_bm25 import BM25Okapi

ROOT = Path(__file__).resolve().parents[5]
KNOWLEDGE_DIR = ROOT / "seeds" / "knowledge"

STOPWORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of", "with",
    "is", "are", "was", "were", "be", "been", "by", "from", "as", "into", "through",
    "during", "what", "which", "who", "whom", "this", "that", "these", "those",
    "am", "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us",
    "them", "my", "your", "his", "their", "our", "should", "would", "could", "can",
    "may", "might", "must", "shall", "will", "do", "does", "did", "have", "has", "had",
    "tell", "give", "recommend", "buy", "how", "when", "where", "why", "good", "best",
    "का", "के", "की", "में", "से", "को", "पर", "है", "हैं", "था", "थी", "थे", "और", "या", "तो", "भी", "ही",
    "लिए", "करना", "चाहिए", "सकते", "सकती", "सकता", "मुझे", "कौन", "कब", "कहाँ", "कहा", "जाने", "करनी",
    "काय", "करावे", "करावेत्", "ਕੀ", "কী", "ಏನು", "ఏమిటి", "என்ன", "କଣ", "ଉଚିତ", "হবে",
}


@dataclass
class KnowledgeChunk:
    chunk_id: str
    source: str
    title: str
    hazard: str
    language: str
    text: str
    retrieval_date: str
    url: str
    license: str
    page: int = 1
    sha256: str = ""


def _tokenize(text: str) -> list[str]:
    """Tokenize text into words and Indic character n-grams, filtering common stopwords."""
    cleaned = "".join(" " if unicodedata.category(c).startswith(("P", "S")) else c for c in text.lower())
    words = [w for w in cleaned.split() if len(w) > 1 and w not in STOPWORDS]
    ngrams: list[str] = []
    for w in words:
        if any(ord(c) > 127 for c in w) and len(w) >= 3:
            for n in (3, 4):
                for i in range(len(w) - n + 1):
                    ngrams.append(w[i : i + n])
    return words + ngrams


class MultilingualDenseRetriever:
    """Multilingual dense embedding retriever using intfloat/multilingual-e5-small."""

    def __init__(self, model_name: str = "intfloat/multilingual-e5-small") -> None:
        self.model_name = model_name
        self._model: Any = None

    def _get_model(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode_queries(self, queries: list[str]) -> np.ndarray:
        model = self._get_model()
        formatted = ["query: " + q for q in queries]
        return np.array(model.encode(formatted, normalize_embeddings=True, show_progress_bar=False), dtype=np.float32)

    def encode_passages(self, passages: list[str]) -> np.ndarray:
        model = self._get_model()
        formatted = ["passage: " + p for p in passages]
        return np.array(model.encode(formatted, normalize_embeddings=True, show_progress_bar=False), dtype=np.float32)


class RagEngine:
    """Advisory RAG Engine using chunked official corpus, BM25, Dense embeddings, and Hybrid ranking."""

    _instance: RagEngine | None = None

    def __init__(self, knowledge_dir: Path | None = None) -> None:
        self.knowledge_dir = knowledge_dir or KNOWLEDGE_DIR
        self.chunks: list[KnowledgeChunk] = []
        self.bm25: BM25Okapi | None = None
        self.dense_retriever = MultilingualDenseRetriever()
        self.chunk_vectors: np.ndarray | None = None
        self.sources_meta: dict[str, dict[str, str]] = {}
        self.load_corpus()

    @classmethod
    def get_instance(cls) -> RagEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_sources_meta(self) -> None:
        sources_csv = self.knowledge_dir / "sources.csv"
        if sources_csv.exists():
            with sources_csv.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.sources_meta[row["filename"]] = row

    def load_corpus(self) -> None:
        """Load official chunked corpus from chunks.json or reconstruct from markdown files."""
        self._load_sources_meta()
        self.chunks.clear()

        if not self.knowledge_dir.exists():
            return

        chunks_json_path = self.knowledge_dir / "chunks.json"
        if chunks_json_path.exists():
            try:
                data = json.loads(chunks_json_path.read_text(encoding="utf-8"))
                for item in data:
                    c = KnowledgeChunk(
                        chunk_id=item["chunk_id"],
                        source=item["source"],
                        title=item["title"],
                        hazard=item["hazard"],
                        language=item.get("language", "en"),
                        text=item["text"],
                        retrieval_date=item.get("retrieval_date", "2026-11-24"),
                        url=item.get("url", "https://ndma.gov.in"),
                        license=item.get("license", "OGDL-India"),
                        page=item.get("page", 1),
                        sha256=item.get("sha256", ""),
                    )
                    self.chunks.append(c)
            except Exception:
                self.chunks.clear()

        # Fallback to parsing markdown files if chunks.json empty
        if not self.chunks:
            for md_file in sorted(self.knowledge_dir.glob("*.md")):
                file_meta = self.sources_meta.get(md_file.name, {})
                source_title = file_meta.get("title", md_file.stem.replace("_", " ").title())
                url = file_meta.get("url", "https://ndma.gov.in")
                license_str = file_meta.get("license", "OGDL-India")
                rdate = file_meta.get("retrieval_date", "2026-11-24")

                content = md_file.read_text(encoding="utf-8")
                sections = content.split("\n## ")

                main_title = md_file.stem.replace("_", " ").title()
                first_section = sections[0].strip()
                if first_section.startswith("# "):
                    main_title = first_section.split("\n", 1)[0].replace("# ", "").strip()

                hazard = "general"
                fname_lower = md_file.stem.lower()
                if "heat" in fname_lower:
                    hazard = "heat_wave"
                elif "cold" in fname_lower:
                    hazard = "cold_wave"
                elif "flood" in fname_lower:
                    hazard = "flood"
                elif "agriculture" in fname_lower or "icar" in fname_lower:
                    hazard = "agriculture"
                elif "fisher" in fname_lower or "marine" in fname_lower:
                    hazard = "marine"
                elif "colour" in fname_lower or "color" in fname_lower:
                    hazard = "colour_code"

                for idx, sec in enumerate(sections[1:], start=1):
                    lines = sec.strip().split("\n")
                    heading = lines[0].strip()
                    body = "\n".join(lines[1:]).strip()

                    chunk_id = f"{md_file.stem}_{idx:02d}"
                    chunk = KnowledgeChunk(
                        chunk_id=chunk_id,
                        source=source_title,
                        title=f"{main_title} - {heading}",
                        hazard=hazard,
                        language="en",
                        text=f"## {heading}\n{body}",
                        retrieval_date=rdate,
                        url=url,
                        license=license_str,
                    )
                    self.chunks.append(chunk)

        # Build BM25 index
        if self.chunks:
            corpus_tokens = [_tokenize(f"{c.title}\n{c.text}") for c in self.chunks]
            self.bm25 = BM25Okapi(corpus_tokens)

            # Load or compute dense embeddings
            emb_file = self.knowledge_dir / "chunk_embeddings.npy"
            if emb_file.exists():
                try:
                    self.chunk_vectors = np.load(str(emb_file))
                except Exception:
                    self.chunk_vectors = None

            if self.chunk_vectors is None or len(self.chunk_vectors) != len(self.chunks):
                try:
                    corpus_texts = [f"{c.title}\n{c.text}" for c in self.chunks]
                    self.chunk_vectors = self.dense_retriever.encode_passages(corpus_texts)
                    np.save(str(emb_file), self.chunk_vectors)
                except Exception:
                    self.chunk_vectors = None

    def search_bm25(self, query: str, top_k: int = 5, threshold: float = 2.0) -> list[tuple[KnowledgeChunk, float]]:
        if not self.bm25 or not self.chunks:
            return []
        q_tokens = _tokenize(query)
        if not q_tokens:
            return []
        scores = self.bm25.get_scores(q_tokens)
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [(self.chunks[i], float(scores[i])) for i in top_indices if scores[i] >= threshold]

    def search_dense(self, query: str, top_k: int = 5, threshold: float = 0.76) -> list[tuple[KnowledgeChunk, float]]:
        if self.chunk_vectors is None or not self.chunks:
            return []
        try:
            q_vec = self.dense_retriever.encode_queries([query])[0]
            sims = np.dot(self.chunk_vectors, q_vec)
            top_indices = np.argsort(sims)[::-1][:top_k]
            return [(self.chunks[i], float(sims[i])) for i in top_indices if sims[i] >= threshold]
        except Exception:
            return []

    def search(
        self,
        query: str,
        lang: str = "en",
        mode: str = "hybrid",
        top_k: int = 3,
        threshold: float = 0.002,
    ) -> list[tuple[KnowledgeChunk, float]]:
        """Search corpus with bm25, dense, or hybrid reciprocal rank fusion."""
        if not self.chunks:
            return []

        if mode == "bm25":
            return self.search_bm25(query, top_k=top_k, threshold=2.0)
        elif mode == "dense":
            return self.search_dense(query, top_k=top_k, threshold=0.76)

        # Hybrid search with Reciprocal Rank Fusion (RRF)
        # Compute BM25 scores
        q_tokens = _tokenize(query)
        bm_scores = self.bm25.get_scores(q_tokens) if (self.bm25 and q_tokens) else np.zeros(len(self.chunks))

        # Compute Dense similarities
        if self.chunk_vectors is not None:
            try:
                q_vec = self.dense_retriever.encode_queries([query])[0]
                dense_sims = np.dot(self.chunk_vectors, q_vec)
            except Exception:
                dense_sims = np.zeros(len(self.chunks))
        else:
            dense_sims = np.zeros(len(self.chunks))

        # RRF combination
        k_rrf = 60
        bm_ranks = np.argsort(bm_scores)[::-1]
        dense_ranks = np.argsort(dense_sims)[::-1]

        max_bm = float(np.max(bm_scores)) if len(bm_scores) > 0 else 0.0
        max_dense = float(np.max(dense_sims)) if len(dense_sims) > 0 else 0.0

        # Reject out-of-domain queries that lack both keyword relevance and strong semantic match
        if max_bm < 1.0 and max_dense < 0.81:
            return []

        rrf_scores: dict[str, float] = {c.chunk_id: 0.0 for c in self.chunks}

        for rank, idx in enumerate(bm_ranks):
            if bm_scores[idx] > 1.0:
                rrf_scores[self.chunks[idx].chunk_id] += 0.3 * (1.0 / (k_rrf + rank + 1))

        for rank, idx in enumerate(dense_ranks):
            if dense_sims[idx] >= 0.76:
                rrf_scores[self.chunks[idx].chunk_id] += 0.7 * (1.0 / (k_rrf + rank + 1))

        chunk_lookup = {c.chunk_id: c for c in self.chunks}
        sorted_chunks = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        results: list[tuple[KnowledgeChunk, float]] = []
        for cid, score in sorted_chunks[:top_k]:
            if score >= threshold:
                results.append((chunk_lookup[cid], score))

        return results

    def search_as_evidence(
        self,
        query: str,
        lang: str = "en",
        mode: str = "hybrid",
        top_k: int = 3,
        threshold: float = 0.002,
    ) -> list[dict[str, Any]]:
        """Search and format results as dictionary representations of EvidencePacket."""
        import datetime as dt
        import uuid

        matches = self.search(query=query, lang=lang, mode=mode, top_k=top_k, threshold=threshold)
        now = dt.datetime.now(dt.timezone.utc)

        # Check if top score meets the threshold
        if not matches:
            no_guidance_map = {
                "hi": (
                    "इस विषय पर कोई आधिकारिक दिशानिर्देश उपलब्ध नहीं है। आपातकालीन स्थिति में 112 (आपातकाल), "
                    "1077 (आपदा प्रबंधन) या किसान कॉल सेंटर 1800-180-1551 पर संपर्क करें।"
                ),
                "bn": (
                    "এই বিষয়ে কোনো সরকারি নির্দেশিকা পাওয়া যায়নি। জরুরি সহায়তার জন্য ১১২ (জরুরি সেবা), "
                    "১০৭৭ (দুর্যোগ ব্যবস্থাপনা) বা ১৮০০-১৮০-১৫৫১ (কিষাণ কল সেন্টার) নম্বরে যোগাযোগ করুন।"
                ),
                "mr": (
                    "या विषयावर कोणतीही अधिकृत मार्गदर्शक तत्त्वे उपलब्ध नाहीत. मदतीसाठी ११२ (आपत्कालीन), "
                    "१०७७ (आपत्ती व्यवस्थापन) किंवा १८০০-१८०-१५५१ (किसान कॉल सेंटर) वर संपर्क साधा."
                ),
                "te": (
                    "ఈ అంశంపై అధికారిక మార్గదర్శకాలు అందుబాటులో లేవు. సహాయం కోసం 112 (ఎమర్జెన్సీ), "
                    "1077 (విపత్తు నిర్వహణ) లేదా 1800-180-1551 (కిసాన్ కాల్ సెంటర్) ను సంప్రదించండి."
                ),
                "ta": (
                    "இந்த விஷயத்தில் அதிகாரப்பூர்வ வழிகாட்டுதல்கள் எதுவும் கிடைக்கவில்லை. உதவிக்கு 112 (அவசர சேவை), "
                    "1077 (பேரிடர் மேலாண்மை) அல்லது 1800-180-1551 (கிசான் கால் சென்டர்) ஐத் தொடர்பு கொள்ளவும்."
                ),
                "or": (
                    "ଏହି ବିଷୟରେ କୌଣସି ସରକାରୀ ନିର୍ଦ୍ଦେଶାବଳୀ ଉପଲବ୍ଧ ନାହିଁ। ସହାୟତା ପାଇଁ ୧୧୨ (ଜରୁରୀକାଳୀନ), "
                    "୧୦୭୭ (ବିପର୍ଯ୍ୟୟ ପରିଚାଳନା) କିମ୍ବା ୧୮୦୦-୧୮୦-୧୫୫୧ (କିଷାନ କଲ୍ ସେଣ୍ଟର) ରେ ଯୋଗାଯୋଗ କରନ୍ତୁ।"
                ),
            }
            no_guidance_text = no_guidance_map.get(
                lang,
                (
                    "I don't have official guidance on that. For assistance dial 112 (National Emergency), "
                    "1077 (Disaster Management) or 1800-180-1551 (Kisan Call Centre)."
                ),
            )
            return [
                {
                    "id": f"kb_fallback_{uuid.uuid4().hex[:8]}",
                    "source": "WeatherGPT Advisory Guidance",
                    "authority_tier": 4,
                    "provenance": "live",
                    "issued_at": now,
                    "valid_from": now,
                    "valid_to": now + dt.timedelta(days=7),
                    "place": {"id": "all_india", "name": "India", "lat": 20.5937, "lon": 78.9629},
                    "values": [
                        {"variable": "chunk_id", "value": "no_official_guidance", "unit": "id"},
                        {"variable": "guidance", "value": no_guidance_text, "unit": "text"},
                        {"variable": "helplines", "value": "112, 1077, 1800-180-1551", "unit": "text"},
                    ],
                    "attribution": "NDMA / IMD Public Safety Guidance",
                    "fetched_at": now,
                }
            ]

        packets: list[dict[str, Any]] = []
        for chunk, score in matches:
            pkt = {
                "id": f"kb_{chunk.chunk_id}",
                "source": chunk.source,
                "authority_tier": 4,
                "provenance": "live",
                "issued_at": now,
                "valid_from": now,
                "valid_to": now + dt.timedelta(days=7),
                "place": {"id": "all_india", "name": "India", "lat": 20.5937, "lon": 78.9629},
                "values": [
                    {"variable": "chunk_id", "value": chunk.chunk_id, "unit": "id"},
                    {"variable": "title", "value": chunk.title, "unit": "text"},
                    {"variable": "hazard", "value": chunk.hazard, "unit": "text"},
                    {"variable": "guidance", "value": chunk.text, "unit": "text"},
                    {"variable": "score", "value": round(float(score), 4), "unit": "score"},
                ],
                "attribution": f"{chunk.source} ({chunk.license})",
                "fetched_at": now,
            }
            packets.append(pkt)

        return packets
