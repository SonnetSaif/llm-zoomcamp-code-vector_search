# 2_chat_with_rag

## Overview
Two-stage RAG flow: ingest release notes, then answer using retrieved context.

## Why this flow matters
Shows how retrieval grounding improves factual accuracy and specificity.

## Flow definition
- YAML: `2_chat_with_rag.yaml`
- Namespace/ID: `zoomcamp.2_chat_with_rag`

## Prerequisites
- `SECRET_GEMINI_API_KEY`
- Network access to the GitHub raw release note URL.

## Inputs
- None (fixed prompt in YAML).

## How it works
1. `ingest_release_notes` downloads release notes and creates embeddings.
2. `chat_with_rag` retrieves relevant chunks and generates answer.
3. `log_results` prints the grounded response.

## Step-by-step tutorial
1. Run `zoomcamp.2_chat_with_rag`.
2. Check that `ingest_release_notes` succeeded.
3. Inspect `chat_with_rag` output.
4. Compare with `1_chat_without_rag`.

## Expected outcome (what to verify)
- Response is more concrete and release-specific than baseline.
- Fewer hallucinations.

## Troubleshooting
- Check source URL availability if ingestion fails.
- Verify Gemini API secret.

## Next recommended flow
- Run `3_rag_with_websearch.yaml` to compare static vs live retrieval.
