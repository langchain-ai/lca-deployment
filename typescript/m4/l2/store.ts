/**
 * m4 L2 — Part 1: The Store
 *
 * Writes a student profile to the LangGraph Store and reads it back.
 *
 * The Store is cross-thread, deployment-wide persistent storage. Anything
 * written here is immediately visible to all threads and survives redeployment.
 *
 * Run against a local deployment (default) or pass a cloud URL:
 *   npx tsx m4/l2/store.ts
 *   npx tsx m4/l2/store.ts https://tutor-xyz.us.langgraph.app
 */

import "dotenv/config"; // expects typescript/.env — loads LANGSMITH_API_KEY
import { Client } from "@langchain/langgraph-sdk";

const DEPLOYMENT_URL = process.argv[2] ?? "http://localhost:2024";
const API_KEY = process.env.LANGSMITH_API_KEY ?? "";

// Each student's data is stored under their own namespace.
// The deep_tutor UI builds the namespace from the student's email by replacing
// `.` with `_` (e.g. jane@example.com -> "jane@example_com"). Here we use a
// hardcoded "john_doe" namespace as a stand-in.
const NAMESPACE = ["john_doe"];

const PROFILE = {
  first_name: "John",
  last_name: "Doe",
  email: "john@example.com",
  goals: "Understand how LangGraph deployments work end to end.",
};

const client = new Client({ apiUrl: DEPLOYMENT_URL, apiKey: API_KEY });

// ---------------------------------------------------------------------------
// Write the profile to the Store
//
// putItem is an upsert — writing the same namespace + key again overwrites.
// The write is immediately visible to all threads in the deployment.
// ---------------------------------------------------------------------------

await client.store.putItem(NAMESPACE, "profile", PROFILE);
console.log(`Wrote profile to Store under namespace ${JSON.stringify(NAMESPACE)}\n`);

// ---------------------------------------------------------------------------
// Read it back
//
// getItem fetches a single item by namespace + key.
// ---------------------------------------------------------------------------

const item = await client.store.getItem(NAMESPACE, "profile");
console.log("Read back:");
if (item) {
  for (const [k, v] of Object.entries(item.value)) {
    console.log(`  ${k}: ${v}`);
  }
}

// ---------------------------------------------------------------------------
// Search all items in the namespace
//
// searchItems returns everything stored under a namespace prefix.
// Useful for listing all data for a student.
// ---------------------------------------------------------------------------

console.log(`\nAll items in namespace ${JSON.stringify(NAMESPACE)}:`);
const result = await client.store.searchItems(NAMESPACE);
for (const entry of result.items) {
  console.log(`  key=${entry.key}  value=${JSON.stringify(entry.value)}`);
}
