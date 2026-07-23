# 2_chat_with_rag

> **Lesson reference:** [05-rag.md](../lessons/05-rag.md) | **YAML:** `2_chat_with_rag.yaml`

---

## Learning objectives

By completing this flow you will:
- Understand the two-phase RAG pipeline: **ingest** and **query**.
- Know what an embedding is, how it is stored, and how similarity search works.
- Explain the purpose of `drop: true`, `gemini-embedding-001`, and `KestraKVStore`.
- Measure the factual improvement over Flow 1's baseline.

---

## Core concept — Retrieval Augmented Generation (RAG)

RAG solves the LLM knowledge problem by injecting relevant external text into the prompt at query time. Instead of asking the model "what do you know?", you first retrieve the answer from a document store and then ask the model to summarize what you found.

### The two phases

```
── Phase 1: Ingest (run once, or on a schedule) ──────────────────────────
  Fetch document from URL
        │
        ▼
  Split into chunks (paragraphs or fixed-size windows)
        │
        ▼
  Embed each chunk → float vector (e.g. 768 or 3072 dimensions)
        │
        ▼
  Store vectors in KV Store (key = chunk hash, value = vector + text)

── Phase 2: Query (run on every user question) ──────────────────────────
  Embed the user question → query vector
        │
        ▼
  Cosine similarity search: find K chunks whose vectors are closest
        │
        ▼
  Inject retrieved chunks into the LLM prompt as context
        │
        ▼
  LLM generates answer grounded in that context
```

### What is an embedding?

An embedding model converts text into a high-dimensional numeric vector. The key property is that **semantically similar texts land close together in vector space**. When you embed both the stored chunks and the user question, the chunks whose meaning is closest to the question float to the top of a cosine-similarity ranking — even when the exact words differ.

Example: "new dashboard feature" and "improved UI panel" will be closer in vector space than "new dashboard feature" and "network timeout error", even though the first pair shares no words.

### Why KV Store?

`KestraKVStore` is Kestra's built-in key-value store. It is used here for **convenience in demos and small corpora** — it requires no extra infrastructure. For production (larger document sets, lower-latency requirements), replace it with a dedicated vector database (pgvector, Qdrant, Pinecone, etc.). See [Module 2: Vector Search](../../02-vector-search/lessons/04-vector-search.md) for that deeper dive.

---

## Flow definition
- YAML: `2_chat_with_rag.yaml`
- Namespace / ID: `zoomcamp.2_chat_with_rag`

## Prerequisites
- `SECRET_GEMINI_API_KEY`
- Outbound network access to `raw.githubusercontent.com`

## Inputs
- None. Both the source URL and question are fixed in the YAML.

---

## YAML walkthrough

### Task 1 — `ingest_release_notes`

```yaml
- id: ingest_release_notes
  type: io.kestra.plugin.ai.rag.IngestDocument    # (1)
  provider:
    type: io.kestra.plugin.ai.provider.GoogleGemini
    modelName: gemini-embedding-001               # (2)
    apiKey: "{{ secret('GEMINI_API_KEY') }}"
  embeddings:
    type: io.kestra.plugin.ai.embeddings.KestraKVStore  # (3)
  drop: true                                      # (4)
  fromExternalURLs:
    - https://raw.githubusercontent.com/kestra-io/docs/...
```

**(1) `rag.IngestDocument`** — Fetches the URL, splits the content into chunks, embeds each chunk with the specified model, and writes the vectors to the embedding store. All three steps happen inside this single plugin.

**(2) `gemini-embedding-001`** — A dedicated embedding model, not a chat model. Its job is to convert text into a high-dimensional vector. It is cheaper and faster than a chat model because it does not need to generate tokens — it only encodes meaning.

**(3) `KestraKVStore`** — The embedding backend. All vectors are stored in Kestra's native KV store under a namespace-scoped key. The same `KestraKVStore` reference in `chat_with_rag` below will read from this same store.

**(4) `drop: true`** — Clears any previously stored embeddings before ingesting. This guarantees a clean, reproducible store every run. In production you would set `drop: false` to *append* new documents without re-embedding existing ones.

### Task 2 — `chat_with_rag`

