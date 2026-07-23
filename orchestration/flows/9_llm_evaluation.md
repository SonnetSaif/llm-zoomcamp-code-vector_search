# 9_llm_evaluation

> **Lesson reference:** [11-evaluation.md](../lessons/11-evaluation.md) | **YAML:** `9_llm_evaluation.yaml`

---

## Learning objectives

By completing this flow you will:
- Understand why automated evaluation is essential for production RAG pipelines.
- Know the **LLM-as-judge** pattern and when it is appropriate.
- Write a judge prompt that reliably produces structured JSON scores.
- Parse that JSON with `{{ json() }}` in a downstream log task.
- Know the three evaluation dimensions (accuracy, relevance, specificity) and how to extend them.
- Understand how to build an evaluation dataset and connect evaluation to scheduled refresh.

---

## Core concept — LLM-as-judge evaluation

Manual inspection is fine for one-off checks. But as your RAG pipeline evolves — new documents ingested, model versions change, prompt rewrites — you need a *repeatable, automated* quality signal. Without it, regressions are only discovered when users complain.

### How LLM-as-judge works

A third LLM call is used as an objective scorer. The judge receives:
1. The original question
2. Two candidate answers (Candidate A = no RAG, Candidate B = with RAG)
3. A scoring rubric with explicit criteria and scale

It returns a structured JSON object with per-dimension scores and a winner — machine-readable output you can log, compare over time, or use to trigger alerts.

```
                  ┌─────────────────┐
                  │   eval_question  │
                  └────────┬────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
       ┌────────────┐            ┌────────────┐
       │  No-RAG    │            │  RAG LLM   │
       │  (baseline)│            │  (grounded)│
       └─────┬──────┘            └─────┬──────┘
             │                         │
             └────────────┬────────────┘
                          ▼
                   ┌────────────┐
                   │ Judge LLM  │
                   │ scores A/B │
                   └─────┬──────┘
                          ▼
                   ┌────────────┐
                   │ JSON report│
                   └────────────┘
```

### The three scoring dimensions

| Dimension | What it measures | Score |
|---|---|---|
| **Accuracy** | Does the answer correctly reflect the source material? | 1–5 |
| **Relevance** | Does the answer address what was actually asked? | 1–5 |
| **Specificity** | Are concrete details included, or is the answer vague? | 1–5 |

Total = sum of the three. Maximum = 15. Winner = higher total.

You can extend this rubric with domain-specific dimensions: `"conciseness"`, `"tone"`, `"cites_sources"`, etc.

### Why the judge needs a strict JSON contract

LLMs default to wrapping JSON in markdown code fences and adding commentary before the first brace. Both break `{{ json() }}` parsing. Two guards are required:

1. **System message**: explicit prohibition of markdown, fences, and commentary.
2. **Prompt**: provide the exact JSON skeleton with placeholder values — the model fills in scores, not structure.

---

## Flow definition
- YAML: `9_llm_evaluation.yaml`
- Namespace / ID: `zoomcamp.9_llm_evaluation`

## Prerequisites
- `SECRET_GEMINI_API_KEY`

## Inputs

| Input | Default | Description |
|---|---|---|
| `eval_question` | "Which features were released in Kestra 1.1?" | Question used for both candidates |

---

## YAML walkthrough

### Task 1 — `ingest_docs`

```yaml
- id: ingest_docs
  type: io.kestra.plugin.ai.rag.IngestDocument
  provider:
    type: io.kestra.plugin.ai.provider.GoogleGemini
    modelName: gemini-embedding-001
    apiKey: "{{ secret('GEMINI_API_KEY') }}"
  embeddings:
    type: io.kestra.plugin.ai.embeddings.KestraKVStore
  drop: true
  fromExternalURLs:
    - https://raw.githubusercontent.com/kestra-io/docs/...release-1-1/index.md
```

Ingests the knowledge base for Candidate B. Candidate A skips this step — it answers from training memory only.

### Tasks 2 & 3 — `answer_without_rag` and `answer_with_rag`

```yaml
- id: answer_without_rag
  type: io.kestra.plugin.ai.completion.ChatCompletion     # (1)
  messages:
    - type: USER
      content: "{{ inputs.eval_question }}"

- id: answer_with_rag
  type: io.kestra.plugin.ai.rag.ChatCompletion            # (2)
  ...
  systemMessage: |
    You are a helpful Kestra assistant. Answer using the provided documentation only.
  prompt: "{{ inputs.eval_question }}"
```

**(1)** Candidate A — plain completion, no retrieval.
**(2)** Candidate B — RAG completion, same question, same model, only retrieval differs.

Holding everything constant except retrieval means any score difference is directly attributable to the presence or absence of retrieved context.

### Task 4 — `judge_agent`

```yaml
- id: judge_agent
  type: io.kestra.plugin.ai.agent.AIAgent
  systemMessage: |
    You are an objective LLM evaluator.
    Output ONLY a valid JSON object — no markdown, no code fences, no commentary.  # (3)
  prompt: |
    Question: "{{ inputs.eval_question }}"

    Answer A (no RAG context):
    "{{ outputs.answer_without_rag.textOutput }}"

    Answer B (with RAG context):
    "{{ outputs.answer_with_rag.textOutput }}"

    Return this exact JSON structure with integer scores only:    # (4)
    {
      "answer_a": {
        "accuracy": 0,
        "relevance": 0,
        "specificity": 0,
        "total": 0,
        "summary": "one sentence assessment"
      },
      "answer_b": { ... },
      "winner": "A or B",
      "reasoning": "one sentence explaining the winner"
    }
```

