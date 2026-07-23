# 11_rag_with_groq

## Overview
Provider-comparison flow using one shared retrieval pipeline with two chat backends (Gemini and Groq/Llama).

## Why this flow matters
Lets you evaluate model/provider trade-offs while holding retrieval constant.

## Flow definition
- YAML: `11_rag_with_groq.yaml`
- Namespace/ID: `zoomcamp.11_rag_with_groq`

## Prerequisites
- `SECRET_GEMINI_API_KEY`
- `SECRET_GROQ_API_KEY`
- Network access to release note source URL

## Inputs
- `question`: prompt asked to both providers

## How it works
1. `ingest_docs` creates shared embeddings.
2. `gemini_answer` generates RAG answer with Gemini chat provider.
3. `groq_answer` generates RAG answer with Groq chat provider.
4. `log_comparison` prints both responses and token usage.

## Step-by-step tutorial
1. Run `zoomcamp.11_rag_with_groq` with default question.
2. Review both outputs in `log_comparison`.
3. Re-run with factual and open-ended prompts to compare behavior.

## Expected outcome (what to verify)
- Both answers are grounded in same retrieved corpus.
- Differences mostly reflect model style/quality trade-offs.
- Token usage differs between providers.

## Troubleshooting
- Verify Groq and Gemini secrets if one side fails.
- Check source URL if ingestion fails.

## Next recommended flow
- Run `9_llm_evaluation.yaml` with each provider setup for systematic scoring.
