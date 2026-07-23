# 7_conversational_agent_with_memory

## Overview
Conversational assistant with persistent memory per thread plus live web retrieval.

## Why this flow matters
Adds continuity across executions so follow-up prompts do not require repeating context.

## Flow definition
- YAML: `7_conversational_agent_with_memory.yaml`
- Namespace/ID: `zoomcamp.7_conversational_agent_with_memory`

## Prerequisites
- `SECRET_GEMINI_API_KEY`
- `SECRET_TAVILY_API_KEY`

## Inputs
- `user_message`: current message
- `conversation_id`: memory thread key

## How it works
1. `conversational_agent` loads/stores memory via `KestraKVStore` using `conversation_id`.
2. Same agent can retrieve fresh web context through Tavily.
3. `log_response` prints the turn details and token usage.

## Step-by-step tutorial
1. Run once with default `conversation_id`.
2. Run again with same `conversation_id` and a follow-up question.
3. Run a third time with a new `conversation_id` and same follow-up.
4. Compare continuity behavior between runs.

## Expected outcome (what to verify)
- Same `conversation_id`: agent references prior context.
- New `conversation_id`: fresh thread with no carry-over context.

## Troubleshooting
- If memory appears missing, verify `conversation_id` is identical across runs.
- Verify Gemini/Tavily keys if execution fails.

## Next recommended flow
- Run `8_faq_rag_pipeline.yaml` for domain-grounded Q&A with explicit baseline comparison.
