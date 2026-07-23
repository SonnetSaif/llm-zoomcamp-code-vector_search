# 10_scheduled_knowledge_refresh

## Overview
Scheduled maintenance flow that refreshes RAG embeddings and validates with a smoke test.

## Why this flow matters
Keeps knowledge base current as source docs change, reducing stale-answer risk.

## Flow definition
- YAML: `10_scheduled_knowledge_refresh.yaml`
- Namespace/ID: `zoomcamp.10_scheduled_knowledge_refresh`

## Prerequisites
- `SECRET_GEMINI_API_KEY`
- Network access to release note source URLs

## Inputs
- None (schedule/manual run driven).

## How it works
1. `ingest_kestra_releases` re-ingests release docs with `drop: true`.
2. `smoke_test` runs a fixed sanity prompt against refreshed store.
3. `log_refresh_report` logs sources, response, and tokens.
4. `weekly_refresh` trigger schedules Monday 02:00 UTC runs (disabled by default).

## Step-by-step tutorial
1. Run manually first (`zoomcamp.10_scheduled_knowledge_refresh`).
2. Confirm ingest and smoke tasks succeed.
3. Enable `weekly_refresh` once validated.
4. Pair with `9_llm_evaluation` for post-refresh quality scoring.

## Expected outcome (what to verify)
- Ingestion succeeds across all configured URLs.
- Smoke response is coherent and factual.
- Scheduled runs remain stable after enablement.

## Troubleshooting
- Source URL changes can silently degrade freshness; update URLs promptly.
- Verify Gemini API key if tasks fail.

## Next recommended flow
- Run `9_llm_evaluation.yaml` after each refresh cycle.
