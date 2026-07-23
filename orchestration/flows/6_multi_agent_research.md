# 6_multi_agent_research

> **Lesson reference:** [07-multi-agent.md](../lessons/07-multi-agent.md) | **YAML:** `6_multi_agent_research.yaml`

---

## Learning objectives

By completing this flow you will:
- Understand why multi-agent systems offer better separation of concerns than a single large agent.
- Know how to wire one `AIAgent` as a **tool** inside another `AIAgent`.
- Enforce structured JSON output from an LLM and parse it downstream with `{{ json() }}`.
- Use `pluginDefaults` to share a provider across nested agent configurations.
- Reason about token costs in a system where one agent call can trigger another.

---

## Core concept — Multi-agent systems and delegation

A single large agent doing everything — searching the web, synthesising data, structuring output — is hard to debug and expensive to iterate on. Multi-agent systems solve this with **separation of concerns**: each agent has a focused responsibility, and agents communicate through well-defined interfaces.

In Flow 5, one agent did everything. Here you have two:

| Agent | Role | Tools | Output |
|---|---|---|---|
| **Research Agent** (nested tool) | Data gathering | `TavilyWebSearch` | Raw factual text about the company |
| **Analyst Agent** (main task) | Synthesis and structure | Research Agent (as a tool) | Structured JSON report |

The Analyst Agent treats the Research Agent **exactly like a web search tool** — it calls it when it needs data, receives text back, and continues reasoning. The Analyst never touches Tavily directly; the Research Agent never touches the output schema.

### Why use `AIAgent` as a tool?

- **Testability** — you can run the Research Agent in isolation and verify its output independently.
- **Cost control** — a cheap model can do raw retrieval; an expensive model handles synthesis. Each uses its own provider configuration.
- **Reusability** — the Research Agent can be reused as a tool in other flows (competitor tracking, news monitoring, etc.) without modification.
- **Debuggability** — if the JSON output is wrong, you can isolate whether the problem is in retrieval (Research Agent) or synthesis (Analyst Agent).

### Enforcing JSON output

