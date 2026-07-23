# 10_scheduled_knowledge_refresh

> **Lesson reference:** [12-advanced-patterns.md](../lessons/12-advanced-patterns.md) | **YAML:** `10_scheduled_knowledge_refresh.yaml`

---

## Learning objectives

By completing this flow you will:
- Understand why static RAG pipelines go stale and what a scheduled refresh solves.
- Know the semantics of `drop: true` (full rebuild) vs. `drop: false` (incremental append).
- Understand how Kestra schedule triggers work and why the trigger ships disabled.
- Run a smoke test after ingestion to verify the refresh succeeded.
- Wire this flow as an upstream trigger for `9_llm_evaluation.yaml`.

---

## Core concept — Knowledge base staleness

A RAG pipeline is only as good as its knowledge base. After you ingest documents once, the world keeps changing:

- A new Kestra release lands with features not in your embeddings.
- The source URL moves and your ingest step silently fetches an empty page.
- A documentation page is rewritten and old vector chunks now point to outdated text.

Without a refresh mechanism, your embeddings gradually diverge from reality. Users start getting outdated or wrong answers — and you only find out when they complain.

### The refresh pattern

```
Every Monday 02:00 UTC (or manually)
        │
        ▼
ingest_kestra_releases
  (drop: true → clears old vectors, re-embeds from scratch)
        │
        ▼
smoke_test
  (one fixed question → verify retrieval returns coherent answer)
        │
        ▼
log_refresh_report
  (timestamp + sources + smoke response + token count)
```

