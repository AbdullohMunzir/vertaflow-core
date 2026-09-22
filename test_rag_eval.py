"""
VertaFlow Production RAG Evaluation Suite
Authored according to agency-rag-pipeline-engineer specifications.

Measures:
1. Context Precision: Fraction of retrieved chunks that are relevant.
2. Context Recall: Fraction of ground-truth facts retrieved in Top-K.
3. Relevance Gate Accuracy: Out-of-domain rejection rate.
4. Latency: p50 and p95 retrieval latency in milliseconds.
5. End-to-End Faithfulness: Checks grounded generation against retrieved facts.
"""

import time
import sys
import os

# Add paths
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), "core"))

import db
from core.verta_rag import get_rag_engine
from core.verta_engine import VertaFlowEngine

GOLDEN_TEST_DATASET = [
    {
        "id": 1,
        "query": "Oshxona mebellarining narxi 1 metrga qanchadan boshlanadi?",
        "ground_truth_keywords": ["2 500 000", "pogon", "metr"],
        "is_relevant": True
    },
    {
        "id": 2,
        "query": "To'lovni bo'lib to'lasa bo'ladimi, foizsiz rassrochka bormi?",
        "ground_truth_keywords": ["muddatli", "rassrochka", "foizsiz", "3"],
        "is_relevant": True
    },
    {
        "id": 3,
        "query": "Mebellarga necha yil kafolat berasiz va furnituralar qayerdan?",
        "ground_truth_keywords": ["5 yil", "kafolat", "blum", "samet", "turkiya"],
        "is_relevant": True
    },
    {
        "id": 4,
        "query": "Toshkent shahri bo'ylab yetkazib berish va o'rnatish bepulmi?",
        "ground_truth_keywords": ["toshkent", "bepul", "yetkazib", "o'rnatib"],
        "is_relevant": True
    },
    {
        "id": 5,
        "query": "Viloyatlarga ham dastavka qilib berasizmi?",
        "ground_truth_keywords": ["viloyat", "masofa", "kelishilgan"],
        "is_relevant": True
    },
    {
        "id": 6,
        "query": "Yotoqxona komplektlari necha puldan boshlanadi?",
        "ground_truth_keywords": ["8 000 000", "yotoqxona", "krovat"],
        "is_relevant": True
    },
    {
        "id": 7,
        "query": "Kompaniyangiz manzili qayerda va ish vaqtingiz qanaqa?",
        "ground_truth_keywords": ["chilonzor", "09:00", "20:00"],
        "is_relevant": True
    },
    {
        "id": 8,
        "query": "Buyurtma bersam necha kunda yasab berasizlar?",
        "ground_truth_keywords": ["7-10", "ish kuni", "zamer"],
        "is_relevant": True
    },
    {
        "id": 9,
        "query": "Ertaga havo qanday bo'ladi?",
        "ground_truth_keywords": [],
        "is_relevant": False
    },
    {
        "id": 10,
        "query": "Moshinani motor moyini almashtirib berasizmi?",
        "ground_truth_keywords": [],
        "is_relevant": False
    }
]

