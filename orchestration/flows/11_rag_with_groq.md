# 11_rag_with_groq

> **Lesson reference:** [12-advanced-patterns.md](../lessons/12-advanced-patterns.md) | **YAML:** `11_rag_with_groq.yaml`

---

## Learning objectives

By completing this flow you will:
- Understand the **decoupling of embedding and inference** in a RAG pipeline.
- Know why you can mix providers (Gemini for embeddings, Groq for inference) without breaking retrieval.
- Run an A/B comparison of two inference backends on the same retrieved context.
- Reason about when to choose one provider over another based on cost, latency, and style.
- Know how to get a free Groq API key and add it as a Kestra secret.

---

## Core concept — Provider decoupling in RAG

In all previous flows, Gemini handled both embedding (turning text into vectors) and inference (generating the answer). These are two *completely separate* operations with two *completely separate* API calls. They can use different providers, different models, and even different API keys — **as long as the same embedding model is used for both ingestion and query-time retrieval**.

```
Ingest phase:    text chunks → [gemini-embedding-001] → vectors → KV Store
Query phase:     user question → [gemini-embedding-001] → query vector
                                     ↓
                             similarity search → top chunks
                                     ↓
                 [chatProvider: Gemini OR Groq OR OpenAI OR Anthropic] → answer
```

The embedding model creates the vector space that defines what "similar" means. The chat model only sees the retrieved text chunks plus the question — it has no awareness of how retrieval worked.

### Why swap the chat provider?

- **Cost**: Groq's Llama 3 is often faster and cheaper per token than Gemini Flash for straightforward Q&A.
- **Latency**: Groq uses custom inference hardware (LPUs) that can return responses significantly faster.
- **Style/format**: Different models have different verbosity, formatting habits, and citation styles.
- **Fallback**: If your primary provider hits a rate limit or outage, the same RAG pipeline can route to an alternative.

### What stays the same

Both `gemini_answer` and `groq_answer` use **identical**:
- `ingest_docs` — same embedded corpus
- `embeddingProvider` — `gemini-embedding-001`
- `embeddings` — same `KestraKVStore`
- `systemMessage` and `prompt` — same instructions and question

**Only `chatProvider` changes.** This controlled difference makes the comparison a clean A/B test.

---

## Flow definition
- YAML: `11_rag_with_groq.yaml`
- Namespace / ID: `zoomcamp.11_rag_with_groq`

## Prerequisites
- `SECRET_GEMINI_API_KEY`
- `SECRET_GROQ_API_KEY`

