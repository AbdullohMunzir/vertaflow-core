"""
VertaFlow Production RAG Engine
Designed and engineered according to agency-rag-pipeline-engineer specifications.

Features:
- Dense Vector Retrieval using Google Gemini gemini-embedding-001 (768-dim)
- Sparse BM25 Retrieval (Okapi BM25) with Uzbek language tokenization & stemming
- Reciprocal Rank Fusion (RRF) combining dense and sparse search (alpha=0.65)
- Document Chunking & Indexing with rich metadata
- Formatted context assembly with exact source citations
- Graceful offline fallback if API is unavailable
"""

import math
import json
import re
import requests
from typing import List, Dict, Any, Optional, Tuple

import os
import db
from core.verta_chunker import VertaChunker
from core.verta_gemini import DEFAULT_GEMINI_KEY

UZBEK_STOPWORDS = {
    "va", "ham", "esa", "bilan", "uchun", "haqida", "qanday", "nima",
    "qachon", "qayerda", "qayerga", "kim", "qaysi", "bormi", "yoqmi",
    "kerak", "mumkin", "iltimos", "assalomu", "alaykum", "salom",
    "rahmat", "aka", "uka", "biz", "siz", "ular", "men", "sizlar",
    "sen", "shu", "bu", "o'zi", "bo'yicha", "bormikin", "qanaqa"
}

