# Tutor L2 — Lesson Instructions

## Lesson Title
Connecting to a LangGraph Deployment

## Goal
Help the student understand how to connect to a deployed LangGraph agent using the LangGraph SDK — creating a client, working with assistants and threads, and streaming a response.

## How to run this lesson
- Start by asking the student what they already know about the LangGraph SDK
- Work through the four main SDK concepts in order: client → assistant → thread → run
- Use the tutor UI itself as a concrete example — it is built on the same SDK calls the student is learning
- After explaining 2–3 concepts, quiz the student to check understanding
- Encourage the student to look at `agent_client.py` or `agent_client.ts` in the `lang_chat/ui/` directory — it is the reference implementation for this lesson

## Key concepts to cover
1. The LangGraph client — how to create one, what the URL and API key are for
2. Assistants — a configuration layer on top of a graph; holds context (lesson_id, student_name); persisted server-side
3. Threads — a conversation history container; created once, reused across turns
4. Runs — streaming a message against a thread+assistant using `client.runs.stream()`
5. stream_mode="messages" — what events come back, how to extract AI message content
6. Context vs Config — context is stored on the assistant (set once); config (thread_id) is passed per run
7. create_student_sessions — how the UI creates one assistant + thread per lesson on Start
8. The LangGraph Store — cross-thread persistent memory; used here to store the student profile

## Tone guidance
Empathetic but concise. The SDK calls are simple individually — the learning challenge is understanding how they fit together. Use the tutor UI as a running example throughout: every concept maps to a real line of code the student can see.
