/**
 * Test client for Lesson 2 — run with: pnpm client
 * Requires the server to be running: pnpm dev --no-browser
 */
import { Client } from "@langchain/langgraph-sdk";

const URL = "http://localhost:2024";

async function main() {
  // --- Unknown token: not in VALID_TOKENS, should be blocked ---
  const hacker = new Client({
    apiUrl: URL,
    defaultHeaders: { Authorization: "Bearer hacker-token" },
  });
  try {
    await hacker.threads.create();
    console.log("❌ Should have been blocked!");
  } catch (e) {
    console.log(`✅ Unknown token correctly blocked: ${e instanceof Error ? e.message : String(e)}`);
  }

  // --- Valid token (Alice) ---
  const alice = new Client({
    apiUrl: URL,
    defaultHeaders: { Authorization: "Bearer alice-token" },
  });
  const thread = await alice.threads.create();
  console.log(`✅ Alice created thread: ${thread.thread_id}`);

  const result = await alice.runs.wait(thread.thread_id, "agent", {
    input: { messages: [{ role: "user", content: "Hello from Alice!" }] },
  });
  const messages = (result as { messages: Array<{ content: string }> }).messages;
  console.log(`✅ Response: ${messages[messages.length - 1].content}`);

  // --- Valid token (Bob) ---
  const bob = new Client({
    apiUrl: URL,
    defaultHeaders: { Authorization: "Bearer bob-token" },
  });
  const bobThread = await bob.threads.create();
  console.log(`✅ Bob created thread: ${bobThread.thread_id}`);

  // --- Bob can see Alice's thread! No @auth.on means no isolation ---
  const bobView = await bob.threads.search();
  console.log(`⚠️  Bob can see ${bobView.length} thread(s) — including Alice's.`);
  console.log("   Authentication confirmed who Bob is, but didn't scope what he sees.");
  console.log("   m5.3 fixes this with @auth.on.");
}

main().catch(console.error);