**(3) System message JSON guard** — Prohibits markdown and code fences. This guard must be in the system message (not just the prompt) because some models ignore prompt-only instructions for output format.

**(4) Prompt skeleton** — Providing the exact JSON structure with `0` as placeholder values tells the model to fill in numbers, not invent new keys. "Integer scores only" prevents the model from returning floats or strings like `"4/5"`.

### Task 5 — `log_evaluation_report`

```yaml
- id: log_evaluation_report
  type: io.kestra.plugin.core.log.Log
  message: |
    Answer A — Accuracy: {{ json(outputs.judge_agent.textOutput).answer_a.accuracy }}/5  # (5)
    ...
    Winner: {{ json(outputs.judge_agent.textOutput).winner }}
```

**(5) `json()` + dot notation** — `json()` parses the judge's text output into a navigable object. `answer_a.accuracy` accesses the nested value. If `json()` throws, inspect `outputs.judge_agent.textOutput` raw to find what the model returned instead of clean JSON.

---

## Data flow

```
eval_question
    │
    ├─── (answer_without_rag) ──► training-only answer (Candidate A)
    │
    ├─── (ingest_docs) ──► KestraKVStore embeddings
    │         │
    │         └─── (answer_with_rag) ──► RAG-grounded answer (Candidate B)
    │
    └─── (judge_agent) ────────────────► receives A + B + rubric → JSON scores
                │
                └─── (log_evaluation_report) ──► parsed scores + winner in log
```

---

## Step-by-step tutorial

1. Run `zoomcamp.9_llm_evaluation` with the default question.
2. Open `log_evaluation_report` → check per-dimension scores and winner.
3. Verify `judge_agent` → `textOutput` raw: confirm it is clean JSON with no markdown.
4. Re-run with a different `eval_question` that is not in the release notes (e.g., "What is the price of Kestra Enterprise?"). Check whether the RAG answer still outperforms baseline, or whether both score equally poorly.
5. Re-run with a question easily answerable from training data (e.g., "What is YAML?"). Baseline may match RAG — useful to see where RAG adds no marginal value.

---

## Expected outcome

- `judge_agent.textOutput` is valid JSON parseable by `{{ json() }}`.
- RAG answer (Candidate B) usually wins on specificity and accuracy for version-specific questions.
- Scores for a general-knowledge question may be equal (neither RAG-dependent).
- Token costs are logged for all three LLM tasks; judge typically uses the most tokens.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `json()` throws error | Judge returned markdown-wrapped JSON | Strengthen system message: "Respond with ONLY the JSON object. The first character of your response must be `{`." |
| Both candidates score equally | Question answerable from training data alone | Use a more version-specific question |
| Candidate A wins | RAG retrieval returned irrelevant chunks | Check `ingest_docs` — URL may have returned empty content |
| `winner` field is missing | Model generated partial JSON | Add to system message: "You MUST include the `winner` and `reasoning` fields" |
| Judge scores inconsistently | Non-deterministic model output | Run 3× with the same question; average scores for more stable measurements |

---

## Building an evaluation dataset

One run gives a snapshot. Many runs give a trend.

1. Collect 10–20 representative questions for your domain.
2. Run `9_llm_evaluation.yaml` with each question.
3. Store the JSON output in a Kestra namespace file or external DB.
4. Re-run the full set after every knowledge-base refresh.
5. Any question where the RAG score drops after refresh points directly to an ingest problem.

---

## Connecting evaluation to the refresh cycle (production pattern)

```
10_scheduled_knowledge_refresh.yaml
           │
           ▼ (ExecutionStatus trigger on SUCCESS)
9_llm_evaluation.yaml
           │
           ▼ (if total score drops below threshold)
   Alert / fail the execution
```

Add this trigger to `9_llm_evaluation.yaml`:
```yaml
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

---

## Key concepts

| Term | Definition |
|---|---|
| **LLM-as-judge** | Using a separate LLM call to score other LLM outputs against a rubric |
| **Evaluation rubric** | The scoring dimensions and scale provided to the judge (accuracy, relevance, specificity, 1–5) |
| **Structured output** | Constraining the judge to return JSON so scores can be parsed programmatically |
| **Regression** | A quality drop detected when scores for the same question fall after a change to the pipeline |
| **Control variable** | Holding model, prompt, and question constant while varying only one factor (retrieval) |

---

## Try this

- Add a `"conciseness"` dimension (1–5) to the rubric and update the JSON skeleton. Does RAG answers score higher or lower on conciseness than baseline?
- Score the output from Flow 6 (`6_multi_agent_research`) by piping its JSON summary as a candidate answer.
- Run the same question 5 times and log all scores. Calculate the variance to understand judge reliability.

---

## Next recommended flow
Run `10_scheduled_knowledge_refresh.yaml` to automate knowledge-base maintenance — and then wire it to this evaluation flow so regressions are detected automatically.
