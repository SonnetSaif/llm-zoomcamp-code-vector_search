# 7_conversational_agent_with_memory

> **Lesson reference:** [10-memory-and-state.md](../lessons/10-memory-and-state.md) | **YAML:** `7_conversational_agent_with_memory.yaml`

---

## Learning objectives

By completing this flow you will:
- Understand why stateless agents fail at multi-turn conversations.
- Know how `KestraKVStore` memory works and how `memoryId` scopes it.
- Run a three-turn conversation that demonstrates memory carry-over.
- Understand the relationship between memory, context window, and token costs.
- Know when memory is the right choice vs. re-ingesting context each run.

---

## Core concept — Stateless vs. stateful agents

Every flow you have run so far is **stateless**: each execution starts fresh with no knowledge of prior runs. This is fine for one-shot queries. For multi-turn conversations it breaks down immediately:

```
Run 1: "Tell me about Kestra's plugin system"
  → Agent answers. Output stored in task log. Memory: none.

Run 2 (stateless): "Give me an example of the type we discussed"
  → Agent has no idea what "the type" refers to. Answers generically.
  
Run 2 (with memory, same conversation_id): "Give me an example of the type we discussed"
  → Agent reads Run 1's exchange from KV Store.
  → Agent knows "the type" = IO plugin. Answers correctly.
```

### How `KestraKVStore` memory works

```
Execution N (conversation_id = "thread-demo")
┌─────────────────────────────────────────────────────────┐
│ 1. AIAgent reads KV Store key "thread-demo"             │
│    → gets full prior conversation history as JSON       │
│ 2. Prepends history to context window                   │
│ 3. Calls Gemini with: history + system message + prompt │
│ 4. Gets response                                        │
│ 5. Appends new [user: prompt, assistant: response]      │
│    to KV Store key "thread-demo"                        │
└─────────────────────────────────────────────────────────┘
```

Memory is stored as a JSON array of message objects. On each execution, the full array is read, injected into the prompt, extended with the new exchange, and written back.

### `memoryId` — thread isolation

`memoryId` is the KV Store key. Two executions share a thread if and only if their `memoryId` is identical:

```
conversation_id = "thread-a"  →  reads/writes KV key "thread-a"
conversation_id = "thread-b"  →  reads/writes KV key "thread-b"  ← isolated
```

This lets one flow serve multiple independent users or topics by simply varying the `conversation_id` input.

### Memory and the context window

Memory extends the *effective* context across execution boundaries, but it does not increase the model's context window limit. The full conversation history is injected on every run. As threads grow longer:
- **Token count grows** — and so does cost per execution
- **Risk of exceeding context limit** increases
- **Model attention may degrade** on very early messages in long threads

Practical limit: keep threads under ~20 exchanges for most models. Create a separate flow to prune stale KV keys when threads are no longer needed.

---

## Flow definition
- YAML: `7_conversational_agent_with_memory.yaml`
- Namespace / ID: `zoomcamp.7_conversational_agent_with_memory`

## Prerequisites
- `SECRET_GEMINI_API_KEY`
- `SECRET_TAVILY_API_KEY`

## Inputs

| Input | Default | Description |
|---|---|---|
| `user_message` | "Tell me about the latest Kestra features..." | The message for this turn |
| `conversation_id` | `kestra-assistant-thread-1` | Thread identifier — reuse to continue, change to start fresh |

---

## YAML walkthrough

```yaml
tasks:
  - id: conversational_agent
    type: io.kestra.plugin.ai.agent.AIAgent
    provider:
      type: io.kestra.plugin.ai.provider.GoogleGemini
      modelName: gemini-2.5-flash
      apiKey: "{{ secret('GEMINI_API_KEY') }}"
    memory:                                                  # (1)
      type: io.kestra.plugin.ai.memory.KestraKVStore
      memoryId: "{{ inputs.conversation_id }}"              # (2)
    systemMessage: |
      You are a knowledgeable Kestra assistant...
      Maintain conversation continuity: reference earlier messages
      in this thread when the user asks follow-up questions.  # (3)
    prompt: "{{ inputs.user_message }}"
    contentRetrievers:
      - type: io.kestra.plugin.ai.retriever.TavilyWebSearch
        apiKey: "{{ secret('TAVILY_API_KEY') }}"
        maxResults: 5                                        # (4)
```

