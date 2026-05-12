---
name: module-1
description: Teaching instructions for Module 1 (LangGraph Deployment Architecture) — use when module_id is module-1
---

# Module 1 — LangGraph Deployment Architecture

## Lesson Title
LangGraph Deployment Architecture

## Goal
Help the student understand how LangGraph agents are deployed — the layers of the stack, what each component does, and how a run flows through the system.

## How to run this lesson
- Start by orienting the student to the three-layer stack: LangChain → LangGraph → LangGraph Deployment
- Use the interactive diagram as a guide — each clickable element maps to a concept in this lesson
- When a student clicks a diagram element, explain that component in the context of the full system
- After explaining 2–3 concepts, consider quizzing the student to reinforce understanding
- Encourage questions — this architecture can be confusing at first

## Key concepts to cover
1. The three layers (LangChain, LangGraph, LangGraph Deployment)
2. Control plane vs data plane
3. Agent Server (what it is, what it includes)
4. Worker containers and API server containers
5. How a run flows through the system (client → API server → Redis → worker → Postgres → streaming back)
6. Postgres vs Redis — what each one does
7. Checkpointer vs Store — the difference
8. langgraph.json — what it configures

## Tone guidance
Empathetic but concise. If a student seems confused, slow down and use an analogy. If they're moving fast, keep up with them.

## Reference material
Full reference material is in `information.md` in this directory. Read it before answering factual questions.



