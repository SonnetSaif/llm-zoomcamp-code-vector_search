# 4_simple_agent

> **Lesson reference:** [06-agents.md](../lessons/06-agents.md) | **YAML:** `4_simple_agent.yaml`

---

## Learning objectives

By completing this flow you will:
- Understand the **agent loop** and how `AIAgent` automates it in Kestra.
- Know the difference between `systemMessage` (role/rules) and `prompt` (task/question).
- Use `pluginDefaults` to share provider configuration across multiple tasks.
- Read and interpret token usage output for cost estimation.
- Chain two agent tasks so the output of one feeds the input of the next.

---

## Core concept — What is an AI agent?

In Module 1 of LLM Zoomcamp you built an agentic loop by hand:

```python
while True:
    response = llm.call(messages)
    if response.has_tool_calls():
        results = execute_tools(response.tool_calls)
        messages.append(tool_results)
    else:
        return response.text   # final answer, no more tool calls
```

Kestra's `AIAgent` plugin encapsulates exactly this loop. You declare the *goal*, the *tools*, and the *behavior rules* — Kestra drives the loop, manages the conversation history, and surfaces the final answer as a task output.

### Traditional workflow vs. agent workflow

```yaml
# Traditional workflow — you define every step
tasks:
  - id: step1
    type: TranslateText
  - id: step2
    type: SummarizeText
  - id: step3
    type: CheckLength
```

```yaml
# Agent workflow — you define the outcome
tasks:
  - id: agent
    type: io.kestra.plugin.ai.agent.AIAgent
    prompt: "Translate and summarize this text, checking that the result is under 100 words"
    # The agent figures out the order and what to do if the check fails
```

The agent approach is more flexible but less deterministic. Use it when the exact sequence of steps isn't known in advance.

### `systemMessage` vs. `prompt`

| Property | Purpose | When to use |
|---|---|---|
| `systemMessage` | Sets the agent's *role*, *behavior rules*, and *output format* | Every agent; write it once |
| `prompt` | The specific *question or task* for this execution | Changes per run; can reference inputs |

Think of `systemMessage` as the job description and `prompt` as the work ticket.

---

## Flow definition
- YAML: `4_simple_agent.yaml`
- Namespace / ID: `zoomcamp.4_simple_agent`

## Prerequisites
- `SECRET_GEMINI_API_KEY`

## Inputs

| Input | Type | Options | Default | Purpose |
|---|---|---|---|---|
| `summary_length` | SELECT | `short`, `medium`, `long` | `medium` | Controls output verbosity |
| `language` | SELECT | `en`, `fr`, `de`, `es`, `it`, `pt`, `ja` | `en` | Target language for first summary |
| `text` | STRING | — | (Kestra description text) | Content to summarize |

---

## YAML walkthrough

### `pluginDefaults` — avoiding provider repetition

```yaml
pluginDefaults:
  - type: io.kestra.plugin.ai.agent.AIAgent    # (1)
    values:
      provider:
        type: io.kestra.plugin.ai.provider.GoogleGemini
        modelName: gemini-3.1-flash-lite       # (2)
        apiKey: "{{ secret('GEMINI_API_KEY') }}"
```

**(1)** `pluginDefaults` applies the given `values` to every task of the specified type in the flow. Both `multilingual_agent` and `english_brevity` inherit the provider block automatically — you write it once instead of twice.

**(2) `gemini-3.1-flash-lite`** — A lightweight, fast, cheap model suitable for summarization. For tool-using agents or complex reasoning tasks you would upgrade to `gemini-2.5-flash` or higher.

### Task 1 — `multilingual_agent`

```yaml
- id: multilingual_agent
  type: io.kestra.plugin.ai.agent.AIAgent
  systemMessage: |
    You are a precise technical assistant.
    Produce a {{ inputs.summary_length }} summary in {{ inputs.language }}.   # (3)
    Output format guidelines:
    - For 'short': 1-2 sentences
    - For 'medium': 2-5 sentences
    - For 'long': 1-3 paragraphs
  prompt: |
    Summarize the following content: {{ inputs.text }}                        # (4)
```

**(3) Dynamic `systemMessage`** — Kestra's expression language `{{ inputs.X }}` resolves at runtime. The agent's behavior adapts to each execution's inputs without code changes.

