# 1_chat_without_rag

> **Lesson reference:** [05-rag.md](../lessons/05-rag.md) | **YAML:** `1_chat_without_rag.yaml`

---

## Learning objectives

By completing this flow you will:
- Understand why a plain LLM call fails for version-specific factual questions.
- Recognize the symptoms of hallucination and training-cutoff degradation.
- Establish a measurable baseline so the improvement from RAG (Flow 2) is concrete.

---

## Core concept — why plain LLMs hallucinate on factual questions

A large language model is trained on a snapshot of the internet up to a certain date (the **training cutoff**). After that date it has no knowledge of new releases, updated policies, or changed documentation. Even within its training window, the model may have seen conflicting information and will synthesize a plausible-sounding but incorrect answer.

Two failure modes appear in this flow:

| Failure mode | What you see in output | Root cause |
|---|---|---|
| **Hallucination** | Features listed that never existed in Kestra 1.1, or existed in a different version | Model fills gaps with plausible-sounding detail |
| **Training cutoff** | Vague, generic description that applies to many versions | Model never saw Kestra 1.1 docs in training data |

The key insight: **the model has no way to distinguish between what it knows confidently and what it is making up.** It will answer with the same confident tone regardless.

This is the central motivation for RAG — retrieve the facts first, then ask the model to summarize them.

---

## Flow definition
- YAML: `1_chat_without_rag.yaml`
- Namespace / ID: `zoomcamp.1_chat_without_rag`

## Prerequisites
- `SECRET_GEMINI_API_KEY` — set as a base64-encoded environment variable before starting Kestra.

## Inputs
- None. The question is hardcoded in the YAML: *"Which features were released in Kestra 1.1? Please list at least 5 major features with brief descriptions."*

---

## YAML walkthrough

```yaml
tasks:
  - id: chat_without_rag
    type: io.kestra.plugin.ai.completion.ChatCompletion   # (1)
    provider:
      type: io.kestra.plugin.ai.provider.GoogleGemini    # (2)
      modelName: gemini-2.5-flash                        # (3)
      apiKey: "{{ secret('GEMINI_API_KEY') }}"           # (4)
    messages:
      - type: USER
        content: |
          Which features were released in Kestra 1.1? ...
```

**(1) `ChatCompletion` vs `rag.ChatCompletion`** — This is the plain completion plugin. It sends your messages directly to the model with no retrieval step. You will see `rag.ChatCompletion` in Flow 2, which adds the vector search layer between the user question and the model call.

**(2) Provider block** — Kestra's AI plugin abstracts all providers behind the same interface. Swapping `GoogleGemini` for `OpenAI` or `Groq` requires changing only this block; the task type and prompt stay identical.

**(3) `gemini-2.5-flash`** — A fast, general-purpose inference model. Used for *generation* here. In Flow 2 you will also see `gemini-embedding-001`, which is a separate, purpose-built *embedding* model. The two roles — embedding and inference — use different models with different APIs.

**(4) Secret reference** — `{{ secret('GEMINI_API_KEY') }}` reads the value from Kestra's encrypted secret store. The environment variable must be exported as `SECRET_GEMINI_API_KEY=<base64-encoded-key>` before Docker Compose starts Kestra.

```yaml
  - id: log_results
    type: io.kestra.plugin.core.log.Log
    message: |
      ❌ Response WITHOUT RAG (no retrieved context):
      {{ outputs.chat_without_rag.textOutput }}   # (5)
```

**(5) Output reference syntax** — `{{ outputs.<task-id>.textOutput }}` is Kestra's expression language for accessing the output of a previous task. `textOutput` is the field that `ChatCompletion` emits with the model's response string.

---

## Data flow

```
User question (hardcoded in YAML)
        │
        ▼
  Gemini 2.5 Flash
  (training data only — no external docs)
        │
        ▼
  textOutput → log_results
```

No retrieval, no context injection. The model answers entirely from memory.

---

## Step-by-step tutorial

1. Import and run `zoomcamp.1_chat_without_rag` from the Kestra UI.
2. Click into the `chat_without_rag` task → **Outputs** tab → read `textOutput`.
3. Open the `log_results` task → **Logs** tab for the formatted view.
4. Write down (or screenshot) the list of features the model claims were in Kestra 1.1.
5. Run `2_chat_with_rag.yaml` next and compare that list against what the release notes actually say.

---

## Expected outcome

- The answer will likely be plausible but inaccurate: generic feature names, wrong version attributions, or features that were in a completely different release.
- There will be no citations, no source links, and no hedging language — the model answers with false confidence.
- This is your **control sample**. Record it so the RAG improvement is measurable.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Flow fails immediately with `Unauthorized` | API key incorrect or not base64-encoded | Re-export: `export SECRET_GEMINI_API_KEY=$(echo -n "your-key" \| base64)` then restart Kestra |
| Flow fails with `model not found` | Model name typo or region restriction | Verify `gemini-2.5-flash` is available on your Gemini plan |
| Output is empty string | Quota exhausted on free tier | Wait for quota reset or switch to a paid key |

---

## Try this

- Change the question to ask about a very recent event (e.g., today's news). The model will either refuse or hallucinate — demonstrating the training cutoff problem clearly.
- Ask the same question to OpenAI by swapping the provider block. Notice whether the hallucination pattern differs between providers.

---

## Next recommended flow
Run `2_chat_with_rag.yaml` immediately after this one so you can compare outputs side by side. The question is identical — the only difference is the retrieval step added in Flow 2.
