# 8_faq_rag_pipeline

> **Lesson reference:** [12-advanced-patterns.md](../lessons/12-advanced-patterns.md) | **YAML:** `8_faq_rag_pipeline.yaml`

---

## Learning objectives

By completing this flow you will:
- Apply RAG to a real-world domain knowledge base (LLM Zoomcamp course docs).
- Understand the mapping between the Python RAG pipeline in this repository (`rag_helper.py`, `rag-vector.ipynb`) and the Kestra equivalent.
- Run a side-by-side baseline vs. RAG comparison on a specific policy question.
- Know how to adapt the flow to your own documentation by changing source URLs.

---

## Core concept — Domain-specific RAG

Flows 2 and 3 used Kestra's own documentation as the knowledge source. In practice, you will build RAG pipelines over *your* data: course materials, internal wikis, product documentation, support FAQs, or API references.

The pattern is identical — the knowledge base changes, not the architecture.

### Mapping the Python pipeline to Kestra

This flow is the Kestra-orchestrated equivalent of the Python pipeline at the root of this repository:

| Python (this repo) | Kestra flow (this flow) |
|---|---|
| `ingest.py` — fetch FAQ JSON from GitHub | `IngestDocument` — fetch markdown from GitHub |
| `minsearch.VectorSearch` / SQLite | `KestraKVStore` embeddings |
| `RAGBase.search()` — cosine similarity search | `rag.ChatCompletion` with embedding retrieval |
| `RAGBase.ask()` → Ollama / OpenAI | `chatProvider` → Gemini |
| Jupyter notebook cell-by-cell execution | Kestra tasks with retries, scheduling, UI |

The key architectural insight: **the pattern is the same, the orchestration layer is different.** Kestra adds retries, scheduling, observability, and a UI without extra code.

### Why a side-by-side comparison?

Running `baseline_answer` and `rag_answer` in the same flow with the same question makes the quality gap immediately visible:

- **Baseline** answers with generic advice that could apply to any course.
- **RAG** answers with specifics from the actual course policies (e.g., the DataTalksClub late-join policy, cohort dates, certification requirements).

The `log_comparison` task prints both answers together so you can read them side by side without switching tabs.

### The `drop: true` trade-off

`drop: true` in `ingest_course_docs` clears and rebuilds the embedding store every run. This is convenient during development (always starts clean) but wasteful in production (re-embeds unchanged documents). Once your corpus is stable, set `drop: false` so re-runs *append* new documents rather than re-embedding everything.

---

## Flow definition
- YAML: `8_faq_rag_pipeline.yaml`
- Namespace / ID: `zoomcamp.8_faq_rag_pipeline`

## Prerequisites
- `SECRET_GEMINI_API_KEY`
- Outbound network access to `raw.githubusercontent.com`

## Inputs

| Input | Default | Description |
|---|---|---|
| `student_question` | "Can I still join the course after the start date?" | The question to answer with and without RAG |

---

## YAML walkthrough

### Task 1 — `baseline_answer` (no context)

```yaml
- id: baseline_answer
  type: io.kestra.plugin.ai.completion.ChatCompletion   # (1)
  messages:
    - type: USER
      content: "{{ inputs.student_question }}"
```

**(1)** Plain `ChatCompletion` — no retrieval, no system message. The model answers entirely from training data. This establishes a baseline to measure RAG improvement against.

### Task 2 — `ingest_course_docs`

```yaml
- id: ingest_course_docs
  type: io.kestra.plugin.ai.rag.IngestDocument
  provider:
    type: io.kestra.plugin.ai.provider.GoogleGemini
    modelName: gemini-embedding-001
    apiKey: "{{ secret('GEMINI_API_KEY') }}"
  embeddings:
    type: io.kestra.plugin.ai.embeddings.KestraKVStore
  drop: true
  fromExternalURLs:
    - https://raw.githubusercontent.com/DataTalksClub/llm-zoomcamp/main/README.md       # (2)
    - https://raw.githubusercontent.com/DataTalksClub/llm-zoomcamp/main/01-intro/README.md
```

**(2) Multi-URL ingestion** — You can list as many URLs as needed; `IngestDocument` fetches and embeds each one, building a unified vector store. Relevant chunks from any URL will be retrieved at query time.

### Task 3 — `rag_answer`

```yaml
- id: rag_answer
  type: io.kestra.plugin.ai.rag.ChatCompletion
  chatProvider:
    type: io.kestra.plugin.ai.provider.GoogleGemini
    modelName: gemini-2.5-flash
    apiKey: "{{ secret('GEMINI_API_KEY') }}"
  embeddingProvider:
    type: io.kestra.plugin.ai.provider.GoogleGemini
    modelName: gemini-embedding-001
    apiKey: "{{ secret('GEMINI_API_KEY') }}"
  embeddings:
    type: io.kestra.plugin.ai.embeddings.KestraKVStore
  systemMessage: |
    You are a helpful assistant for DataTalks.Club course participants.
    Answer questions accurately and concisely using only the provided course
    documentation. If the answer is not in the context, say so clearly
    rather than guessing.                             # (3)
  prompt: "{{ inputs.student_question }}"
```