**(1) `memory` block** — Adding this block to any `AIAgent` task enables persistence. Without it, the agent is stateless. With it, every execution reads and writes the conversation thread.

**(2) `memoryId: "{{ inputs.conversation_id }}"` — Dynamic thread key**. Because it's an expression, any caller can specify their own thread by passing a unique `conversation_id`. This is how you scale one flow to many parallel conversations.

**(3) Memory instruction in `systemMessage`** — The model needs to be told to use the prior context, not just that it exists. Without this instruction the model may answer each turn in isolation even when history is available in the window.

**(4) `maxResults: 5`** — Lower than Flow 5's 10, because memory already fills part of the context window. More retrieval results = more tokens consumed per run. Balance retrieval depth against conversation length.

---

## Data flow — across executions

```
Run 1 (conversation_id = "thread-demo")
    │
    ▼
KV Store "thread-demo" = [] (empty — first run)
    │
    ▼
[system message + user_message_1] → Gemini → response_1
    │
    ▼
KV Store "thread-demo" = [{user: msg1, assistant: response_1}]

Run 2 (same conversation_id = "thread-demo")
    │
    ▼
KV Store "thread-demo" = [{user: msg1, assistant: response_1}]  ← loaded
    │
    ▼
[system message + history + user_message_2] → Gemini → response_2
(Gemini sees msg1 and response_1 as prior context)
    │
    ▼
KV Store "thread-demo" = [{user: msg1, assistant: response_1},
                           {user: msg2, assistant: response_2}]
```

---

## Step-by-step tutorial — three-turn demo

Run the flow three times in sequence with the same `conversation_id`:

| Run | `conversation_id` | `user_message` | What to verify |
|---|---|---|---|
| 1 | `thread-demo` | "Tell me about the latest Kestra features and what makes them useful." | Agent answers with features found via Tavily |
| 2 | `thread-demo` | "Which of those features would help with scheduled pipelines?" | Agent references the specific features from Run 1 |
| 3 | `thread-demo` | "Can you summarise everything we discussed?" | Agent summarises both exchanges |
| 4 | `thread-demo-2` | "Which of those features would help with scheduled pipelines?" | Agent has no context — answers generically |

Run 4 with a different `conversation_id` is the control. Comparing Runs 2 and 4 makes the impact of memory concrete.

---

## Expected outcome

- Same `conversation_id`: each run's response references prior context naturally.
- New `conversation_id`: fresh thread with no carry-over.
- Token count grows with each successive run on the same thread (growing history).

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Agent does not reference prior context | `conversation_id` differs between runs (typo or whitespace) | Copy-paste the exact ID from Run 1 |
| Memory seems to reset unexpectedly | KV Store key was manually deleted | Check Kestra UI → KV Store namespace for the key |
| Token count growing too fast | Long threads accumulating | Create a maintenance flow to delete the KV key when thread is done |
| Tavily returning stale or irrelevant results | Low `maxResults` or topic too broad | Increase `maxResults` or narrow the prompt |
| Agent ignores system message continuity instruction | Short-form system message stripped by model | Rephrase: "Always acknowledge what was said earlier in this conversation before answering" |

---

## Key concepts

| Term | Definition |
|---|---|
| **Stateless** | Each execution starts fresh with no knowledge of prior runs |
| **Stateful** | Execution reads prior state, acts on it, and writes updated state |
| **`KestraKVStore` memory** | Kestra's built-in KV Store used as a conversation thread database |
| **`memoryId`** | The key under which a conversation thread is stored and retrieved |
| **Context window** | The maximum tokens an LLM can see in one call; memory history fills part of it |
| **Thread isolation** | Two executions with different `memoryId` values share no history |

---

## Try this

- After a 5-turn conversation, inspect the raw KV Store value in the Kestra UI (namespace → KV Store tab). What does the stored JSON look like?
- Start a second thread (`conversation_id = "thread-demo-parallel"`) and run it in parallel with `thread-demo`. Verify the two threads remain completely isolated.
- Intentionally use a very long `user_message` (paste a full article). Watch how token count spikes — this demonstrates why memory threads should be kept short.

---

## Next recommended flow
Run `8_faq_rag_pipeline.yaml` to see domain-specific RAG applied to a real course FAQ dataset — the same Python pipeline you worked with elsewhere in this repository, now orchestrated in Kestra.
