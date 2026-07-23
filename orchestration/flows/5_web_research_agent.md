# 5_web_research_agent

> **Lesson reference:** [06-agents.md](../lessons/06-agents.md) | **YAML:** `5_web_research_agent.yaml`

---

## Learning objectives

By completing this flow you will:
- Understand the distinction between **goal-based** and **step-based** workflow design.
- Know the difference between `contentRetrievers` (read-only retrieval) and `tools` (read-write actions).
- Understand how Kestra uses MCP (Model Context Protocol) to give agents filesystem access via Docker.
- Observe the agent's autonomous multi-step decision loop in execution logs.
- Read and use `outputFiles` to retrieve files the agent created.

---

## Core concept — Goal-based agent autonomy

In Flow 4, you specified *exactly what to do* in each task. In this flow, you specify only the *desired outcome* and let the agent decide the steps.

You write:
> "Research the latest trends in data orchestration. Include popular tools, emerging patterns, key challenges, and recent innovations."

The agent decides:
- How many web searches to perform and with what queries
- Whether the initial results are sufficient or more searches are needed
- How to structure the report
- When to declare the task complete

This is the shift from **orchestrating steps** to **orchestrating goals**.

### `contentRetrievers` vs. `tools`

These two YAML properties serve different purposes:

| Property | Direction | Side effects | Example |
|---|---|---|---|
| `contentRetrievers` | Read-only — injects text as context | None | `TavilyWebSearch`, `KestraKVStore` |
| `tools` | Read-write — agent can call them as functions | Yes (creates files, runs code, calls APIs) | `DockerMcpClient` (filesystem), `CodeExecution`, `KestraFlow` |

A `contentRetriever` is automatically called before each LLM invocation to provide background context. A `tool` is only called when the agent decides to invoke it by name.

### MCP and `DockerMcpClient`