The smoke test is critical: it catches silent failures where the ingest step ran but returned empty content (e.g., a 404 that doesn't throw an exception). A coherent smoke answer confirms the KV Store has fresh, usable embeddings.

### `drop: true` semantics — full rebuild vs. incremental

| | `drop: true` | `drop: false` |
|---|---|---|
| **Behaviour** | Clears all stored embeddings before ingesting | Appends new chunks to existing store |
| **When to use** | Development, or when source docs are fully replaced | Production, when only new docs are added |
| **Risk of `true`** | Temporary gap: store is empty between drop and ingest completion | None |
| **Risk of `false`** | Duplicate or stale chunks if source URL content changes | Grows indefinitely without cleanup |

For a weekly full-site refresh like this flow, `drop: true` is correct: it guarantees a clean, consistent store after every run.

---

## Flow definition
- YAML: `10_scheduled_knowledge_refresh.yaml`
- Namespace / ID: `zoomcamp.10_scheduled_knowledge_refresh`

## Prerequisites
- `SECRET_GEMINI_API_KEY`
- Outbound network access to `raw.githubusercontent.com`

## Inputs
- None. Schedule-driven or manual run only.

---

## YAML walkthrough

### Task 1 — `ingest_kestra_releases`

```yaml
- id: ingest_kestra_releases
  type: io.kestra.plugin.ai.rag.IngestDocument
  provider:
    type: io.kestra.plugin.ai.provider.GoogleGemini
    modelName: gemini-embedding-001
    apiKey: "{{ secret('GEMINI_API_KEY') }}"
  embeddings:
    type: io.kestra.plugin.ai.embeddings.KestraKVStore
  drop: true                                           # (1)
  fromExternalURLs:
    - https://raw.githubusercontent.com/kestra-io/.../release-1-1/index.md
    - https://raw.githubusercontent.com/kestra-io/.../release-1-0/index.md  # (2)
```

**(1) `drop: true`** — On every refresh run, the entire KV Store is cleared before new embeddings are written. This prevents stale chunks from prior ingests from being retrieved alongside fresh ones. The trade-off: if this task fails mid-run, the store is temporarily empty. For production with high availability requirements, consider a two-store pattern (write to a staging store, then swap on success).

**(2) Multiple release URLs** — Adding `release-1-0` alongside `release-1-1` builds a multi-version knowledge base. A question about Kestra 1.0 features will retrieve from the 1.0 blog; a 1.1 question from the 1.1 blog. Both corpora live in the same KV Store but remain retrievable separately because vector similarity handles the routing.

### Task 2 — `smoke_test`

```yaml
- id: smoke_test
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
    You are a quality assurance assistant. Respond in exactly one sentence.  # (3)
  prompt: "What is Kestra and what was the headline feature of the 1.1 release?"
```

**(3) One-sentence constraint** — Forces a brief, parseable response. The smoke test is not about answer quality; it is about verifying the retrieval pipeline is functional. A one-sentence coherent answer is sufficient signal. If the smoke response is generic or says "I don't know," the ingest likely failed.

### The schedule trigger

```yaml
triggers:
  - id: weekly_refresh
    type: io.kestra.plugin.core.trigger.Schedule
    cron: "0 2 * * 1"      # (4)
    disabled: true          # (5)
```

**(4) Cron expression** — `"0 2 * * 1"` = every Monday at 02:00 UTC. The cron format is `minute hour day-of-month month day-of-week`.

**(5) `disabled: true`** — The trigger ships disabled so importing the flow does not immediately schedule it. Enable it after you have run the flow manually at least once and confirmed ingest and smoke test succeed.

**Two ways to enable the schedule:**

From the YAML:
```yaml
    disabled: false   # change this line and re-import the flow
```

From the Kestra UI:
> Open the flow → **Triggers** tab → toggle the weekly_refresh trigger on.

---

## Data flow

```
Monday 02:00 UTC (or manual run)
    │
    ▼ (ingest_kestra_releases)
GitHub raw URLs fetched
→ Chunks → Embed (gemini-embedding-001) → KestraKVStore [fresh vectors]
    │
    ▼ (smoke_test)
Fixed test question → embed → similarity search → Gemini 2.5 Flash → one-sentence answer
    │
    ▼ (log_refresh_report)
{{ now() }} + source list + smoke answer + token count → execution log
```

---

## Step-by-step tutorial

1. Run `zoomcamp.10_scheduled_knowledge_refresh` manually.
2. Verify `ingest_kestra_releases` → **Logs** show both URLs fetched successfully (no 404s).
3. Read the smoke test response in `log_refresh_report`. It should name Kestra and a specific 1.1 feature.
4. If the smoke test looks good, enable the schedule trigger from the Kestra UI.
5. After the first scheduled run completes, run `9_llm_evaluation.yaml` to confirm answer quality has not regressed.

---

## Expected outcome

- `ingest_kestra_releases` completes without HTTP errors.
- Smoke test response is one coherent sentence about Kestra and a specific 1.1 feature.
- `log_refresh_report` shows both URLs and a timestamp.
- After schedule is enabled, the flow runs autonomously every Monday.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Smoke test returns generic or empty answer | One or both URLs returned 404 or empty content | Verify URLs in a browser; update `fromExternalURLs` if docs moved |
| Smoke test uses Gemini but answer is about a different product | KV Store collision with another flow | Use a namespaced KV Store key via a `storeId` parameter if the plugin supports it |
| Scheduled run never fires | Trigger still disabled | Toggle trigger on in the Kestra UI, or set `disabled: false` in YAML |
| Ingest runs but KV Store shows 0 chunks | Content at URL is empty (page moved, access blocked) | Add a `Fail` condition task after `ingest_kestra_releases` that checks chunk count > 0 |
| Token costs spiking weekly | Multiple large source docs added to `fromExternalURLs` | Reduce `fromExternalURLs` list or filter by section using namespace file imports |

---

## Connecting to evaluation (production pattern)

```yaml
# Add to 9_llm_evaluation.yaml to trigger automatically after refresh:
triggers:
  - id: after_refresh
    type: io.kestra.plugin.core.trigger.Flow
    conditions:
      - type: io.kestra.plugin.core.condition.ExecutionFlowCondition
        namespace: zoomcamp
        flowId: 10_scheduled_knowledge_refresh
      - type: io.kestra.plugin.core.condition.ExecutionStatusCondition
        in: [SUCCESS]
```

This creates a dependency chain: refresh succeeds → evaluation runs automatically → if scores drop below threshold, an alert fires.

---

## Key concepts

| Term | Definition |
|---|---|
| **Knowledge staleness** | The gradual divergence of stored embeddings from the current state of source documents |
| **Scheduled refresh** | Periodic automatic re-ingestion to keep embeddings current |
| **Smoke test** | A fixed, known-good query run immediately after ingestion to verify the pipeline is functional |
| **Cron expression** | A time-based schedule specification: `"0 2 * * 1"` = Monday 02:00 UTC |
| **`disabled: true`** | Trigger property that prevents a schedule from firing on import |

---

## Try this

- Add a third URL (e.g., `release-1-2/index.md`) to `fromExternalURLs` and run manually. Verify the smoke test answer now references 1.2 features if they exist.
- Set `disabled: false` and import the flow. Verify the next Monday run appears in the scheduled executions list.
- After the refresh, immediately run `9_llm_evaluation.yaml` manually and record the scores. Run it again after the next scheduled refresh. Do scores improve, stay the same, or change?

---

## Next recommended flow
After enabling the schedule, run `9_llm_evaluation.yaml` after each refresh cycle to build a quality trend over time. Then explore `11_rag_with_groq.yaml` to see how provider swapping affects answer quality with no retrieval changes.