**Getting a free Groq API key:**
1. Sign up at [console.groq.com](https://console.groq.com/) (free tier, no credit card)
2. Create an API key in the dashboard
3. Export it as a secret before starting Kestra:
   ```bash
   export SECRET_GROQ_API_KEY=$(echo -n "your-groq-key-here" | base64)
   docker compose up -d
   ```

## Inputs

| Input | Default | Description |
|---|---|---|
| `question` | "Which features were released in Kestra 1.1?" | Question sent to both providers |

---

## YAML walkthrough

### Task 1 — `ingest_docs` (shared)

```yaml
- id: ingest_docs
  type: io.kestra.plugin.ai.rag.IngestDocument
  provider:
    type: io.kestra.plugin.ai.provider.GoogleGemini
    modelName: gemini-embedding-001               # (1)
    apiKey: "{{ secret('GEMINI_API_KEY') }}"
  embeddings:
    type: io.kestra.plugin.ai.embeddings.KestraKVStore
  drop: true
  fromExternalURLs:
    - https://raw.githubusercontent.com/kestra-io/docs/.../release-1-1/index.md
```

**(1)** Gemini is used for embedding here. It will also be used in `embeddingProvider` in both answer tasks. Consistency between ingest and retrieval embedding models is required — they must produce vectors in the same space.

### Task 2 — `gemini_answer`

```yaml
- id: gemini_answer
  type: io.kestra.plugin.ai.rag.ChatCompletion
  chatProvider:                                    # (2)
    type: io.kestra.plugin.ai.provider.GoogleGemini
    modelName: gemini-2.5-flash
    apiKey: "{{ secret('GEMINI_API_KEY') }}"
  embeddingProvider:                               # (3)
    type: io.kestra.plugin.ai.provider.GoogleGemini
    modelName: gemini-embedding-001
    apiKey: "{{ secret('GEMINI_API_KEY') }}"
  embeddings:
    type: io.kestra.plugin.ai.embeddings.KestraKVStore
  systemMessage: |
    You are a helpful Kestra assistant. Answer concisely using the documentation provided.
  prompt: "{{ inputs.question }}"
```

**(2) `chatProvider`** — The model that generates the answer text. This is the only block that differs between `gemini_answer` and `groq_answer`.

**(3) `embeddingProvider`** — Used at query time to embed the user question. Must match the embedding model used during ingestion (`gemini-embedding-001`). Even though Groq is the chat provider in the next task, Gemini still handles embedding in both tasks.

### Task 3 — `groq_answer`

```yaml
- id: groq_answer
  type: io.kestra.plugin.ai.rag.ChatCompletion
  chatProvider:
    type: io.kestra.plugin.ai.provider.Groq        # (4)
    modelName: llama-3.3-70b-versatile             # (5)
    apiKey: "{{ secret('GROQ_API_KEY') }}"
  embeddingProvider:                               # (same as gemini_answer)
    type: io.kestra.plugin.ai.provider.GoogleGemini
    modelName: gemini-embedding-001
    apiKey: "{{ secret('GEMINI_API_KEY') }}"
  embeddings:
    type: io.kestra.plugin.ai.embeddings.KestraKVStore
  systemMessage: |
    You are a helpful Kestra assistant. Answer concisely using the documentation provided.
  prompt: "{{ inputs.question }}"
```

**(4) `io.kestra.plugin.ai.provider.Groq`** — The Groq inference provider. Uses Groq's LPU-based API at `api.groq.com`. Only this line differs from `gemini_answer`.

**(5) `llama-3.3-70b-versatile`** — Meta's Llama 3.3 70B model running on Groq's infrastructure. The 70B parameter count makes it competitive with Gemini 2.5 Flash for factual Q&A while often being faster and cheaper.

### Task 4 — `log_comparison`

```yaml
- id: log_comparison
  type: io.kestra.plugin.core.log.Log
  message: |
    🔵 Gemini 2.5 Flash:
    {{ outputs.gemini_answer.textOutput }}
    📊 Tokens: {{ outputs.gemini_answer.tokenUsage.totalTokenCount }}

    🟠 Groq — Llama 3.3 70B:
    {{ outputs.groq_answer.textOutput }}
    📊 Tokens: {{ outputs.groq_answer.tokenUsage.totalTokenCount }}
```

Both answers and their token counts appear in one log entry for side-by-side comparison.

---

## Data flow

```
inputs.question
    │
    ▼ (ingest_docs)
GitHub URL → Chunks → Embed (Gemini gemini-embedding-001) → KestraKVStore
    │
    ├─── (gemini_answer)
    │     Embed question (Gemini) → similarity search → chunks
    │     → [system + chunks + question] → Gemini 2.5 Flash → textOutput
    │
    └─── (groq_answer)
          Embed question (Gemini) → similarity search → SAME chunks
          → [system + chunks + question] → Groq Llama 3.3 70B → textOutput
    │
    ▼ (log_comparison)
Both textOutputs + token counts side by side
```

Note: `gemini_answer` and `groq_answer` are sequentially dependent on `ingest_docs` but independent of each other — they could run in parallel with a `parallel` block for faster execution.

---

## Step-by-step tutorial

1. Set up `SECRET_GROQ_API_KEY` and restart Kestra.
2. Run `zoomcamp.11_rag_with_groq` with the default question.
3. Open `log_comparison` → read both answers carefully.
4. Note differences in: verbosity, formatting style, feature list completeness.
5. Check token counts — they often differ because the models use different tokenizers.
6. Re-run with an open-ended question (e.g., "How would you explain Kestra's architecture to a junior engineer?") to see stylistic differences more clearly.
7. Run `9_llm_evaluation.yaml` and use one provider's answer as Candidate A and the other as Candidate B to get a formal quality score.

---

## Expected outcome

- Both answers are grounded in the same retrieved corpus (Kestra 1.1 release notes).
- Differences reflect model style, not retrieval differences.
- Token counts differ due to different tokenizers (Groq counts may appear lower for the same text).
- Response latency may differ significantly; Groq is often faster.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `groq_answer` fails with `Unauthorized` | `SECRET_GROQ_API_KEY` not set | Add key, restart Kestra: `docker compose restart` |
| `groq_answer` fails with `model not found` | Model name changed on Groq's end | Check [console.groq.com/docs/models](https://console.groq.com/docs/models) for current names |
| Both answers look identical | Retrieved context is so specific that both models paraphrase it the same way | Use a more open-ended question to surface stylistic differences |
| `gemini_answer` fails but `groq_answer` succeeds | Gemini rate limit hit (embedding + inference from same key) | Use a separate Gemini key for embedding vs. inference |
| Token count shows 0 for one task | Cached output from prior run | Change `inputs.question` slightly to force a fresh execution |

---

## Provider comparison reference

| Provider | Plugin type | Best for |
|---|---|---|
| Google Gemini | `io.kestra.plugin.ai.provider.GoogleGemini` | Embeddings + general inference; strong multimodal |
| OpenAI | `io.kestra.plugin.ai.provider.OpenAI` | GPT-4o family; strong reasoning and code |
| Anthropic Claude | `io.kestra.plugin.ai.provider.Anthropic` | Long context; strong instruction following |
| Groq | `io.kestra.plugin.ai.provider.Groq` | High throughput, low latency, cost-efficient |
| Ollama (local) | `io.kestra.plugin.ai.provider.Ollama` | Fully local inference; no data leaves your machine |

See the [full provider list](https://kestra.io/plugins/plugin-ai/provider) for current models and options.

---

## Key concepts

| Term | Definition |
|---|---|
| **Provider decoupling** | Using different providers for embedding (ingest/retrieval) and inference (answer generation) |
| **`chatProvider`** | The inference model used to generate the final answer in `rag.ChatCompletion` |
| **`embeddingProvider`** | The model used to embed the query at retrieval time; must match the ingest embedding model |
| **A/B testing** | Running two variants of the same pipeline with one variable changed to compare outcomes |
| **LPU** | Language Processing Unit — Groq's custom inference hardware optimized for low-latency LLM calls |

---

## Try this

- Change `groq_answer` to use `llama-3.1-8b-instant` (a smaller, faster Groq model). How does quality compare to the 70B version?
- Add a third task using `io.kestra.plugin.ai.provider.OpenAI` with `gpt-4o-mini`. Now you have a three-way provider comparison.
- Feed the outputs of this flow into `9_llm_evaluation.yaml` as Candidate A (Gemini) and Candidate B (Groq). Run 10 different questions and tally which provider wins more often.

---

## Next recommended flow
Run `9_llm_evaluation.yaml` with each provider's output to get formal quality scores, then use those scores to make an evidence-based provider selection for your production pipeline.
