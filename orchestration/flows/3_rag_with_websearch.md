# 3_rag_with_websearch

> **Lesson reference:** [05-rag.md](../lessons/05-rag.md) | **YAML:** `3_rag_with_websearch.yaml`

---

## Learning objectives

By completing this flow you will:
- Distinguish between **static RAG** (pre-ingested vectors) and **web search RAG** (live retrieval at query time).
- Understand what a `contentRetriever` is and how it differs from an embedding store.
- Know when to choose live retrieval over a static knowledge base.
- Recognize the trade-offs: freshness vs. reliability and cost.

---

## Core concept — Web search as a retriever

In Flow 2, context was retrieved from vectors you stored in advance. **Web search RAG skips the ingestion phase entirely.** At query time, the retriever (Tavily) performs a live web search, collects the top results, and passes them as context to the chat model — all within a single task execution.

### Static RAG vs. web search RAG

| | Static RAG (Flow 2) | Web Search RAG (Flow 3) |
|---|---|---|
| **Data source** | Documents you ingested in advance | Live web results at query time |
| **Ingestion step** | Required | Not required |
| **Freshness** | Depends on last ingest run | Always current |
| **Consistency** | Same answer on every run (corpus fixed) | Can vary as web changes |
| **Control over source** | High — you choose what to ingest | Low — depends on search engine coverage |
| **Best for** | Internal docs, policies, fixed knowledge bases | Time-sensitive or rapidly changing info |
| **Cost per query** | 1× embedding call + KV lookup | 1× Tavily search API call |

### How Tavily fits in

[Tavily](https://www.tavily.com/) is a search API optimised for LLM pipelines. Unlike a standard web search, it:
- Returns clean extracted text (not raw HTML)
- Ranks results by relevance for AI consumption
- Supports configuring `maxResults` to control context length

In Kestra, Tavily is wired as a `contentRetriever` on the `rag.ChatCompletion` task. The plugin calls Tavily with your prompt as the query, collects results, and prepends them to the system context before calling the chat model.

### No `embeddingProvider` needed

Because web search retrieval does not use vectors, this flow has **no embedding model and no KV store**. The `rag.ChatCompletion` task detects that a `contentRetriever` is configured and uses it instead of vector similarity search.

---

## Flow definition
- YAML: `3_rag_with_websearch.yaml`
- Namespace / ID: `zoomcamp.3_rag_with_websearch`

## Prerequisites
- `SECRET_OPENAI_API_KEY` (this flow uses OpenAI, not Gemini)
- `SECRET_TAVILY_API_KEY`

> **Why OpenAI here?** This flow demonstrates that Kestra's provider abstraction is truly agnostic. To switch to Gemini, replace the `chatProvider` block with `io.kestra.plugin.ai.provider.GoogleGemini` and your Gemini key — nothing else changes.

## Inputs
- None. The question is fixed: *"What is the latest release of Kestra?"*

---

## YAML walkthrough

```yaml
tasks:
  - id: chat_with_rag_and_websearch_content_retriever
    type: io.kestra.plugin.ai.rag.ChatCompletion       # (1)
    chatProvider:
      type: io.kestra.plugin.ai.provider.OpenAI        # (2)
      apiKey: "{{ secret('OPENAI_API_KEY') }}"
      modelName: gpt-5-mini
    contentRetrievers:                                  # (3)
      - type: io.kestra.plugin.ai.retriever.TavilyWebSearch
        apiKey: "{{ secret('TAVILY_API_KEY') }}"
    systemMessage: You are a helpful assistant that can answer questions about Kestra.
    prompt: What is the latest release of Kestra?
```

**(1) `rag.ChatCompletion` — same task type as Flow 2**, but driven by `contentRetrievers` instead of an `embeddings` store. The plugin handles both retrieval strategies through the same surface.

**(2) `OpenAI` provider** — Demonstrates provider swappability. Only the `chatProvider` block changes when you switch inference backends; the retrieval layer is unaffected.

**(3) `contentRetrievers`** — A list of retriever plugins. At query time, each retriever is called with the `prompt` text, and the results are concatenated into the context window. `TavilyWebSearch` is the most common, but you can also use `GoogleCustomWebSearch` or build a custom retriever.

---

## Data flow

```
User prompt: "What is the latest release of Kestra?"
        │
        ▼ (TavilyWebSearch)
Tavily API → live web search → top N result texts extracted
        │
        ▼
[system message + Tavily results + prompt] → OpenAI GPT
        │
        ▼
Answer grounded in live web content → task output
```

No KV store, no embedding model, no ingestion step. The entire pipeline runs in one task.

---

## Step-by-step tutorial

1. Ensure both `SECRET_OPENAI_API_KEY` and `SECRET_TAVILY_API_KEY` are set and Kestra is restarted.
2. Run `zoomcamp.3_rag_with_websearch`.
3. Open the task output — the answer should reference the latest Kestra release by name and version.
4. Re-run the flow a week later and compare: the answer may change if a new Kestra release was published in the interim.
5. **Compare with Flow 2**: Flow 2 references Kestra 1.1 specifically (its corpus is pinned). Flow 3 will surface whichever version is most discussed on the web right now.

---

## Expected outcome

- The answer will include a specific Kestra version number and features from live web results.
- Outputs will mention release notes, blog posts, or GitHub entries found by Tavily.
- The answer can vary between runs as the web changes — this is by design.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `Unauthorized` on OpenAI call | Key not set or wrong format | Re-export `SECRET_OPENAI_API_KEY` (base64-encoded); restart Kestra |
| `Unauthorized` on Tavily call | Tavily key missing | Add `SECRET_TAVILY_API_KEY` and restart |
| Answer is generic or vague | Tavily returned low-relevance results | Try a more specific prompt (e.g., add the project name and version) |
| `model not found` for `gpt-5-mini` | Model name changed on OpenAI's end | Update `modelName` to a current model (e.g., `gpt-4o-mini`) |

---

## Key concepts

| Term | Definition |
|---|---|
| **contentRetriever** | A plugin that fetches external context at query time (web search, database, etc.) instead of from a pre-built vector store |
| **Tavily** | A search API designed for LLM pipelines that returns clean extracted text |
| **Live retrieval** | Fetching context at the moment a question is asked, not in advance |
| **Provider agnostic** | The ability to swap inference backends (OpenAI, Gemini, Groq) without changing retrieval logic |

---

## Try this

- Add `maxResults: 10` to the `TavilyWebSearch` config and compare the answer quality and token count versus the default.
- Swap `chatProvider` to Gemini by replacing the type with `io.kestra.plugin.ai.provider.GoogleGemini` and `modelName: gemini-2.5-flash`. Verify the retrieval behavior is identical.
- Add a second `contentRetriever` of type `io.kestra.plugin.ai.retriever.GoogleCustomWebSearch` (if you have a key) and observe how combined retrieval affects answer quality.

---

## Next recommended flow
Run `7_conversational_agent_with_memory.yaml` to layer persistent memory on top of the web retrieval pattern introduced here.