**(4)** `prompt` carries the data. `systemMessage` carries the rules. Keeping them separate makes the rules reusable across different prompts.

### Task 2 — `english_brevity`

```yaml
- id: english_brevity
  type: io.kestra.plugin.ai.agent.AIAgent
  prompt: |
    Generate exactly 1 sentence English summary of the following:
    "{{ outputs.multilingual_agent.textOutput }}"   # (5)
```

**(5) Output chaining** — `{{ outputs.multilingual_agent.textOutput }}` injects the previous task's result into this task's prompt. This is how you build multi-step agent pipelines: each task reads the prior task's `textOutput` and refines or transforms it.

### Task 3 — `log_token_usage`

```yaml
- id: log_token_usage
  type: io.kestra.plugin.core.log.Log
  message: |
    Multilingual Agent:
    - Input tokens:  {{ outputs.multilingual_agent.tokenUsage.inputTokenCount }}
    - Output tokens: {{ outputs.multilingual_agent.tokenUsage.outputTokenCount }}
    - Total tokens:  {{ outputs.multilingual_agent.tokenUsage.totalTokenCount }}
```

Every `AIAgent` and `ChatCompletion` task exposes a `tokenUsage` output. The three fields map directly to API billing:
- **Input tokens** — prompt + context + system message (usually the largest cost driver)
- **Output tokens** — generated response (typically 2–10× more expensive per token than input)
- **Total** — sum; multiply by your provider's rate to estimate cost

---

## Data flow

```
inputs.text
    │
    ▼ (multilingual_agent)
systemMessage [role + length + language rules]
+ prompt [inputs.text]
    → Gemini gemini-3.1-flash-lite
    → textOutput: summary in target language
    │
    ▼ (english_brevity)
prompt ["1 sentence summary of: <multilingual output>"]
    → Gemini gemini-3.1-flash-lite
    → textOutput: 1-sentence English distillation
    │
    ▼ (log_token_usage)
tokenUsage from both tasks printed to execution log
```

---

## Step-by-step tutorial

1. Run once with `summary_length=short`, `language=en`. Read both outputs in the task logs.
2. Run again with `summary_length=long`, `language=ja`. Compare how dramatically the first summary changes while the second always produces one English sentence.
3. Check `log_token_usage` — notice that `long` language generates significantly more tokens than `short`.
4. Edit `pluginDefaults` to use `gemini-2.5-flash` and re-run. Compare output quality and token counts.

---

## Expected outcome

- `multilingual_agent` output respects selected length and language.
- `english_brevity` output is always exactly one English sentence regardless of language chosen.
- Token counts are logged for both tasks.
- Cost difference between `short` and `long` is visible in `outputTokenCount`.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Language not respected | Model override from training data for short texts | Add explicit reinforcement: "You MUST respond in [language] only" |
| Length constraint ignored | Model not following system message rules | Restructure system message to put format rules first |
| `english_brevity` output is multiple sentences | Model ignoring "exactly 1 sentence" | Add: "If you generate more than one sentence, truncate to the first." |
| Token count is 0 | Old output cached from previous run | Force a fresh run by changing inputs slightly |

---

## Key concepts

| Term | Definition |
|---|---|
| **Agent loop** | The while-loop: call LLM → execute tool calls → call LLM again → repeat until no tool calls |
| **systemMessage** | Instructions that define the agent's persona, rules, and output format; sent before every user message |
| **pluginDefaults** | YAML-level default values applied to all tasks of a given type within the flow |
| **tokenUsage** | The per-task output object containing `inputTokenCount`, `outputTokenCount`, `totalTokenCount` |
| **Output chaining** | Using `{{ outputs.<task-id>.textOutput }}` to pass one task's result to the next |

---

## Try this

- Intentionally give the agent a non-text input (a URL or a list of numbers). Does the system message guard (`"If the input is non-text, return a one-sentence explanation"`) fire?
- Add a third agent task that translates the English one-sentence summary into a third language not covered by `multilingual_agent`.
- Replace `gemini-3.1-flash-lite` in `pluginDefaults` with `gemini-2.5-flash`. Measure token cost and quality difference for the same input.

---

## Next recommended flow
Run `5_web_research_agent.yaml` to see an agent that autonomously decides *which tools to call* to achieve a goal — the key step from structured chaining to true autonomy.
