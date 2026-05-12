/**
 * m2.2 — Assistants and Context
 *
 * Demonstrates creating named assistants with custom context, and how two
 * assistants on the same graph behave differently based on the context bound
 * to each.
 *
 * Steps:
 *   1. Connect to your deployment
 *   2. Create a named assistant (assistantM1) with module-1 context
 *   3. Create a thread
 *   4. Run (wait) — module-1 response
 *   5. Create a second named assistant (assistantM2) with module-2 context +
 *      a new thread + a streamed run — module-2 response
 *   6. Delete both assistants
 *
 * Documentation:
 *   LangSmith Assistants:   https://docs.langchain.com/langsmith/assistants
 *   Create Assistant API:   https://docs.langchain.com/langsmith/agent-server-api/assistants/create-assistant
 *   Patch Assistant API:    https://docs.langchain.com/langsmith/agent-server-api/assistants/patch-assistant
 *   LangGraph SDK (JS):     https://langchain-ai.github.io/langgraphjs/reference/
 */

import "dotenv/config";  // expects typescript/.env — loads LANGSMITH_API_KEY
import { Client } from "@langchain/langgraph-sdk";

const urlProvided = process.argv[2] !== undefined;
const DEPLOYMENT_URL = process.argv[2] ?? "http://localhost:2024";
const API_KEY = process.env.LANGSMITH_API_KEY ?? "";

async function checkConnection(): Promise<void> {
  try {
    const res = await fetch(`${DEPLOYMENT_URL}/ok`, {
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
  } catch (e) {
    if (urlProvided) {
      console.error(`Cannot reach deployment at ${DEPLOYMENT_URL}\nCheck the URL and try again.\n${e}`);
    } else {
      console.error(`Cannot reach local dev server at ${DEPLOYMENT_URL}\nIs \`langgraph dev\` running?\n${e}`);
    }
    process.exit(1);
  }
}

await checkConnection();

// ---------------------------------------------------------------------------
// Step 1: Connect to your deployment
// ---------------------------------------------------------------------------

const client = new Client({ apiUrl: DEPLOYMENT_URL, apiKey: API_KEY });

// ---------------------------------------------------------------------------
// Step 2: Create a named assistant for module 1
//
// Context is stored server-side on the assistant. Every run that uses this
// assistant_id gets module_id and store_namespace injected automatically.
// ---------------------------------------------------------------------------

const assistantM1 = await client.assistants.create({
  graphId: "tutor",
  name: "Tutor — Module 1",
  context: {
    module_id: "module-1",
    store_namespace: "",
  },
});
console.log(`Created assistant: ${assistantM1.assistant_id}  name=${assistantM1.name}`);

// ---------------------------------------------------------------------------
// Step 3: Create a thread
// ---------------------------------------------------------------------------

const thread = await client.threads.create();
console.log(`Thread: ${thread.thread_id}`);

// ---------------------------------------------------------------------------
// Step 4: Run against the named assistant
// ---------------------------------------------------------------------------

const result = await client.runs.wait(thread.thread_id, assistantM1.assistant_id, {
  input: { messages: [{ role: "user", content: "What module is this?" }] },
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
  console.log(content ?? "");
}

// ---------------------------------------------------------------------------
// Step 5: Second assistant with module-2 context — streaming
//
// Same graph, same question. Different context => different answer.
// ---------------------------------------------------------------------------

const assistantM2 = await client.assistants.create({
  graphId: "tutor",
  name: "Tutor — Module 2",
  context: {
    module_id: "module-2",
    store_namespace: "",
  },
});
console.log(`\nCreated assistant: ${assistantM2.assistant_id}  name=${assistantM2.name}`);

const threadM2 = await client.threads.create();
console.log(`Thread: ${threadM2.thread_id}\n`);

const stream = client.runs.stream(threadM2.thread_id, assistantM2.assistant_id, {
  input: { messages: [{ role: "user", content: "What module is this?" }] },
  streamMode: "messages-tuple",
});
for await (const event of stream) {
  if (event.event !== "messages") continue;
  const [messageChunk] = event.data as [Record<string, unknown>, unknown];
  let content = messageChunk.content;
  if (Array.isArray(content)) {
    content = (content as Array<Record<string, unknown>>)
      .filter((b) => b.type === "text")
      .map((b) => b.text ?? "")
      .join("");
  }
  if (typeof content === "string" && content) {
    process.stdout.write(content);
  }
}
console.log();

// ---------------------------------------------------------------------------
// Step 6: Delete both assistants
//
// Frees the configuration records. Does not affect compute or running
// containers — assistants are config only.
// ---------------------------------------------------------------------------

await client.assistants.delete(assistantM1.assistant_id);
console.log(`\nDeleted assistantM1: ${assistantM1.assistant_id}`);
await client.assistants.delete(assistantM2.assistant_id);
console.log(`Deleted assistantM2: ${assistantM2.assistant_id}`);