**(3) Grounding instruction + citation discipline** — `"If the answer is not in the context, say so clearly rather than guessing"` prevents the model from mixing course-specific facts with hallucinated general advice. Without this, the model may confidently blend accurate policy details with invented ones.

### Task 4 — `log_comparison`

```yaml
- id: log_comparison
  type: io.kestra.plugin.core.log.Log
  message: |
    ❌ Without course context (generic answer):
    {{ outputs.baseline_answer.textOutput }}

    ✅ With course documentation (RAG answer):
    {{ outputs.rag_answer.textOutput }}
```

Running both answers in the same log task means they appear in the same execution log — you never need to navigate between two separate executions to compare them.

---

## Data flow

```
inputs.student_question
    │
    ├──────────────────────────────────────────────────────
    │ (baseline_answer — parallel path)                   │
    ▼                                                      │
ChatCompletion (no context)                               │
→ generic answer                                          │
    │                                                      │
    ◄──────────────────────────────────────────────────────
    │
    ▼ (ingest_course_docs)
Fetch README.md + 01-intro/README.md from GitHub
→ chunk → embed (gemini-embedding-001) → KestraKVStore
    │
    ▼ (rag_answer)
Embed question → similarity search → top chunks
→ [system + chunks + question] → Gemini 2.5 Flash
→ course-grounded answer
    │
    ▼ (log_comparison)
Both answers side by side in one log
```

Note: `baseline_answer` and `ingest_course_docs` could run in parallel (they are independent), but they run sequentially here for clarity. In production you would parallelise them with `parallel` blocks to reduce wall-clock time.

---

## Step-by-step tutorial

1. Run `zoomcamp.8_faq_rag_pipeline` with the default question.
2. Open `log_comparison` → **Logs**. Read both answers carefully.
3. Notice whether the RAG answer references the actual DataTalksClub late-join policy.
4. Re-run with: `"What is the deadline to submit the final project for the certificate?"` — another question only answerable from the docs.
5. Try: `"What programming language is used in the course?"` — this may be answerable without RAG too, demonstrating where RAG adds value vs. where it is neutral.

---

## Expected outcome

- `baseline_answer` gives generic course-registration advice.
- `rag_answer` gives policy-specific answers matching the course README.
- Token count for RAG answer is higher (retrieved chunks add tokens to the prompt).

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| RAG answer is still generic | Ingest failed silently | Check `ingest_course_docs` logs for HTTP errors on GitHub URLs |
| RAG answer says "not in context" for a clearly answerable question | Retrieval chunks don't match question vocabulary | Rephrase question to use terms that appear verbatim in the README |
| Baseline and RAG answers are identical | Model hallucinated the same thing it would have retrieved | Compare with a more obscure policy question that isn't in training data |
| GitHub 403 on raw URL | Rate limit or access issue | Wait a few minutes and retry; GitHub raw URLs occasionally throttle |

---

## Adapting this flow to your own data

1. Replace `fromExternalURLs` with your documentation URLs (internal wiki, Confluence export, etc.).
2. Update `systemMessage` to describe your domain: `"You are a support assistant for [Product]. Answer using the provided documentation only."`
3. Set `drop: false` once your corpus is stable — append-only ingestion avoids re-embedding unchanged docs.
4. Add more URLs to `fromExternalURLs` as your knowledge base grows; retrieval still returns only the most relevant chunks.

---

## Key concepts

| Term | Definition |
|---|---|
| **Domain-specific RAG** | A RAG pipeline where the knowledge base is your own data rather than public documentation |
| **Side-by-side comparison** | Running baseline and RAG answers in the same flow execution for direct quality comparison |
| **Citation discipline** | Instructing the model to say "not in context" rather than guess when retrieval misses the answer |
| **`drop: true`** | Clears the embedding store before ingesting — use during development, switch to `false` in production |

---

## Try this

- Replace the GitHub URLs with a local namespace file using `fromNamespaceFiles` (see IngestDocument docs). This eliminates the GitHub dependency.
- Add a third task that counts how many tokens the RAG answer used and logs a cost estimate.
- Remove the `systemMessage` grounding instruction and re-run. Does the model hallucinate more?

---

## Next recommended flow
Run `9_llm_evaluation.yaml` to move from manual visual comparison to automated, scored evaluation of baseline vs. RAG quality.