LLMs tend to wrap JSON in markdown code fences (` ```json `) or add preamble text. This breaks downstream `{{ json() }}` parsing. The pattern used here guards against this in two places:

1. **System message**: `"Output must be a valid JSON object only — without markdown, code fences, or commentary. Never include ```json or ``` markers."`
2. **Prompt**: Provides the exact JSON skeleton with field names and types written out.

Both guards together are more reliable than either alone.

---

## Flow definition
- YAML: `6_multi_agent_research.yaml`
- Namespace / ID: `zoomcamp.6_multi_agent_research`

## Prerequisites
- `SECRET_GEMINI_API_KEY`
- `SECRET_TAVILY_API_KEY`

## Inputs

| Input | Default | Description |
|---|---|---|
| `company_name` | `kestra.io` | Company domain or name to research |

---

## YAML walkthrough

### `pluginDefaults` — provider shared across nested agents

```yaml
pluginDefaults:
  - type: io.kestra.plugin.ai.provider.GoogleGemini   # (1)
    values:
      modelName: gemini-2.5-flash
      apiKey: "{{ secret('GEMINI_API_KEY') }}"
```

**(1)** `pluginDefaults` on the *provider type* (not the task type) propagates the model and key to every Gemini provider reference in the flow, including inside the nested `AIAgent` tool. This means neither the outer nor inner agent needs to repeat the provider configuration.

### Main agent — `analysis`

```yaml
- id: analysis
  type: io.kestra.plugin.ai.agent.AIAgent
  provider:
    type: io.kestra.plugin.ai.provider.GoogleGemini   # resolves from pluginDefaults
  systemMessage: |
    You are a senior market intelligence analyst...
    Output must be a **valid JSON object only** — without markdown or commentary.
  prompt: |
    Research the company "{{ inputs.company_name }}" using the research tool.
    Then summarize your findings in this JSON structure:
    {
      "company": "string",
      "summary": "string",
      "recent_news": [ { "title": ..., "date": ..., "description": ... } ],
      "competitors": ["string"]
    }
  tools:
    - type: io.kestra.plugin.ai.tool.AIAgent           # (2)
      description: Web research and data gathering     # (3)
      systemMessage: |
        You are a research assistant that searches the web for factual
        and up-to-date company information as of date {{ now() }}.   # (4)
        Return concise factual summaries — no markdown, no formatting.
      provider:
        type: io.kestra.plugin.ai.provider.GoogleGemini
      contentRetrievers:
        - type: io.kestra.plugin.ai.retriever.TavilyWebSearch
          apiKey: "{{ secret('TAVILY_API_KEY') }}"
```

**(2) `AIAgent` as a tool** — The nested agent is declared inline under `tools`. When the main Analyst Agent decides to call the research tool, Kestra instantiates this inner agent, runs its full loop (including Tavily searches), and returns its `textOutput` to the outer agent as a tool result.

**(3) `description`** — The tool description is shown to the outer LLM so it knows when to invoke this tool. Write it as a one-line capability statement: "what does this tool do?"

**(4) `{{ now() }}`** — Injects the current timestamp into the inner agent's system message so it can ground its searches to the current date.

### Output parsing — `parse_results`

```yaml
- id: parse_results
  type: io.kestra.plugin.core.log.Log
  message: |
    Company: {{ json(outputs.analysis.textOutput).company }}       # (5)
    {% for news in json(outputs.analysis.textOutput).recent_news %} # (6)
    - {{ news.title }} ({{ news.date }})
    {% endfor %}
```

**(5) `json()` function** — Kestra's built-in template function that parses a JSON string into an object. `outputs.analysis.textOutput` holds the raw JSON string; `json(...)` makes its fields addressable with dot notation.

**(6) Pebble `{% for %}` loop** — Kestra uses [Pebble templating](https://pebbletemplates.io/), which supports full Jinja-style control flow. This iterates over the `recent_news` array in the parsed JSON.

---

## Data flow

```
inputs.company_name: "kestra.io"
    │
    ▼ (analysis agent loop begins)
Analyst: "I need to research kestra.io — I'll call the research tool"
    │
    ▼ (Research Agent invoked as tool)
    Research Agent loop:
      → TavilyWebSearch("kestra.io company overview")
      → TavilyWebSearch("kestra.io recent news 2025")
      → synthesize → return text summary
    │
    ▼ (back in Analyst loop)
Analyst: received research results
→ structures into JSON schema
→ returns textOutput: {"company": ..., "summary": ..., ...}
    │
    ▼ (parse_results)
json(outputs.analysis.textOutput) → field access → formatted log
```

---

## Step-by-step tutorial

1. Run `zoomcamp.6_multi_agent_research` with `company_name=kestra.io`.
2. Open the `analysis` task → **Logs** to watch both agents' reasoning unfold.
3. In `analysis` → **Outputs** → `textOutput`: verify it is raw JSON (no code fences, no preamble).
4. Open `parse_results` → **Logs** to see the formatted report with company, news, and competitors.
5. Re-run with `company_name=apache.org` and compare the JSON structure — it should be identical, only the values differ.

---

## Expected outcome

- `analysis.textOutput` is valid JSON that can be parsed without errors.
- At least two `recent_news` entries and two `competitors` are present.
- `parse_results` log shows all fields correctly extracted.
- Token count in `analysis.tokenUsage` is higher than Flow 5 (two nested LLM calls).

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `json()` throws parse error | Model added markdown fences or preamble | Reinforce both system message and prompt JSON guards; try a temperature of 0 if provider supports it |
| `recent_news` is empty array | Research Agent returned no current news | Add to prompt: "Always include at least two recent_news items, using industry knowledge if web results are sparse" |
| `competitors` missing or empty | Same | Same fix as above |
| Inner agent never called | Outer agent answered from training data | Add explicit instruction: "You MUST use the research tool before writing your JSON output" |
| Rate limit errors | Two concurrent Gemini calls | Add delays or switch one agent to a different provider/model |

---

## Key concepts

| Term | Definition |
|---|---|
| **Multi-agent system** | A design where multiple specialized agents collaborate, each handling a distinct responsibility |
| **Nested tool agent** | An `AIAgent` declared inline under another agent's `tools` list; the outer agent calls it like any other function |
| **Structured output** | Constraining the LLM to return a specific format (JSON) rather than free text, enabling downstream parsing |
| **`json()` function** | Kestra template function that parses a JSON string into a navigable object |
| **Separation of concerns** | Each agent handles one responsibility; problems are isolated to a specific agent rather than a monolithic agent |

---

## Try this

- Add a `configuration: logRequests: true` block to the inner Research Agent tool. Re-run and inspect the raw Tavily queries it generates.
- Add a third agent tool that summarizes competitor strengths (calls the research agent twice — once per top competitor). Observe how token costs multiply.
- Swap the inner Research Agent's model to `gemini-3.1-flash-lite` (cheaper) while keeping the Analyst on `gemini-2.5-flash`. Do the results degrade?

---

## Next recommended flow
Run `9_llm_evaluation.yaml` to learn how to systematically score the quality of agent outputs rather than relying on manual review.
