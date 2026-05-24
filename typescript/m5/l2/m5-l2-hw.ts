/**
 * Lesson 2 Homework — run with: pnpm hw
 *
 * Part 1: Pass name through the auth pipeline
 * --------------------------------------------
 * Before running, make two small changes:
 *
 *   auth.ts — add `name` to the returned user dict:
 *
 *       return {
 *         identity: VALID_TOKENS[token].id,
 *         name:     VALID_TOKENS[token].name,
 *       };
 *
 *   agent/graph.ts — use name in the response:
 *
 *       const name = (user.name as string) ?? identity;
 *       return { messages: [new AIMessage(`[${name}] ${content}`)] };
 *
 * Part 2: Authentication is not authorization
 * --------------------------------------------
 * No changes needed — just run and observe.
 */
import { Client } from "@langchain/langgraph-sdk";

const URL = "http://localhost:2024";

async function main() {
  const alice = new Client({ apiUrl: URL, defaultHeaders: { Authorization: "Bearer alice-token" } });
  const bob   = new Client({ apiUrl: URL, defaultHeaders: { Authorization: "Bearer bob-token" } });

  // --- Part 1: name flows from auth.ts into the graph ---
  const thread = await alice.threads.create();
  const result = await alice.runs.wait(thread.thread_id, "agent", {
    input: { messages: [{ role: "user", content: "Hello!" }] },
  });
  const messages = (result as { messages: Array<{ content: string }> }).messages;
  console.log(`✅ Part 1 — Alice's response: ${messages[messages.length - 1].content}`);
  console.log("   Expected: [Alice] Hello!  (not [user1] Hello!)");

  // --- Part 2: authentication is not authorization ---
  const aliceThread = await alice.threads.create();
  console.log(`\n   Alice created thread: ${aliceThread.thread_id}`);

  const bobView = await bob.threads.get(aliceThread.thread_id);
  console.log(`✅ Part 2 — Bob read Alice's thread: ${bobView.thread_id}`);
  console.log("   Bob is authenticated as user2, but nothing stopped him reading Alice's data.");
  console.log("   @auth.on — added in the next lesson — is what closes this gap.");
}

main().catch(console.error);
