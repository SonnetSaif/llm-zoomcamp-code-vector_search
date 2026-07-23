# 6_multi_agent_research

## Overview
Multi-agent flow: a main analyst agent delegates web research to a specialized nested agent tool.

## Why this flow matters
Shows separation of concerns: one agent controls structure, another focuses on data gathering.

## Flow definition
- YAML: `6_multi_agent_research.yaml`
- Namespace/ID: `zoomcamp.6_multi_agent_research`

## Prerequisites
- `SECRET_GEMINI_API_KEY`
- `SECRET_TAVILY_API_KEY`

## Inputs
- `company_name`: company/domain to analyze

## How it works
1. `analysis` (main agent) receives strict JSON output schema.
2. Nested `AIAgent` tool performs Tavily research when called.
3. `parse_results` logs parsed report fields from JSON output.

## Step-by-step tutorial
1. Run `zoomcamp.6_multi_agent_research` with `kestra.io`.
2. Re-run with a second company.
3. Validate `analysis.textOutput` is valid JSON.
4. Inspect summary, recent news, and competitors in logs.

## Expected outcome (what to verify)
- Output is machine-readable JSON without markdown fences.
- At least two `recent_news` items and two `competitors` entries are present.

## Troubleshooting
- If JSON parsing fails, inspect model output format constraints.
- Verify Tavily and Gemini API secrets.

## Next recommended flow
- Run `9_llm_evaluation.yaml` to score answer quality systematically.