class BM25Retriever:
    """Okapi BM25 implementation optimized for Uzbek e-commerce and sales corpora."""
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus: List[Dict[str, Any]] = []
        self.doc_lengths: List[int] = []
        self.avg_dl: float = 0.0
        self.df: Dict[str, int] = {}  # Document frequency of terms
        self.idf: Dict[str, float] = {}

    def fit(self, chunks: List[Dict[str, Any]]):
        """Indexes chunks for BM25 search."""
        self.corpus = chunks
        if not chunks:
            self.doc_lengths = []
            self.avg_dl = 0.0
            self.df = {}
            self.idf = {}
            return

        total_length = 0
        self.doc_lengths = []
        self.df = {}
        N = len(chunks)

        for doc in chunks:
            tokens = self._tokenize(doc["content"])
            total_length += len(tokens)
            self.doc_lengths.append(len(tokens))
            unique_tokens = set(tokens)
            for t in unique_tokens:
                self.df[t] = self.df.get(t, 0) + 1

        self.avg_dl = total_length / N if N > 0 else 1.0

        # Calculate Okapi IDF
        self.idf = {}
        for term, freq in self.df.items():
            self.idf[term] = math.log((N - freq + 0.5) / (freq + 0.5) + 1.0)

    def score(self, query: str) -> List[Tuple[Dict[str, Any], float]]:
        """Calculates BM25 score for each document against the query."""
        if not self.corpus:
            return []

        q_tokens = self._tokenize(query)
        if not q_tokens:
            return []

        scores = []
        for idx, doc in enumerate(self.corpus):
            doc_tokens = self._tokenize(doc["content"])
            doc_len = self.doc_lengths[idx]
            
            # Frequency map
            freq_map: Dict[str, int] = {}
            for t in doc_tokens:
                freq_map[t] = freq_map.get(t, 0) + 1

            doc_score = 0.0
            for qt in q_tokens:
                if qt not in self.idf:
                    continue
                tf = freq_map.get(qt, 0)
                if tf > 0:
                    numerator = tf * (self.k1 + 1.0)
                    denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / (self.avg_dl or 1.0)))
                    doc_score += self.idf[qt] * (numerator / denominator)

            scores.append((doc, doc_score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

    def _tokenize(self, text: str) -> List[str]:
        """Normalizes and tokenizes Uzbek text, removing stopwords and stemming suffixes."""
        # Convert to lowercase and normalize apostrophes
        text = text.lower().replace("‘", "'").replace("’", "'").replace("`", "'")
        # Remove punctuation except letters, digits, and apostrophes
        words = re.findall(r"[a-zа-яё0-9_']+", text)
        
        # Strip common Uzbek grammatical suffixes for better matching
        suffixes = ["ning", "dagi", "lar", "dan", "ga", "da", "ni", "mi", "chi", "ku"]
        cleaned = []
        for w in words:
            if len(w) <= 2 or w in UZBEK_STOPWORDS:
                continue
            stem = w
            for suf in suffixes:
                if stem.endswith(suf) and len(stem) > len(suf) + 2:
                    stem = stem[:-len(suf)]
                    break
            if stem not in UZBEK_STOPWORDS:
                cleaned.append(stem)
        return cleaned


class VertaRAG:
    """
    Production Hybrid RAG Engine
    Combines dense Gemini embeddings + sparse BM25 with Reciprocal Rank Fusion (RRF).
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or db.get_setting("gemini_api_key") or os.environ.get("GEMINI_API_KEY") or DEFAULT_GEMINI_KEY
        self.chunker = VertaChunker(chunk_size=500, chunk_overlap=80)
        self.bm25 = BM25Retriever()
        self._cached_chunks: List[Dict[str, Any]] = []
        self.refresh_cache()

    def refresh_cache(self):
        """Reloads all chunks from DB and fits the BM25 index."""
        self._cached_chunks = db.get_all_chunks()
        self.bm25.fit(self._cached_chunks)

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generates 768-dim embedding via Gemini gemini-embedding-001."""
        if not self.api_key:
            self.api_key = db.get_setting("gemini_api_key")
        if not self.api_key:
            return None

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key={self.api_key}"
        payload = {
            "content": {
                "parts": [{"text": text[:2000]}]  # Stay safely within limit
            }
        }
        try:
            resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("embedding", {}).get("values")
        except Exception:
            pass
        return None

    def generate_batch_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generates batch embeddings via batchEmbedContents."""
        if not self.api_key:
            self.api_key = db.get_setting("gemini_api_key")
        if not self.api_key or not texts:
            return [None] * len(texts)

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:batchEmbedContents?key={self.api_key}"
        requests_list = [
            {
                "model": "models/gemini-embedding-001",
                "content": {"parts": [{"text": t[:2000]}]}
            }
            for t in texts
        ]
        payload = {"requests": requests_list}
        try:
            resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                embs = data.get("embeddings", [])
                return [e.get("values") if e else None for e in embs]
        except Exception:
            pass

        # Fallback to single requests if batch fails
        return [self.generate_embedding(t) for t in texts]

    def index_document(self, parent_id: int, title: str, item_type: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Splits a document, embeds all chunks in batch, and stores them in DB."""
        chunks = self.chunker.chunk_document(text=content, title=title, item_type=item_type, metadata=metadata)
        if not chunks:
            return

        texts = [c["content"] for c in chunks]
        embeddings = self.generate_batch_embeddings(texts)

        db_chunks = []
        for c, emb in zip(chunks, embeddings):
            db_chunks.append({
                "parent_id": parent_id,
                "chunk_index": c["chunk_index"],
                "content": c["content"],
                "embedding": emb,
                "metadata": c["metadata"]
            })

        # Remove old chunks for this parent_id to avoid duplication
        db.delete_chunks_for_item(parent_id)
        db.add_chunks_batch(db_chunks)
        self.refresh_cache()

    def sync_all_knowledge(self):
        """Audits all knowledge_items and re-indexes any unindexed documents."""
        items = db.list_knowledge_items()
        indexed_parent_ids = {c["parent_id"] for c in self._cached_chunks}

        for item in items:
            if item["id"] not in indexed_parent_ids:
                meta = item.get("metadata") or {}
                self.index_document(
                    parent_id=item["id"],
                    title=item["title"],
                    item_type=item["item_type"],
                    content=item["content"],
                    metadata=meta
                )
        self.refresh_cache()

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        alpha: float = 0.65,
        threshold: float = 0.01
    ) -> List[Dict[str, Any]]:
        """
        Hybrid Search: Dense (Cosine) + Sparse (BM25) with Reciprocal Rank Fusion (RRF).
        alpha: Weight for dense search (0.65 favors semantic relevance while respecting keyword matches).
        """
        if not self._cached_chunks:
            self.refresh_cache()
            if not self._cached_chunks:
                # If still empty, attempt auto-sync
                self.sync_all_knowledge()

        if not self._cached_chunks:
            return []

        # 1. Sparse BM25 Search
        bm25_results = self.bm25.score(query)
        sparse_ranks: Dict[int, int] = {}
        for rank, (doc, score) in enumerate(bm25_results):
            if score > 0:
                sparse_ranks[doc["id"]] = rank + 1

        # 2. Dense Semantic Search
        q_emb = self.generate_embedding(query)
        dense_scores = []
        if q_emb:
            for doc in self._cached_chunks:
                d_emb = doc.get("embedding")
                if d_emb and len(d_emb) == len(q_emb):
                    sim = self._cosine_similarity(q_emb, d_emb)
                    dense_scores.append((doc, sim))
                else:
                    dense_scores.append((doc, 0.0))
        else:
            # If embedding unavailable, dense rank is neutral
            for doc in self._cached_chunks:
                dense_scores.append((doc, 0.0))

        dense_scores.sort(key=lambda x: x[1], reverse=True)
        dense_ranks: Dict[int, int] = {
            doc["id"]: rank + 1
            for rank, (doc, sim) in enumerate(dense_scores)
            if sim > 0.1
        }

        # 3. Reciprocal Rank Fusion (RRF)
        # RRF formula: alpha * (1 / (60 + dense_rank)) + (1 - alpha) * (1 / (60 + sparse_rank))
        fused_scores: List[Tuple[Dict[str, Any], float, float, float]] = []
        for doc in self._cached_chunks:
            doc_id = doc["id"]
            d_rank = dense_ranks.get(doc_id, 9999)
            s_rank = sparse_ranks.get(doc_id, 9999)

            d_rrf = (1.0 / (60.0 + d_rank)) if d_rank < 9999 else 0.0
            s_rrf = (1.0 / (60.0 + s_rank)) if s_rank < 9999 else 0.0
            total_rrf = (alpha * d_rrf) + ((1.0 - alpha) * s_rrf)

            # Get raw dense similarity if available
            raw_sim = 0.0
            if q_emb and doc.get("embedding"):
                raw_sim = self._cosine_similarity(q_emb, doc["embedding"])

            if total_rrf > threshold or raw_sim > 0.40:
                fused_scores.append((doc, total_rrf, raw_sim, s_rrf))

        fused_scores.sort(key=lambda x: x[1], reverse=True)
        top_candidates = fused_scores[:top_k]

        qualified_results = []
        for item in top_candidates:
            doc = item[0]
            total_rrf = item[1]
            raw_sim = item[2]
            s_rrf = item[3]

            # Relevance Gate: Must have semantic relevance >= 0.70 OR (BM25 keyword match with semantic >= 0.65)
            is_relevant = False
            if q_emb:
                if raw_sim >= 0.70 or (s_rrf > 0 and raw_sim >= 0.65):
                    is_relevant = True
            else:
                # Fallback when embeddings are unavailable: rely on positive BM25
                if s_rrf > 0:
                    is_relevant = True

            if is_relevant:
                qualified_results.append({
                    "id": doc["id"],
                    "content": doc["content"],
                    "metadata": doc["metadata"],
                    "rrf_score": total_rrf,
                    "cosine_sim": raw_sim
                })

        # Dynamic Pruning: Only keep supplementary chunks if their score is within 0.07 of the top chunk
        if qualified_results:
            top_sim = qualified_results[0]["cosine_sim"]
            pruned = [qualified_results[0]]
            for extra in qualified_results[1:]:
                if (top_sim - extra["cosine_sim"]) <= 0.07 or extra["cosine_sim"] >= 0.78:
                    pruned.append(extra)
            qualified_results = pruned

        return qualified_results

    def assemble_context(self, query: str, top_k: int = 3) -> str:
        """
        Assembles formatted context string from retrieved chunks with exact citations.
        If no relevant chunks are found, returns empty string so the LLM remains grounded.
        """
        results = self.retrieve(query=query, top_k=top_k)
        if not results:
            return ""

        blocks = ["### TEGISHLI RASMIY KORXONA MA'LUMOTLARI (ANIQ MANBALAR):"]
        for idx, res in enumerate(results, 1):
            meta = res.get("metadata") or {}
            source_title = meta.get("source_title") or meta.get("section") or "Rasmiy hujjat"
            category = meta.get("category") or meta.get("item_type", "").upper()
            tag = f"{source_title} ({category})" if category else source_title
            blocks.append(f"[{idx}] [Manba: {tag}]\n{res['content']}")

        return "\n\n".join(blocks)

    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """Calculates cosine similarity between two float vectors."""
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)


# Global singleton instance for VertaRAG
_rag_instance: Optional[VertaRAG] = None

def get_rag_engine() -> VertaRAG:
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = VertaRAG()
    return _rag_instance
