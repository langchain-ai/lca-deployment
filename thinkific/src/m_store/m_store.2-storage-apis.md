# Accessing Storage

Let's try to use some of these memories. In this lesson, you will use the LangGraph SDK to read and write the store and then read data from the Checkpointer. You'll use the `deep_tutor` deployment you already have running.

The local filesystem is the third storage type. It is inside the deployment container and cannot be reached from the SDK client, but is being used to provide instructions to the agent in the skills and AGENT.md files.

By the end, you will have:
- Written a student profile to the Store and read it back
- Sent a message to the agent and read the resulting thread state from the Checkpointer

---

## Setup

These scripts connect to `deep_tutor` running locally. Start it if it is not already running:

```bash
# python/deep_tutor
cd python/deep_tutor
uv run langgraph dev
```

In a second terminal, install dependencies for this exercise:

```bash
# python/m_store/l2
cd python/m_store/l2
uv sync
```

Copy `.env.example` to `.env` and add your LangSmith API key.

---

## Part 1: The Store

**File:** `store.py`

This script will access the store. The code and results are described in the section below. 

```bash
# python/m_store/l2
uv run python store.py
```

### Writing a profile

Each student's data is stored under their own namespace — a tuple that scopes the data to that student. The namespace follows the same `first_last` pattern the `deep_tutor` UI sets as `store_namespace`.

```python
# python/m_store/l2/store.py
NAMESPACE = ("john_doe",)

await client.store.put_item(NAMESPACE, key="profile", value={
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "goals": "Understand how LangGraph deployments work end to end.",
})
print(f"Wrote profile to Store under namespace {NAMESPACE!r}")
```

```text
Wrote profile to Store under namespace ('john_doe',)
```

`put_item` is an upsert — writing the same namespace + key again overwrites the previous value.

### Reading it back

```python
# python/m_store/l2/store.py
item = await client.store.get_item(NAMESPACE, key="profile")
for k, v in item["value"].items():
    print(f"  {k}: {v}")
```

```text
  first_name: John
  last_name: Doe
  email: john@example.com
  goals: Understand how LangGraph deployments work end to end.
```

### Listing all items in a namespace

```python
# python/m_store/l2/store.py
result = await client.store.search_items(NAMESPACE)
for entry in result["items"]:
    print(f"  key={entry['key']}  value={entry['value']}")
```

```text
  key=profile  value={'first_name': 'John', 'last_name': 'Doe', 'email': 'john@example.com', 'goals': 'Understand how LangGraph deployments work end to end.'}
```

`search_items` returns every item stored under the namespace prefix — useful for listing all data belonging to a student.

---

## Part 2: The Checkpointer

**File:** `checkpointer.py`

The checkpointer records the state at the end of each node in the execution. You generally won't need to view or manipulate this, but for completeness, the code below shows how to access the checkpointer.

```bash
# python/m_store/l2
uv run python checkpointer.py
```

### Reading thread state

After the run completes, `get_state` returns the last checkpoint — the full state as it was after the final node, including the complete message history.

```python
# python/m_store/l2/checkpointer.py
state = await client.threads.get_state(thread["thread_id"])
messages = state["values"].get("messages", [])
print(f"Checkpointer — thread has {len(messages)} messages:")
for msg in messages:
    role = msg.get("type", msg.get("role", "?"))
    content = msg.get("content", "")
    print(f"  [{role}]: {str(content)[:80]}")
```

```text
Checkpointer — thread has 7 messages:
  [human]: What is the checkpointer in LangGraph?
  [ai]: 
  [tool]: Title: Checkpointer integrations — Link: https://docs.langchain.com/oss/python/int
  [ai]: 
  [tool]: exit: 0 --- stdout --- Persistence LangGraph has a built-in persistence layer th
  [tool]: exit: 0 --- stdout --- Checkpointer integrations Integrate with checkpointer bac
  [ai]: A checkpointer in LangGraph is a persistence layer that allows agents to save an
```

### Reading thread history

`get_history` returns every checkpoint saved during the run — one per node execution. This shows how state evolved step by step through the graph.

```python
# python/m_store/l2/checkpointer.py
history = await client.threads.get_history(thread["thread_id"])
print(f"Checkpointer history — {len(history)} checkpoints saved for this thread")
```

```text
Checkpointer history — 10 checkpoints saved for this thread
```

A single message exchange through `deep_tutor` saves around 10 checkpoints — one for the LLM call, one for each tool call, one for each tool result, and one for the final response.

---

## Next up

Great! Now you have accessed the store and checkpointer using the SDK.

The DeepAgents library has used these basics to build a flexible backend that allows you to choose where your data is stored. It's a good example of using these simple storage options to create a sophisticated resource. Learn more in the next lesson.