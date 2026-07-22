# Advanced Patterns

This lesson covers three production-oriented patterns that extend the core RAG and agent building blocks from earlier lessons: domain-specific RAG over your own data, scheduled knowledge-base maintenance, and multi-provider inference for cost and quality trade-offs.

> Note: Flows in this lesson use `{{ secret('GEMINI_API_KEY') }}` and `{{ secret('GROQ_API_KEY') }}`. Make sure you've completed the [setup instructions](03-setup.md) and added the relevant secrets before running them.

## Pattern 1 — Domain-Specific RAG

The RAG examples in [Lesson 5](05-rag.md) use Kestra's own documentation as the knowledge source. In practice, you'll ingest *your own* data: internal wikis, product docs, support FAQs, or API references.

Flow: [`8_faq_rag_pipeline.yaml`](../flows/8_faq_rag_pipeline.yaml)

This flow is the Kestra-orchestrated equivalent of the Python pipeline at the root of this repository (`rag-vector.ipynb`, `rag_helper.py`). It ingests the DataTalks.Club LLM Zoomcamp course README and answers student questions grounded in actual course policies.

It also runs a side-by-side comparison — the same question answered with and without retrieved context — so the quality difference is immediately visible.

### Mapping the Python pipeline to Kestra

| Python (this repo) | Kestra flow (flow 8) |
|--------------------|----------------------|
| `ingest.py` — fetch FAQ JSON | `IngestDocument` — fetch markdown from GitHub |
| `minsearch.VectorSearch` / `sqlitesearch` | `KestraKVStore` embeddings |
| `RAGBase.search()` | `rag.ChatCompletion` with embedding retrieval |
| `RAGBase.ask()` → Ollama / OpenAI | `chatProvider` → Gemini |

The pattern is identical. The difference is that Kestra handles retries, scheduling, observability, and UI without additional code.

### Adapting for your own data

To point the flow at your own documentation:

1. Replace the URLs in `fromExternalURLs` with your content
2. Update `systemMessage` to describe your domain and expected answer style
3. Keep `drop: true` during development; switch to `drop: false` once the corpus is stable so re-runs append rather than replace

Supported source types include external URLs, Kestra namespace files, and inline text — see the [`IngestDocument` plugin docs](https://kestra.io/plugins/plugin-ai/rag) for the full list.

## Pattern 2 — Scheduled Knowledge Refresh

Static RAG pipelines go stale. Documentation is updated, new releases land, policies change. Without a refresh mechanism, your embeddings will gradually diverge from reality and answer quality will silently degrade.

Flow: [`10_scheduled_knowledge_refresh.yaml`](../flows/10_scheduled_knowledge_refresh.yaml)

This flow runs the full ingest cycle on a weekly schedule, then executes a smoke test query to verify the refresh worked:

```
Every Monday 02:00 UTC
        │
        ▼
ingest_kestra_releases (drop: true → re-embeds from scratch)
        │
        ▼
smoke_test (one sentence RAG query against fresh embeddings)
        │
        ▼
log_refresh_report
```

### Enabling the schedule

The trigger ships with `disabled: true` so the flow is safe to import without immediately scheduling it. Enable it in two ways:

**From the YAML:**
```yaml
triggers:
  - id: weekly_refresh
    type: io.kestra.plugin.core.trigger.Schedule
    cron: "0 2 * * 1"
    disabled: false   # ← change this
```

**From the Kestra UI:**  
Open the flow → Triggers tab → toggle the schedule on.

### Connecting refresh to evaluation

After a successful refresh, run `9_llm_evaluation.yaml` to confirm answer quality. If you wire the evaluation as a downstream trigger, regressions surface immediately rather than when the next user asks a question:

```yaml
# In 9_llm_evaluation.yaml — add this trigger block
triggers:
  - id: after_refresh
    type: io.kestra.plugin.core.trigger.Flow
    conditions:
      - type: io.kestra.plugin.core.condition.ExecutionFlowCondition
        namespace: zoomcamp
        flowId: 10_scheduled_knowledge_refresh
      - type: io.kestra.plugin.core.condition.ExecutionStatusCondition
        in:
          - SUCCESS
```

## Pattern 3 — Multi-Provider Inference

All previous flows use Gemini for both embeddings and inference. But embeddings and inference are independent concerns — you can mix providers freely. This matters when you want to:

- Use a cheaper or faster model for inference while keeping high-quality embeddings
- A/B test two models on the same retrieved context
- Fall back to an alternative provider if one is unavailable

Flow: [`11_rag_with_groq.yaml`](../flows/11_rag_with_groq.yaml)

This flow runs the same question through two inference backends — Gemini 2.5 Flash and Groq (Llama 3.3 70B) — using identical embeddings and retrieved context. Only the `chatProvider` block differs:

```yaml
# Gemini inference
chatProvider:
  type: io.kestra.plugin.ai.provider.GoogleGemini
  modelName: gemini-2.5-flash
  apiKey: "{{ secret('GEMINI_API_KEY') }}"

# Groq inference (Llama 3.3 70B)
chatProvider:
  type: io.kestra.plugin.ai.provider.Groq
  modelName: llama-3.3-70b-versatile
  apiKey: "{{ secret('GROQ_API_KEY') }}"
```

The `embeddingProvider` and `embeddings` blocks are identical in both tasks — embeddings are computed once during ingest and shared.

### Getting a Groq API key

1. Sign up at [console.groq.com](https://console.groq.com/)
2. Create an API key (free tier is generous)
3. Add it as a secret before starting Kestra:
   ```bash
   export SECRET_GROQ_API_KEY=$(echo -n "your-groq-key-here" | base64)
   docker compose up -d
   ```

### Supported providers

Kestra's AI plugin supports all major providers with the same interface:

| Provider | Plugin type |
|----------|-------------|
| Google Gemini | `io.kestra.plugin.ai.provider.GoogleGemini` |
| OpenAI | `io.kestra.plugin.ai.provider.OpenAI` |
| Anthropic Claude | `io.kestra.plugin.ai.provider.Anthropic` |
| Groq | `io.kestra.plugin.ai.provider.Groq` |
| Ollama (local) | `io.kestra.plugin.ai.provider.Ollama` |

See the [full provider list](https://kestra.io/plugins/plugin-ai/provider) for current models and options.

## Putting It All Together

The three patterns in this lesson combine naturally into a production pipeline:

```
10_scheduled_knowledge_refresh  (weekly: re-ingest + smoke test)
        │
        ▼ (on success trigger)
9_llm_evaluation                (verify quality with LLM-as-judge)
        │
        ▼ (on demand)
8_faq_rag_pipeline              (answer user questions)
```

Domain-specific RAG (flow 8) serves users. Scheduled refresh (flow 10) keeps the knowledge base fresh. Automated evaluation (flow 9) catches regressions. This three-layer structure is the foundation of a maintainable production RAG system.

[← Evaluation](11-evaluation.md) | [Back to module](../)
