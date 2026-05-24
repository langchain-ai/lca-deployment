/**
 * Test client for Lesson 3 part 2a — run with: pnpm client
 * Requires the server to be running: pnpm dev --no-browser
 */
import { Client } from "@langchain/langgraph-sdk";

const URL = "http://localhost:2024";

async function main() {
  const alice = new Client({ apiUrl: URL, defaultHeaders: { Authorization: "Bearer alice-token" } });
  const bob   = new Client({ apiUrl: URL, defaultHeaders: { Authorization: "Bearer bob-token" } });

  // Alice creates a thread
  const aliceThread = await alice.threads.create();
  console.log(`✅ Alice created thread: ${aliceThread.thread_id}`);

  // Bob tries to access Alice's thread — should get 404
  try {
    await bob.threads.get(aliceThread.thread_id);
    console.log("❌ Bob should not see Alice's thread!");
  } catch (e) {
    const err = e as { status?: number; message?: string };
    const status = err.status ?? "error";
    console.log(`✅ Bob correctly blocked: ${status} — ${err.message ?? e}`);
  }

  // Each user lists only their own threads
  const aliceThreads = await alice.threads.search();
  const bobThreads   = await bob.threads.search();
  console.log(`✅ Alice sees ${aliceThreads.length} thread(s)`);
  console.log(`✅ Bob sees ${bobThreads.length} thread(s)`);
}

main().catch(console.error);