```yaml
- id: chat_with_rag
  type: io.kestra.plugin.ai.rag.ChatCompletion    # (5)
  chatProvider:                                   # (6)
    type: io.kestra.plugin.ai.provider.GoogleGemini
    modelName: gemini-2.5-flash
    apiKey: "{{ secret('GEMINI_API_KEY') }}"
  embeddingProvider:                              # (7)
    type: io.kestra.plugin.ai.provider.GoogleGemini
    modelName: gemini-embedding-001
    apiKey: "{{ secret('GEMINI_API_KEY') }}"
  embeddings:
    type: io.kestra.plugin.ai.embeddings.KestraKVStore
  systemMessage: |
    You are a helpful assistant... If you don't find the information
    in the context, say so.                       # (8)
  prompt: |
    Which features were released in Kestra 1.1?
```

**(5) `rag.ChatCompletion`** — The RAG-aware version of `ChatCompletion`. Before calling the chat model it embeds the `prompt`, searches the KV store for similar chunks, and prepends the top-K results to the prompt as context.

**(6) `chatProvider`** — The inference model used to generate the final answer. This is the same as the `provider` in `ai.completion.ChatCompletion`.

**(7) `embeddingProvider`** — A second provider block, used only to embed the *query* at search time. Must use the same embedding model that was used during ingestion, otherwise vector dimensions will mismatch and similarity scores will be meaningless.

**(8) Grounding instruction** — "If you don't find the information in the context, say so" is a critical guard. Without it the model falls back to hallucinating when the retrieved context is weak, defeating the purpose of RAG.

---

## Data flow

```
GitHub URL
    │
    ▼ (IngestDocument)
Fetch → Chunk → Embed (gemini-embedding-001)
    │
    ▼
KestraKVStore [vectors + text]

User question
    │
    ▼ (rag.ChatCompletion)
Embed question (gemini-embedding-001)
    │
    ▼
Cosine similarity search → top-K chunks
    │
    ▼
[system message + retrieved chunks + question] → Gemini 2.5 Flash
    │
    ▼
Grounded answer → log_results
```

---

## Step-by-step tutorial

1. Run `zoomcamp.2_chat_with_rag`.
2. Check the `ingest_release_notes` task — the **Outputs** tab shows how many chunks were ingested and stored.
3. Open `chat_with_rag` → **Outputs** → `textOutput`. Read the feature list carefully.
4. Compare it against the `1_chat_without_rag` output. Note which specific version-1.1 details appear that were missing or wrong in the baseline.
5. Open `chat_with_rag` → **Outputs** → `tokenUsage` to see how many tokens the RAG prompt consumed (retrieval context adds tokens).

---

## Expected outcome

- The answer will cite specific Kestra 1.1 features (e.g., AI features, plugin improvements, UI changes) that match the actual release blog post.
- Answers will be more concrete and use the language of the documentation.
- If a feature is not in the release notes, the model will decline to fabricate it (because of the grounding instruction).

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ingest_release_notes` fails with HTTP 404 | GitHub URL moved | Update `fromExternalURLs` to the new path |
| `chat_with_rag` returns generic answer | Ingest ran but store is empty | Check ingest logs for embedding errors; verify API key has Gemini Embeddings quota |
| `textOutput` says "I don't have information" | Retrieved chunks do not match the question | Try rephrasing the prompt to match keywords in the source doc |
| Dimension mismatch error | `embeddingProvider` model differs from ingest model | Ensure both tasks use `gemini-embedding-001` |

---

## Key concepts

| Term | Definition |
|---|---|
| **Embedding** | A numeric vector representation of text that encodes semantic meaning |
| **Cosine similarity** | Distance metric between vectors; 1 = identical meaning, 0 = unrelated |
| **Chunk** | A fragment of the original document (typically a paragraph) that is embedded individually |
| **Ingest** | The one-time (or scheduled) process of fetching, chunking, and embedding documents |
| **Grounding** | Anchoring an LLM's answer to specific retrieved text rather than training memory |

---

## Try this

- Change `fromExternalURLs` to a different Kestra release note (e.g., `release-1-0/index.md`) and ask the same question. The model should now describe 1.0 features instead.
- Remove the grounding instruction from `systemMessage` and re-run. Notice whether the model starts hallucinating again when the context is weak.
- Set `drop: false` and run twice. Check whether duplicate embeddings affect answer quality.

---

## Next recommended flow
Run `3_rag_with_websearch.yaml` to see how live web retrieval compares to the static ingestion approach used here.
