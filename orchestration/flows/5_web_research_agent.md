# 5_web_research_agent

## Overview
Autonomous research flow where the agent chooses search strategy, synthesizes findings, and writes a report file.

## Why this flow matters
Demonstrates goal-based agent behavior: you define outcome, the agent determines steps.

## Flow definition
- YAML: `5_web_research_agent.yaml`
- Namespace/ID: `zoomcamp.5_web_research_agent`

## Prerequisites
- `SECRET_GEMINI_API_KEY`
- `SECRET_TAVILY_API_KEY`
- Docker support for `mcp/filesystem` tool usage

## Inputs
- `research_topic`: topic and scope for research

## How it works
1. `research_agent` performs Tavily-based iterative research.
2. Agent writes `research_report.md` via filesystem MCP tool.
3. `log_report` prints output file path and token usage.

## Step-by-step tutorial
1. Run `zoomcamp.5_web_research_agent` with default topic.
2. Inspect `research_agent` execution.
3. Open generated `research_report.md` from output files.
4. Validate report structure and sources.

## Expected outcome (what to verify)
- Report file exists and is non-empty.
- Content includes summary, findings, analysis, and source links.

## Troubleshooting
- Missing Tavily key or Docker/MCP support can break report generation.
- Sparse topics may return thin source coverage.

## Next recommended flow
- Run `6_multi_agent_research.yaml` to see explicit agent delegation architecture.
