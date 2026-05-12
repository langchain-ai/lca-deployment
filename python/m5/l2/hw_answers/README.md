# Lesson 2 Homework — Answer Key

This is a working solution to the Lesson 2 homework. The two changes from the base lesson are:

- **`auth.py`** — returns `name` and `role` in addition to `identity`
- **`agent/graph.py`** — uses `name` and `role` from the user dict in the response

## Run the server

```bash
cd python/m5/l2/hw_answers
langgraph dev --no-browser
```

No `.env` file is needed — this lesson uses no environment variables.

## Run the client

In a second terminal, run the existing lesson client:

```bash
cd python/m5/l2
uv run client.py
```

## Expected output

```
✅ Unknown token correctly blocked: Invalid token
✅ Alice created thread: <thread-id>
✅ Response: [identity=user1, name=Alice, role=student] Hello from Alice!
✅ Bob created thread: <thread-id>
```

The response prints every field in the user dict — whatever you return from `auth.py` shows up automatically. Add more fields and they appear without touching `graph.py`.
