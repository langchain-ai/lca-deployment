/**
 * m2.1 — Connecting to your deployment
 *
 * Demonstrates the basic connect → thread → run flow against a deployed agent.
 * Uses the default assistant (graph name "tutor") — no named assistant required.
 *
 * Steps:
 *   1. Connect to your deployment
 *   2. Create a thread
 *   3. Run (wait) against the default assistant
 *   4. Stream the response
 *
 * Documentation:
 *   LangGraph SDK (JS):      https://langchain-ai.github.io/langgraphjs/reference/
 *   Run execution lifecycle: https://docs.langchain.com/langsmith/agent-server#run-execution-lifecycle
 */

import dotenv from "dotenv";
dotenv.config({ override: true });  // expects typescript/.env — loads LANGSMITH_API_KEY
import { Client } from "@langchain/langgraph-sdk";

const urlProvided = process.argv[2] !== undefined;
const DEPLOYMENT_URL = process.argv[2] ?? "http://localhost:2024";
const API_KEY = process.env.LANGSMITH_API_KEY ?? "";

const CHECK = "✅";
const ARROW = "→";

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
console.log(`${CHECK} Connected: ${DEPLOYMENT_URL}`);

// ---------------------------------------------------------------------------
// Step 2: Create a thread
// ---------------------------------------------------------------------------

const thread = await client.threads.create();
console.log(`${CHECK} Thread created: ${thread.thread_id}`);

// ---------------------------------------------------------------------------
// Step 3: Run against the default assistant
//
// "tutor" is the graph name — it doubles as the assistant_id of the default
// assistant that the deployment created for that graph.
// ---------------------------------------------------------------------------

let query = "In one sentence, what is the LangGraph runtime?";
console.log(`\n${ARROW} Running (wait): ${query}`);
const result = await client.runs.wait(thread.thread_id, "tutor", {
  input: { messages: [{ role: "user", content: query }] },
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
  console.log(`${CHECK} Response: ${content ?? ""}`);
}

// ---------------------------------------------------------------------------
// Step 4: Stream the response
// ---------------------------------------------------------------------------

query = "In one sentence, what does the Agent Server include?";
console.log(`\n${ARROW} Running (stream): ${query}`);
process.stdout.write(`${CHECK} Response: `);
const stream = client.runs.stream(thread.thread_id, "tutor", {
  input: { messages: [{ role: "user", content: query }] },
  streamMode: "messages-tuple",
});
for await (const event of stream) {
  if (event.event !== "messages") continue;
  const [messageChunk] = event.data as [Record<string, unknown>, unknown];
  if (messageChunk.type !== "ai") continue;  // skip tool calls / tool results — show only the agent's reply
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
