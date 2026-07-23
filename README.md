## FAQ Vector Search Playground

This repo explores vector search and RAG (Retrieval-Augmented Generation) over the
DataTalks.Club course FAQ data. It covers multiple vector-search backends — from a
pure in-memory NumPy approach all the way to persistent SQLite and PostgreSQL — and
wraps them all in a reusable RAG pipeline. A separate orchestration layer shows the
same patterns implemented as Kestra workflows.

---

## Start here

**[`00_pipeline.ipynb`](00_pipeline.ipynb)** is the master notebook. It runs the full
pipeline from end to end, explains how every file fits together, and produces the
shared objects (`model`, `documents`, `vectors`, `X`) that the focused notebooks depend
on. Open it first.

---

## Sequential file map

| # | File / folder | Purpose |
|---|---------------|---------|
| 0 | `pyproject.toml` / `.python-version` | Project metadata and locked Python version |
| 1 | `ingest.py` | Download FAQ data; build minsearch keyword index |
| 2 | `embeddings.ipynb` | **Core exploration**: model loading, dot-product similarity, batch encoding, NumPy top-k, minsearch VectorSearch, SQLite VectorSearchIndex, RAG demos |
| 3 | `minsearch-vector.ipynb` | Focused look at `minsearch.VectorSearch` — needs `X` and `documents` from Stage 2 |
| 4 | `rag_helper.py` | `RAGBase` class: search → context → prompt → LLM stream |
| 5 | `rag-vector.ipynb` | RAG pipeline wired to a `VectorSearch` index — needs `X` and `documents` from Stage 2 |
| 6 | `sqlitesearch-vector.ipynb` | Open the persisted `faq_vectors2.db` and run SQLite-backed RAG |
| 7 | `pgvector-vector.ipynb` | PostgreSQL + pgvector backend; HNSW index; pgvector RAG |
| 8 | `main.py` | Minimal CLI entry-point placeholder |
| 9 | `orchestration/` | Kestra workflow orchestration: docker-compose, 11 YAML flows, 12 lesson notes |

### Dependency graph

```
ingest.py
    └── documents, index
            │
            ▼
    embeddings.ipynb  ──────────────────────────────────────────┐
    (model, vectors, X)                                         │
            │                                                   │
     ┌──────┴──────────────────────┐                           │
     ▼                             ▼                           │
minsearch-vector.ipynb    sqlitesearch-vector.ipynb            │
  (needs X, documents)      (needs faq_vectors2.db)            │
     │                                                         │
     ▼                                                         │
rag_helper.py  ◄───────────────────────────────────────────────┘
(RAGBase)                    pgvector-vector.ipynb
     │                         (standalone, needs Postgres)
     ▼
rag-vector.ipynb
  (needs X, documents)
```

The `orchestration/` folder is independent — it uses Kestra to orchestrate similar
RAG and agent patterns via YAML flows rather than Python notebooks.

---

## What each file does

### `ingest.py`
Fetches the DataTalks.Club FAQ catalog, follows each course path, and returns a flat
list of documents with `question`, `answer`, `section`, and `course` fields. Also
exposes `build_index(documents)` for a lightweight minsearch keyword index.

### `embeddings.ipynb`
The main exploration notebook. Covers:
1. Loading `all-MiniLM-L6-v2` from `sentence-transformers`
2. Encoding individual texts and computing dot-product similarity
3. Batch encoding all FAQs → NumPy array `X`
4. Manual top-k retrieval with `np.argsort`
5. `minsearch.VectorSearch` with keyword filtering
6. `sqlitesearch.VectorSearchIndex` (writes `faq_vectors2.db`)
7. `RAGVector` subclass wired to Ollama

### `minsearch-vector.ipynb`
Short focused demo of `minsearch.VectorSearch`. Expects `X` and `documents` to
already be defined — run `00_pipeline.ipynb` or `embeddings.ipynb` first.

### `rag_helper.py`
Defines `RAGBase`: a reusable RAG class that any vector backend can extend by
overriding `search()`. All other notebooks import from here.

### `rag-vector.ipynb`
Subclasses `RAGBase` to use the minsearch `VectorSearch` index. Requires `X` and
`documents` from Stage 2, plus an LLM client configured via `.env`.

### `sqlitesearch-vector.ipynb`
Opens the persisted `faq_vectors2.db` (built in `embeddings.ipynb`) and runs
SQLite-backed vector search RAG with Ollama.

### `pgvector-vector.ipynb`
Standalone notebook for the PostgreSQL backend. Re-encodes all FAQs, stores them in
a `documents` table with an `embedding vector(384)` column, creates an HNSW cosine
index, and defines `RAGPgVector`. Requires a running Postgres instance with the
`pgvector` extension.

