# 3_rag_with_websearch

## Overview
Single-task RAG flow that retrieves live web context using Tavily at query time.

## Why this flow matters
Useful for time-sensitive questions where pre-ingested documents may be outdated.

## Flow definition
- YAML: `3_rag_with_websearch.yaml`
- Namespace/ID: `zoomcamp.3_rag_with_websearch`

## Prerequisites
- `SECRET_OPENAI_API_KEY`
- `SECRET_TAVILY_API_KEY`

## Inputs
- None (fixed prompt in YAML).

## How it works
1. `chat_with_rag_and_websearch_content_retriever` performs Tavily search.
2. Retrieved snippets are passed to OpenAI for final answer generation.

## Step-by-step tutorial
1. Run `zoomcamp.3_rag_with_websearch`.
2. Review the output for "latest release" details.
3. Re-run later and compare freshness across runs.

## Expected outcome (what to verify)
- Answer reflects recent web information.
- Output can vary with changing web results.

## Troubleshooting
- Verify both API keys if task fails.
- If results are weak, Tavily query coverage may be limited at that moment.

## Next recommended flow
- Run `7_conversational_agent_with_memory.yaml` to add conversation state on top of retrieval.
