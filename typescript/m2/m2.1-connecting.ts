/**
 * m2.1 — Connecting an Assistant to a Deployment
 *
 * Steps:
 *   1. Connect to your deployment
 *   2. List available graphs (to find the graph_id)
 *   3. Create an assistant pointing to your graph
 *   4. Update the assistant with context
 *   5. Create a thread
 *   6a. Run the assistant (non-streaming)
 *   6b. Create assistantM2 and run it streaming — same question, different context
 *   7. Delete both assistants when done
 *
 * Documentation:
 *   LangSmith Assistants:   https://docs.langchain.com/langsmith/assistants
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

const client = new Client({ apiUrl: DEPLOYMENT_URL, apiKey: API_KEY });

// ---------------------------------------------------------------------------
// Step 2: List available assistants/graphs
// ---------------------------------------------------------------------------

const assistants = await client.assistants.search();
console.log("Available assistants/graphs:");
for (const a of assistants) {
  console.log(`  graph_id=${a.graph_id}  assistant_id=${a.assistant_id}  name=${a.name}`);
}

// ---------------------------------------------------------------------------
// Step 3: Create an assistant
// ---------------------------------------------------------------------------

let assistantM1 = await client.assistants.create({
  graphId: "tutor",
  name: "Tutor — Module 1",
  context: {},
});
console.log(`\nCreated assistant: ${assistantM1.assistant_id}  name=${assistantM1.name}`);

// ---------------------------------------------------------------------------
// Step 4: Update the assistant with context
//
// NOTE: When updating, include ALL context fields — not just the ones changing.
// ---------------------------------------------------------------------------

assistantM1 = await client.assistants.update(assistantM1.assistant_id, {
  context: {
    module_id: "module-1",
    store_namespace: "",
  },
});
console.log(`Updated assistant: ${assistantM1.assistant_id}`);

// ---------------------------------------------------------------------------
// Step 5: Create a thread
// ---------------------------------------------------------------------------

const thread = await client.threads.create();
console.log(`\nThread: ${thread.thread_id}`);

// ---------------------------------------------------------------------------
// Step 6a: Run the assistant
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
// Step 6b: Create a second assistant with module 2 context — streaming output
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
// Step 7: Delete both assistants
// ---------------------------------------------------------------------------

await client.assistants.delete(assistantM1.assistant_id);
console.log(`\nDeleted assistantM1: ${assistantM1.assistant_id}`);
await client.assistants.delete(assistantM2.assistant_id);
console.log(`Deleted assistantM2: ${assistantM2.assistant_id}`);
