# 1_chat_without_rag

## Overview
Baseline flow that asks an LLM about Kestra 1.1 without retrieval.

## Why this flow matters
It gives you a control sample so you can clearly see the quality gap between plain prompting and RAG.

## Flow definition
- YAML: `1_chat_without_rag.yaml`
- Namespace/ID: `zoomcamp.1_chat_without_rag`

## Prerequisites
- `SECRET_GEMINI_API_KEY`

## Inputs
- None (fixed user prompt in the YAML task).

## How it works
1. `chat_without_rag` sends the question directly to Gemini.
2. `log_results` prints the response and guidance for comparison.

## Step-by-step tutorial
1. Run `zoomcamp.1_chat_without_rag`.
2. Open task `chat_without_rag` output.
3. Open task `log_results`.
4. Note how specific (or generic) the answer is.

## Expected outcome (what to verify)
- Response may be plausible but version details can be vague or wrong.
- No evidence of source grounding.

## Troubleshooting
- If flow fails immediately, verify `SECRET_GEMINI_API_KEY`.

## Next recommended flow
- Run `2_chat_with_rag.yaml` and compare side by side.