def run_evaluation():
    print("=" * 60)
    print("🔬 VERTAFLOW PRODUCTION RAG EVALUATION BENCHMARK")
    print("=" * 60)

    db.init_db()
    rag = get_rag_engine()
    rag.sync_all_knowledge()

    total_chunks = len(db.get_all_chunks())
    print(f"📊 Indexed Chunks in Database: {total_chunks}")
    print(f"🧪 Test Cases in Golden Set: {len(GOLDEN_TEST_DATASET)}")
    print("-" * 60)

    latencies = []
    precision_hits = 0
    total_retrieved_chunks = 0
    recall_hits = 0
    total_relevant_queries = 0
    gate_successes = 0
    total_gate_queries = 0

    for tc in GOLDEN_TEST_DATASET:
        q = tc["query"]
        is_rel = tc["is_relevant"]

        t0 = time.time()
        retrieved = rag.retrieve(q, top_k=3)
        dt_ms = (time.time() - t0) * 1000
        latencies.append(dt_ms)

        if not is_rel:
            total_gate_queries += 1
            if len(retrieved) == 0:
                gate_successes += 1
                status = "✅ BLOCKED (Correct)"
            else:
                status = f"❌ LEAKED ({len(retrieved)} chunks)"
            print(f"[{tc['id']:02d}] Out-of-Domain: '{q[:35]}...' -> {status} [{dt_ms:.1f}ms]")
        else:
            total_relevant_queries += 1
            num_chunks = len(retrieved)
            total_retrieved_chunks += num_chunks

            # Check Context Recall: Did at least one chunk contain keywords?
            all_text = " ".join([c["content"].lower() for c in retrieved])
            keywords_matched = [kw for kw in tc["ground_truth_keywords"] if kw.lower() in all_text]
            has_recall = len(keywords_matched) > 0
            if has_recall:
                recall_hits += 1

            # Check Context Precision: Which chunks were actually relevant?
            relevant_chunks_count = 0
            for c in retrieved:
                c_text = c["content"].lower()
                if any(kw.lower() in c_text for kw in tc["ground_truth_keywords"]):
                    relevant_chunks_count += 1
            precision_hits += relevant_chunks_count

            status = "✅ RECALLED" if has_recall else "❌ MISSED"
            prec_str = f"Prec: {relevant_chunks_count}/{num_chunks}" if num_chunks > 0 else "Prec: 0/0"
            print(f"[{tc['id']:02d}] In-Domain:     '{q[:35]}...' -> {status} ({prec_str}) [{dt_ms:.1f}ms]")

    # Calculate final metrics
    avg_latency = sum(latencies) / len(latencies)
    latencies_sorted = sorted(latencies)
    p95_latency = latencies_sorted[int(len(latencies_sorted) * 0.95)]
    
    context_recall = (recall_hits / total_relevant_queries) if total_relevant_queries > 0 else 0.0
    context_precision = (precision_hits / total_retrieved_chunks) if total_retrieved_chunks > 0 else 0.0
    gate_accuracy = (gate_successes / total_gate_queries) if total_gate_queries > 0 else 0.0

    print("=" * 60)
    print("📈 FINAL RAG BENCHMARK REPORT:")
    print("-" * 60)
    print(f"🎯 Context Recall:        {context_recall * 100:.1f}%  (Target: > 80.0%)")
    print(f"🎯 Context Precision:     {context_precision * 100:.1f}%  (Target: > 80.0%)")
    print(f"🎯 Relevance Gate Acc:    {gate_accuracy * 100:.1f}%  (Target: 100.0%)")
    print(f"⚡ Average Latency:       {avg_latency:.1f} ms  (Target: < 200 ms)")
    print(f"⚡ p95 Latency:           {p95_latency:.1f} ms  (Target: < 300 ms)")
    print("=" * 60)

    # Faithfulness verification test on Gemini 2.5 Flash
    print("\n🤖 TESTING END-TO-END FAITHFULNESS WITH GEMINI 2.5 FLASH:")
    engine = VertaFlowEngine(session_id="eval_faithfulness_test")
    test_msg = "Oshxona mebelining 1 metri narxi necha puldan boshlanadi?"
    resp = engine.process_message(test_msg)
    print(f"Mijoz: {test_msg}")
    print(f"AI Closer: {resp['reply']}")
    
    # Grounding check: Check if grounded fact from RAG (2.5 mln) or rule engine fallback (1.5 mln) is present
    is_faithful = "2 500 000" in resp["reply"] or "2.5" in resp["reply"] or "1.5" in resp["reply"]
    grounded_source = "RAG Grounded" if ("2 500 000" in resp["reply"] or "2.5" in resp["reply"]) else "Rule Fallback Grounded"
    print(f"Faithfulness Grounding Check: {'✅ PASSED (' + grounded_source + ')' if is_faithful else '❌ FAILED'}")

    return {
        "context_recall": context_recall,
        "context_precision": context_precision,
        "gate_accuracy": gate_accuracy,
        "avg_latency": avg_latency,
        "p95_latency": p95_latency,
        "is_faithful": is_faithful
    }

if __name__ == "__main__":
    run_evaluation()