### `main.py`
The `.py` equivalent of `00_pipeline.ipynb`. Runs the same five stages — ingest,
embed, vector index, search, and optional RAG — as a command-line script:

```bash
# Vector search (no LLM needed)
uv run python main.py --query "Can I still join after the start date?"

# Full RAG answer (needs OLLAMA_API_KEY or OPENAI_API_KEY in .env)
uv run python main.py --query "Can I still join after the start date?" --rag

# Filter to one course, show 10 results
uv run python main.py --query "How do I install Docker?" --course mlops-zoomcamp --top-k 10
```

### `orchestration/`
Kestra-based orchestration layer:
- `docker-compose.yml` — starts Kestra + Postgres (UI at `http://localhost:8080`)
- `flows/1_chat_without_rag.yaml` — baseline LLM query with no context
- `flows/2_chat_with_rag.yaml` — RAG via Gemini embedding store
- `flows/3_rag_with_websearch.yaml` — RAG via live Tavily web search
- `flows/4_simple_agent.yaml` — parameterised summarisation agent with token tracking
- `flows/5_web_research_agent.yaml` — agent with web-search tool
- `flows/6_multi_agent_research.yaml` — multi-agent collaboration
- `flows/7_conversational_agent_with_memory.yaml` — persistent memory across executions
- `flows/8_faq_rag_pipeline.yaml` — domain RAG over DataTalks.Club course docs
- `flows/9_llm_evaluation.yaml` — LLM-as-judge evaluation (RAG vs. no-RAG scoring)
- `flows/10_scheduled_knowledge_refresh.yaml` — weekly scheduled ingest + smoke test
- `flows/11_rag_with_groq.yaml` — same RAG pipeline via Gemini and Groq side-by-side
- `lessons/` — twelve markdown notes (`01-intro.md` … `12-advanced-patterns.md`)

#### Flow instruction docs (YAML → Markdown)
- `flows/1_chat_without_rag.yaml` → `flows/1_chat_without_rag.md`
- `flows/2_chat_with_rag.yaml` → `flows/2_chat_with_rag.md`
- `flows/3_rag_with_websearch.yaml` → `flows/3_rag_with_websearch.md`
- `flows/4_simple_agent.yaml` → `flows/4_simple_agent.md`
- `flows/5_web_research_agent.yaml` → `flows/5_web_research_agent.md`
- `flows/6_multi_agent_research.yaml` → `flows/6_multi_agent_research.md`
- `flows/7_conversational_agent_with_memory.yaml` → `flows/7_conversational_agent_with_memory.md`
- `flows/8_faq_rag_pipeline.yaml` → `flows/8_faq_rag_pipeline.md`
- `flows/9_llm_evaluation.yaml` → `flows/9_llm_evaluation.md`
- `flows/10_scheduled_knowledge_refresh.yaml` → `flows/10_scheduled_knowledge_refresh.md`
- `flows/11_rag_with_groq.yaml` → `flows/11_rag_with_groq.md`

---

## How to run

```bash
# Install dependencies
uv sync

# Open the master pipeline notebook
uv run jupyter notebook 00_pipeline.ipynb

# Or open an individual focused notebook
uv run jupyter notebook embeddings.ipynb

# Vector search via CLI (no Jupyter needed)
uv run python main.py --query "Can I still join after the start date?"

# Full RAG answer
uv run python main.py --query "Can I still join after the start date?" --rag

# Start the Kestra orchestration layer
cd orchestration && docker compose up -d
```

### Environment variables (`.env` at project root)

```
OLLAMA_API_KEY=<your-key>
OPENAI_API_KEY=<your-key>
# For orchestration/docker-compose.yml:
SECRET_GEMINI_API_KEY=<your-key>
SECRET_TAVILY_API_KEY=<your-key>
SECRET_GROQ_API_KEY=<your-key>     # flows 7, 11 — free at console.groq.com
SECRET_OPENAI_API_KEY=<your-key>
```

---

## Dependencies

Python 3.12. Key packages (see `pyproject.toml`):

| Package | Used for |
|---------|----------|
| `requests` | Downloading FAQ data |
| `minsearch` | Keyword index + in-memory `VectorSearch` |
| `sentence-transformers` | `all-MiniLM-L6-v2` embedding model |
| `sqlitesearch` | Persistent SQLite vector index |
| `psycopg` | PostgreSQL client for pgvector backend |
| `openai` / `ollama` | LLM inference in the RAG pipeline |
| `python-dotenv` | Loading API keys from `.env` |
| `numpy` / `jupyter` | Notebook computing |
