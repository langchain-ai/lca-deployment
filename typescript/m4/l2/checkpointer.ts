/**
 * m4 L2 — Part 2: The Checkpointer
 *
 * Sends a message to the deep_tutor agent and reads the thread state from
 * the checkpointer after the run completes.
 *
 * The checkpointer is LangGraph's execution log. After every superstep,
 * LangGraph writes the current state (including all messages) to Postgres.
 * From the SDK client, the checkpointer is read-only — LangGraph manages
 * all writes.
 *
 * Run against a local deployment (default) or pass a cloud URL:
 *   npx tsx m4/l2/checkpointer.ts
 *   npx tsx m4/l2/checkpointer.ts https://tutor-xyz.us.langgraph.app
 */

import "dotenv/config"; // expects typescript/.env — loads LANGSMITH_API_KEY
import { Client } from "@langchain/langgraph-sdk";

const DEPLOYMENT_URL = process.argv[2] ?? "http://localhost:2024";
const API_KEY = process.env.LANGSMITH_API_KEY ?? "";

const client = new Client({ apiUrl: DEPLOYMENT_URL, apiKey: API_KEY });

// ---------------------------------------------------------------------------
// Create an assistant and thread
//
// An assistant is a named configuration on top of a graph.
// A thread is a conversation — the checkpointer saves state per thread.
// ---------------------------------------------------------------------------

const assistant = await client.assistants.create({
  graphId: "tutor",
  name: "checkpointer-exercise",
  context: {
    module_id: "module-1",
    student_name: "Jane Doe",
    store_namespace: "jane_doe",
  },
});
const thread = await client.threads.create();
console.log(`Assistant: ${assistant.assistant_id}`);
console.log(`Thread:    ${thread.thread_id}\n`);

// ---------------------------------------------------------------------------
// Send a message and wait for the response
// ---------------------------------------------------------------------------

const result = await client.runs.wait(thread.thread_id, assistant.assistant_id, {
  input: { messages: [{ role: "user", content: "What is the checkpointer in LangGraph?" }] },
});

const messages = (result as Record<string, unknown[]>).messages ?? [];
if (messages.length > 0) {
  const last = messages[messages.length - 1] as Record<string, unknown>;
  let content = last.content;
  if (Array.isArray(content)) {
    content = (content as Array<Record<string, unknown>>)
      .filter((b) => b.type === "text")
      .map((b) => b.text ?? "")
      .join("");
  }
  console.log(`Agent response (truncated):\n${String(content).slice(0, 300)}...\n`);
}

// ---------------------------------------------------------------------------
// Read thread state from the checkpointer
//
// getState returns the last checkpoint — the full state after the final node.
// values["messages"] contains the complete message history for this thread.
// ---------------------------------------------------------------------------

const state = await client.threads.getState(thread.thread_id);
const stateMessages = ((state.values as Record<string, unknown>)?.messages ?? []) as Array<Record<string, unknown>>;
console.log(`Checkpointer — thread has ${stateMessages.length} messages:`);
for (const msg of stateMessages) {
  const role = msg.type ?? msg.role ?? "?";
  let content = msg.content;
  if (Array.isArray(content)) {
    content = (content[0] as Record<string, unknown>)?.text ?? "";
  }
  console.log(`  [${role}]: ${String(content).slice(0, 80)}`);
}

// ---------------------------------------------------------------------------
// Read thread history
//
// getHistory returns all checkpoints ever saved for this thread —
// one per superstep. Shows how state evolved step by step.
// ---------------------------------------------------------------------------

const history = await client.threads.getHistory(thread.thread_id);
console.log(`\nCheckpointer history — ${history.length} checkpoints saved for this thread`);

// ---------------------------------------------------------------------------
// Clean up
// ---------------------------------------------------------------------------

await client.assistants.delete(assistant.assistant_id);
console.log(`\nDeleted assistant ${assistant.assistant_id}`);
