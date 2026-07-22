# Evaluation

Deploying a RAG pipeline is easy. Knowing whether it's *good* is harder. This lesson covers automated LLM evaluation — a systematic way to measure answer quality so you can detect regressions before they reach users.

> Note: The flow in this lesson uses `{{ secret('GEMINI_API_KEY') }}`. Make sure you've completed the [setup instructions](03-setup.md) before running it.

## Why Evaluation Matters

A RAG pipeline can silently degrade in several ways:

- A source URL changes and the ingest step quietly fetches an empty page
- A model update changes response style or accuracy
- A new question type falls outside the scope of ingested documents

Without automated evaluation, you only discover these problems when a user complains.

## The LLM-as-Judge Pattern

The most practical evaluation approach for RAG pipelines uses a separate LLM call to score responses. The judge receives:

1. The original question
2. Two (or more) candidate answers
3. A rubric to score against

It returns structured scores that can be logged, tracked over time, or used to trigger alerts.

```
                  ┌─────────────┐
                  │  Question   │
                  └──────┬──────┘
                         │
           ┌─────────────┴─────────────┐
           ▼                           ▼
    ┌─────────────┐             ┌─────────────┐
    │  No-RAG LLM │             │  RAG LLM    │
    └──────┬──────┘             └──────┬──────┘
           │                           │
           └─────────────┬─────────────┘
                         ▼
                  ┌─────────────┐
                  │ Judge LLM   │
                  │ (scores A/B)│
                  └──────┬──────┘
                         ▼
                  ┌─────────────┐
                  │ Score report│
                  └─────────────┘
```

## Evaluation Dimensions

The example flow scores answers on three dimensions:

| Dimension | What it measures | Score |
|-----------|-----------------|-------|
| **Accuracy** | Does the answer reflect the source material correctly? | 1–5 |
| **Relevance** | Does the answer address what the user actually asked? | 1–5 |
| **Specificity** | Does the answer include concrete details vs. vague generalities? | 1–5 |

You can extend this rubric with dimensions like *conciseness*, *tone*, or domain-specific criteria.

## Example: Automated Evaluation Flow

Flow: [`9_llm_evaluation.yaml`](../flows/9_llm_evaluation.yaml)

This flow runs the full evaluation pipeline in one execution:

1. Ingest the Kestra 1.1 release notes into the embedding store
2. Generate **Candidate A**: answer without any retrieved context (baseline)
3. Generate **Candidate B**: answer with RAG context (retrieved from ingested docs)
4. Pass both answers to the **judge agent** with the scoring rubric
5. Log a structured report with per-dimension scores, totals, and a winner

The judge is prompted to return strict JSON so the `log_results` step can parse it with `{{ json(...) }}`. Never ask for a winner without a rubric — the judge needs explicit criteria to produce consistent scores.

Import and run `9_llm_evaluation.yaml` with the default question, then try a few of your own to see how RAG quality changes with different question types.

## Getting Consistent Judge Output

The biggest failure mode is the judge returning markdown-wrapped JSON or adding commentary before the opening brace. Guard against this with a firm system message:

```yaml
systemMessage: |
  You are an objective LLM evaluator.
  Output ONLY a valid JSON object — no markdown, no code fences, no commentary.
```

And in the prompt, provide the exact JSON skeleton with placeholder values:

```yaml
prompt: |
  Return this exact JSON structure with integer scores only:
  {
    "answer_a": { "accuracy": 0, "relevance": 0, ... },
    ...
  }
```

## Building an Evaluation Dataset

A single evaluation run gives you a snapshot. A dataset gives you a trend.

1. Collect 10–20 representative questions for your domain
2. Run `9_llm_evaluation.yaml` with each question
3. Store the JSON output in a Kestra namespace file or external database
4. Re-run after every knowledge-base refresh to track changes over time

Pairs that show a big drop in the RAG score after a refresh point directly to ingest problems — the right context is no longer being retrieved.

## Connecting Evaluation to the Refresh Cycle

The most robust production setup chains evaluation directly to the refresh flow:

```
10_scheduled_knowledge_refresh.yaml
           │
           ▼ (on success)
9_llm_evaluation.yaml
           │
           ▼ (if score drops below threshold)
  Alert / fail the execution
```

Kestra's flow triggers support exactly this pattern — use an `ExecutionStatus` trigger to start the evaluation flow automatically when the refresh completes. See the [Kestra docs on triggers](https://kestra.io/docs/workflow-components/triggers) for details.

## Limitations

LLM-as-judge evaluation is powerful but not perfect:

- The judge can be biased toward longer or more confident-sounding answers
- It cannot verify factual claims against ground truth without extra context
- Scores are subjective and can vary slightly between runs

For critical production use, combine LLM-as-judge with human spot checks and ground-truth comparisons where labeled data is available.

[← Memory and State](10-memory-and-state.md) | [Advanced Patterns →](12-advanced-patterns.md)
