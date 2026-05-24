/**
 * Test client for Lesson 3c — run with: pnpm client
 * Requires the server to be running: pnpm dev --no-browser
 */
import { Client } from "@langchain/langgraph-sdk";

const URL = "http://localhost:2024";

async function main() {
  const alice = new Client({ apiUrl: URL, defaultHeaders: { Authorization: "Bearer alice-token" } });
  const bob   = new Client({ apiUrl: URL, defaultHeaders: { Authorization: "Bearer bob-token" } });
  const admin = new Client({ apiUrl: URL, defaultHeaders: { Authorization: "Bearer admin-token" } });

  // Alice stores a note in her namespace
  await alice.store.putItem(["user1", "notes"], "note1", { content: "Alice's private note" });
  console.log("✅ Alice stored a note");

  // Bob tries to read Alice's note — should be blocked
  try {
    await bob.store.getItem(["user1", "notes"], "note1");
    console.log("❌ Bob should not see Alice's note!");
  } catch (e) {
    console.log(`✅ Bob correctly blocked: ${e instanceof Error ? e.message : String(e)}`);
  }

  // Alice reads her own note
  const item = await alice.store.getItem(["user1", "notes"], "note1");
  const content = (item?.value as { content?: string } | undefined)?.content;
  console.log(`✅ Alice reads her note: ${content}`);

  // Bob stores his own note
  await bob.store.putItem(["user2", "notes"], "note1", { content: "Bob's private note" });
  console.log("✅ Bob stored a note");

  // Admin can read from any namespace
  const aliceItem = await admin.store.getItem(["user1", "notes"], "note1");
  const bobItem   = await admin.store.getItem(["user2", "notes"], "note1");
  const aliceContent = (aliceItem?.value as { content?: string } | undefined)?.content;
  const bobContent   = (bobItem?.value as { content?: string } | undefined)?.content;
  console.log(`✅ Admin reads Alice's note: ${aliceContent}`);
  console.log(`✅ Admin reads Bob's note: ${bobContent}`);
}

main().catch(console.error);