[MCP (Model Context Protocol)](https://modelcontextprotocol.io/) is an open protocol for exposing tools to LLMs. Kestra's `DockerMcpClient` spins up a Docker container that exposes MCP tools over stdio, lets the agent call them, then tears the container down.

The `mcp/filesystem` image exposes standard filesystem operations: `read_file`, `write_file`, `list_directory`, etc. The agent calls `write_file` with path `/tmp/research_report.md` and the report contents — the file appears in the task's working directory and is collected by `outputFiles`.

```yaml
tools:
  - type: io.kestra.plugin.ai.tool.DockerMcpClient
    image: mcp/filesystem          # Docker image implementing MCP
    command: ["/tmp"]              # Root directory exposed to the agent
    binds: ["{{workingDir}}:/tmp"] # Maps Kestra's working dir to /tmp in container
```

`{{workingDir}}` is a Kestra built-in variable resolving to the task's working directory. Files written there are accessible to `outputFiles`.

---

## Flow definition
- YAML: `5_web_research_agent.yaml`
- Namespace / ID: `zoomcamp.5_web_research_agent`

## Prerequisites
- `SECRET_GEMINI_API_KEY`
- `SECRET_TAVILY_API_KEY`
- Docker available (for the `DockerMcpClient` filesystem tool)

## Inputs

| Input | Default | Description |
|---|---|---|
| `research_topic` | "Research the latest trends in data orchestration..." | Free-form goal description |

---

## YAML walkthrough

```yaml
tasks:
  - id: research_agent
    type: io.kestra.plugin.ai.agent.AIAgent
    provider:
      type: io.kestra.plugin.ai.provider.GoogleGemini
      apiKey: "{{ secret('GEMINI_API_KEY') }}"
      modelName: gemini-2.5-flash           # (1)
    prompt: "{{ inputs.research_topic }}"   # (2)
    systemMessage: |
      You are a thorough research assistant. Follow this process:
      1. Use the TavilyWebSearch content retriever to gather information.
         Search multiple times if needed...  # (3)
      4. Save the final report as 'research_report.md' in /tmp  # (4)
    contentRetrievers:
      - type: io.kestra.plugin.ai.retriever.TavilyWebSearch
        apiKey: "{{ secret('TAVILY_API_KEY') }}"
        maxResults: 10                       # (5)
    tools:
      - type: io.kestra.plugin.ai.tool.DockerMcpClient
        image: mcp/filesystem
        command: ["/tmp"]
        binds: ["{{workingDir}}:/tmp"]
    outputFiles:
      - research_report.md                   # (6)
```

**(1) `gemini-2.5-flash`** — Upgraded from Flow 4's `gemini-3.1-flash-lite` because this agent needs stronger reasoning to plan multiple searches, evaluate sufficiency, and write a structured report.

**(2) Dynamic prompt from input** — The research goal is entirely driven by `inputs.research_topic`, making this flow reusable for any research question without YAML edits.

**(3) System message as instructions** — The system message here serves as a *process specification*: it tells the agent what steps to follow, what quality bar to meet, and what format to produce. Without explicit structure in the system message, agent output quality is unpredictable.

**(4) File output instruction** — The agent must be told explicitly in the system message to use the filesystem tool and where to save the file. Without this instruction the agent may produce the report as text output but never write the file.

**(5) `maxResults: 10`** — Tells Tavily to return up to 10 search results per query. More results = richer context = better synthesis, but also higher token consumption. 10 is a good balance for research tasks.

**(6) `outputFiles`** — Lists files the task should collect from `{{workingDir}}` after execution. These become downloadable from the task's Outputs tab in the Kestra UI.

---

## Data flow — the agent loop in detail

```
inputs.research_topic
    │
    ▼ (research_agent loop begins)
Iteration 1:
  system message + prompt → Gemini
  Gemini: "I'll search for [query 1]"
  → TavilyWebSearch("data orchestration trends 2024") → 10 results injected
  Gemini: "I need more on [sub-topic], I'll search again"

Iteration 2:
  system message + prior exchange + prompt → Gemini
  Gemini: "I'll search for [query 2]"
  → TavilyWebSearch("AI-driven workflow automation") → 10 results
  Gemini: "I have enough. I'll write the report now."

Iteration 3:
  Gemini: calls write_file("/tmp/research_report.md", <report content>)
  → DockerMcpClient writes file to workingDir
  Gemini: "Report saved. Task complete."
  → loop ends, textOutput = final message

outputFiles collector → research_report.md attached to task output
    │
    ▼ (log_report)
URI of report file + token usage printed to log
```

---

## Step-by-step tutorial

1. Run `zoomcamp.5_web_research_agent` with the default `research_topic`.
2. Watch the execution unfold in the **Gantt** or **Logs** view — you will see multiple search and reasoning iterations.
3. Open `research_agent` → **Outputs** → click `research_report.md` to download and read the generated report.
4. Check `tokenUsage.totalTokenCount` — multi-search agents consume far more tokens than single-call tasks.
5. Re-run with a narrow `research_topic` (e.g., `"Recent benchmarks comparing Apache Airflow vs Kestra"`) and compare structure and depth.

---

## Expected outcome

- `research_report.md` exists, is non-empty, and contains all four sections: Executive Summary, Key Findings, Detailed Analysis, Sources.
- Sources include actual URLs found by Tavily.
- Token count is higher than previous flows (often 5,000–20,000 tokens) because of iterative search loops.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `research_report.md` missing from outputs | Agent produced text but didn't call `write_file` | Reinforce in system message: "You MUST save the report using the filesystem tool before finishing" |
| Agent loops indefinitely or hits Gemini rate limit | Too many search iterations | Add: "Perform at most 3 searches total, then synthesize what you have" |
| Docker pull error on `mcp/filesystem` | Docker not available or image not pulled | Run `docker pull mcp/filesystem` beforehand; ensure Docker socket is accessible to Kestra |
| Report has no source URLs | Agent hallucinated without searching | Check `configuration: logRequests: true` to see if Tavily was actually called |
| Empty `outputFiles` | File written to wrong path in container | Ensure agent writes to `/tmp/research_report.md` (not a subdirectory) |

---

## Key concepts

| Term | Definition |
|---|---|
| **Goal-based agent** | An agent given an outcome to achieve rather than a sequence of steps to follow |
| **contentRetriever** | Read-only context source called automatically before each LLM invocation |
| **tool** | A callable function the agent invokes by name when it decides to act |
| **MCP (Model Context Protocol)** | Open protocol for exposing typed tool interfaces to LLMs |
| **DockerMcpClient** | Kestra plugin that runs an MCP server inside a Docker container and bridges its tools to the agent |
| **outputFiles** | YAML property listing filenames to collect from the task's working directory after execution |

---

## Try this

- Add `configuration: logRequests: true` under `research_agent` to see the raw Tavily queries the agent generates. Do they match what you'd search manually?
- Constrain the agent with: "Perform exactly 2 searches, then write the report regardless of coverage." Observe how the report quality changes.
- Replace `mcp/filesystem` with a custom MCP server image that writes to S3 or sends the report via webhook.

---

## Next recommended flow
Run `6_multi_agent_research.yaml` to see how the single autonomous agent scales into a two-agent system where a main analyst delegates research to a specialized sub-agent.
