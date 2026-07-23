# 4_simple_agent

## Overview
Introductory agent flow for controlled summarization, task chaining, and token tracking.

## Why this flow matters
It teaches core agent orchestration patterns before moving to tool-using or multi-agent designs.

## Flow definition
- YAML: `4_simple_agent.yaml`
- Namespace/ID: `zoomcamp.4_simple_agent`

## Prerequisites
- `SECRET_GEMINI_API_KEY`

## Inputs
- `summary_length`: `short | medium | long`
- `language`: `en | fr | de | es | it | pt | ja`
- `text`: source content to summarize

## How it works
1. `multilingual_agent` creates summary based on selected length/language.
2. `english_brevity` compresses that output into one English sentence.
3. `log_token_usage` logs token usage for both agent calls.

## Step-by-step tutorial
1. Run once with `summary_length=short`, `language=en`.
2. Run again with `summary_length=long`, `language=ja`.
3. Compare output length/quality and token counts.

## Expected outcome (what to verify)
- Output respects selected length and language.
- Chained task output is coherent.
- Token usage appears for both agent tasks.

## Troubleshooting
- If language/length behavior is inconsistent, inspect system prompt rules.
- Verify Gemini key if execution fails.

## Next recommended flow
- Run `5_web_research_agent.yaml` to see agent autonomy with external tools.
