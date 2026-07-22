"""
Pipeline entry point — script equivalent of 00_pipeline.ipynb.

Stages
------
1. Ingest   — download FAQ data and build a keyword index  (ingest.py)
2. Embed    — encode all documents with all-MiniLM-L6-v2
3. Index    — build a minsearch VectorSearch index (in-memory)
4. Search   — vector-search the index for a query
5. RAG      — run full retrieval-augmented generation (requires .env with an LLM key)

Usage
-----
# Stage 1-4: just vector search, no LLM required
uv run python main.py --query "Can I still join after the start date?"

# Stage 1-5: full RAG answer (needs OLLAMA_API_KEY or OPENAI_API_KEY in .env)
uv run python main.py --query "Can I still join after the start date?" --rag

# Filter results to one course
uv run python main.py --query "How do I install Docker?" --course mlops-zoomcamp

# Show more results
uv run python main.py --query "How do I install Docker?" --top-k 10
"""

import argparse
import os

import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from tqdm.auto import tqdm

from ingest import build_index, load_faq_data
from rag_helper import RAGBase


# ── Stage 3: vector subclass of RAGBase ──────────────────────────────────────

class RAGVector(RAGBase):
    """RAGBase that searches with a minsearch VectorSearch index."""

    def __init__(self, embedder, **kwargs):
        super().__init__(**kwargs)
        self.embedder = embedder

    def search(self, query, num_results=5):
        query_vector = self.embedder.encode(query)
        return self.index.search(
            query_vector,
            filter_dict={"course": self.course},
            num_results=num_results,
        )


# ── Stage helpers ─────────────────────────────────────────────────────────────

def stage_ingest():
    print("Stage 1 — Ingesting FAQ data...")
    documents = load_faq_data()
    index = build_index(documents)
    print(f"  Loaded {len(documents)} documents")
    return documents, index


def stage_embed(documents):
    print("Stage 2 — Encoding documents...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    texts = [doc["question"] + "    " + doc["answer"] for doc in documents]

    batch_size = 50
    vectors = []
    for i in tqdm(range(0, len(texts), batch_size), desc="  Batches"):
        vectors.extend(model.encode(texts[i: i + batch_size]))

    X = np.array(vectors)
    print(f"  Embedding matrix: {X.shape}")
    return model, vectors, X


def stage_vector_index(model, X, documents):
    print("Stage 3 — Building minsearch VectorSearch index...")
    from minsearch import VectorSearch
    vindex = VectorSearch(keyword_fields=["course"])
    vindex.fit(X, documents)
    print("  Done")
    return vindex


def stage_search(model, vindex, query, course, top_k):
    print(f"\nStage 4 — Vector search  (course={course!r}, top_k={top_k})")
    q_vec = model.encode(query)
    filter_dict = {"course": course} if course else {}
    results = vindex.search(q_vec, filter_dict=filter_dict, num_results=top_k)

    print(f"\n  Query: {query}\n")
    for i, r in enumerate(results, 1):
        print(f"  [{i}] [{r['course']}] {r['question']}")
        print(f"       {r['answer'][:120].strip()}...")
        print()
    return results


def stage_rag(model, vindex, query, course):
    print("Stage 5 — RAG answer")
    load_dotenv()

    llm_client = _build_llm_client()
    if llm_client is None:
        print("  No LLM client configured. Add OLLAMA_API_KEY or OPENAI_API_KEY to .env")
        return

    assistant = RAGVector(
        embedder=model,
        index=vindex,
        llm_client=llm_client,
        course=course or "llm-zoomcamp",
    )

    print(f"\n  Query: {query}\n")
    print("  Answer:\n")
    assistant.rag(query)
    print()


def _build_llm_client():
    """Return an Ollama or OpenAI-compatible client, or None if unconfigured."""
    ollama_key = os.environ.get("OLLAMA_API_KEY")
    if ollama_key:
        from ollama import Client
        return Client(
            host="https://ollama.com",
            headers={"Authorization": f"Bearer {ollama_key}"},
        )

    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        from openai import OpenAI
        return OpenAI(api_key=openai_key)

    return None


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="FAQ vector search pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--query", "-q",
        default="Can I still join the course after the start date?",
        help="Search query (default: a join-late question)",
    )
    parser.add_argument(
        "--course", "-c",
        default="",
        help="Filter results to one course slug, e.g. llm-zoomcamp",
    )
    parser.add_argument(
        "--top-k", "-k",
        type=int,
        default=5,
        help="Number of results to return (default: 5)",
    )
    parser.add_argument(
        "--rag",
        action="store_true",
        help="Run Stage 5: generate an LLM answer (requires a key in .env)",
    )
    args = parser.parse_args()

    documents, _kw_index = stage_ingest()
    model, vectors, X = stage_embed(documents)
    vindex = stage_vector_index(model, X, documents)
    stage_search(model, vindex, args.query, args.course, args.top_k)

    if args.rag:
        stage_rag(model, vindex, args.query, args.course)


if __name__ == "__main__":
    main()
