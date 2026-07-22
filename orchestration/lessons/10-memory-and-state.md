# Memory and State

Up to this point all flows have been stateless — each execution is independent, and the agent has no recollection of prior runs. For one-shot queries that's fine. But for multi-turn conversations, debugging workflows, or iterative research, you need the agent to remember what it already said.

Kestra solves this with the `memory` property on `AIAgent` tasks. Memory is stored in the Kestra KV Store, persisted between executions, and scoped to a `memoryId` you control.

> Note: The flow in this lesson uses `{{ secret('GEMINI_API_KEY') }}` and `{{ secret('TAVILY_API_KEY') }}`. Make sure you've completed the [setup instructions](03-setup.md) before running it.

## How Memory Works

```
Execution 1                 Execution 2
───────────                 ───────────
User: "Tell me about        User: "What did you just
Kestra 1.1"                 tell me about?"
       │                           │
       ▼                           ▼
  AIAgent ──writes──►  KV Store  ──reads──► AIAgent
  (no prior memory)    [thread-1]           (sees Exec 1)
       │                                        │
       ▼                                        ▼
  Response A                             Response B
  (answers fresh)                        (refers to A)
```

Memory is keyed by `memoryId`. Two executions with the same `memoryId` share a conversation thread. Two executions with different IDs are completely isolated.

## Anatomy of a Stateful Agent

```yaml
tasks:
  - id: agent
    type: io.kestra.plugin.ai.agent.AIAgent
    provider:
      type: io.kestra.plugin.ai.provider.GoogleGemini
      modelName: gemini-2.5-flash
      apiKey: "{{ secret('GEMINI_API_KEY') }}"

    # Scopes memory to a named thread.
    # Use an input or dynamic expression to support multiple users.
    memory:
      type: io.kestra.plugin.ai.memory.KestraKVStore
      memoryId: "{{ inputs.conversation_id }}"

    systemMessage: |
      You are a helpful assistant. Reference earlier messages
      in this conversation when the user asks follow-up questions.

    prompt: "{{ inputs.user_message }}"
```

## Example: Conversational Agent with Web Search

Flow: [`7_conversational_agent_with_memory.yaml`](../flows/7_conversational_agent_with_memory.yaml)

This flow combines persistent memory with live web search:

1. The user sends a message and a `conversation_id`
2. The agent searches the web for current information if needed
3. Its response is written to the KV Store under that `conversation_id`
4. On the next run with the same `conversation_id`, the full prior exchange is injected into the prompt automatically

Try this sequence:

| Run | conversation_id | user_message |
|-----|----------------|--------------|
| 1 | `thread-demo` | "Tell me about the latest Kestra features." |
| 2 | `thread-demo` | "Which of those features would help with scheduled pipelines?" |
| 3 | `thread-demo` | "Can you summarise everything we discussed?" |

On Run 2, the agent will refer back to the features it listed in Run 1. On Run 3, it will summarise the entire thread — without the user having to repeat anything.

Now change `conversation_id` to `thread-demo-2` and ask Run 2's question directly. The agent will have no context and will answer generically — demonstrating exactly what memory adds.

## When to Use Memory

Use memory when:

- Building conversational interfaces (chatbots, Q&A assistants, interactive research)
- Debugging multi-step agent decisions across runs
- Letting an agent accumulate findings over several scheduled executions

Skip memory when:

- Each execution is independent (ETL jobs, one-shot analysis)
- You want deterministic, reproducible outputs
- Cost matters and conversation history is long (memory injects all prior turns)

## Memory vs. Context Window

Memory extends the *effective* context of your agent across execution boundaries — but it still fills your model's context window. Long threads will eventually hit token limits or become expensive.

Practical tips:

1. Use descriptive `memoryId` values that reflect the thread purpose (e.g. `research-kestra-2025-q2`)
2. Create a separate flow that deletes stale KV keys when threads are no longer needed
3. Use shorter `systemMessage` instructions so more of the window is available for memory

[← Next Steps](09-next-steps.md) | [Evaluation →](11-evaluation.md)
