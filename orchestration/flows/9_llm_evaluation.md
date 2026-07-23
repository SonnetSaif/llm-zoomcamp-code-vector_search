# 9_llm_evaluation

## Overview
LLM-as-judge flow that scores two candidate answers: no-RAG baseline vs RAG answer.

## Why this flow matters
Provides repeatable quality measurement to detect regressions instead of relying on ad-hoc checks.

## Flow definition
- YAML: `9_llm_evaluation.yaml`
- Namespace/ID: `zoomcamp.9_llm_evaluation`

## Prerequisites
- `SECRET_GEMINI_API_KEY`

## Inputs
- `eval_question`: question used for both candidates

## How it works
1. `ingest_docs` builds RAG context from release notes.
2. `answer_without_rag` generates candidate A.
3. `answer_with_rag` generates candidate B.
4. `judge_agent` scores both and emits strict JSON.
5. `log_evaluation_report` prints parsed scores and winner.

## Step-by-step tutorial
1. Run `zoomcamp.9_llm_evaluation` with default question.
2. Review scoring fields and winner in `log_evaluation_report`.
3. Re-run with multiple question styles and compare trends.

## Expected outcome (what to verify)
- Judge output is valid JSON.
- RAG candidate usually wins on specificity/accuracy.
- Total scores and winner fields are populated.

## Troubleshooting
- If parsing fails, inspect judge output format.
- Verify ingestion succeeded and API key is valid.

## Next recommended flow
- Run `10_scheduled_knowledge_refresh.yaml` and then re-run this evaluation flow periodically.
