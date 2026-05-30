/**
 * Test client for Lesson 4 — run with: pnpm client
 * Requires the server to be running: pnpm dev --no-browser
 */
import "dotenv/config";
import { Client } from "@langchain/langgraph-sdk";

const SUPABASE_URL = process.env.SUPABASE_URL!;
const SUPABASE_PUBLISHABLE_KEY = process.env.SUPABASE_PUBLISHABLE_KEY!;
const URL = "http://127.0.0.1:2024";

const EMAIL1 = "alice+test@example.com";
const EMAIL2 = "bob+test@example.com";
const PASSWORD = "supersecret123";

async function login(email: string, pw: string): Promise<string> {
  // Steps 1-2: send credentials to Supabase, receive a signed JWT
  console.log(`➡️ logging in ${email} via Supabase...`);
  const r = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=password`, {
    method: "POST",
    headers: { apiKey: SUPABASE_PUBLISHABLE_KEY, "Content-Type": "application/json" },
    body: JSON.stringify({ email, password: pw }),
  });
  if (!r.ok) {
    console.log(`❌ login failed for ${email}: ${r.status}`);
    throw new Error(`${r.status}: ${await r.text()}`);
  }
  const data = await r.json() as { access_token: string };
  console.log(`✅ got JWT for ${email}`);
  return data.access_token;
}

async function main() {
  const token1 = await login(EMAIL1, PASSWORD);
  const token2 = await login(EMAIL2, PASSWORD);

  // Step 3: attach the JWT as a Bearer token on every request to the agent server
  const alice = new Client({ apiUrl: URL, defaultHeaders: { Authorization: `Bearer ${token1}` } });
  const bob   = new Client({ apiUrl: URL, defaultHeaders: { Authorization: `Bearer ${token2}` } });

  // Steps 3-8: each call sends the JWT; the server validates it with the auth provider
  // (@auth.authenticate, steps 4-6), applies @auth.on (step 7), and responds (step 8)
  const aliceThread = await alice.threads.create();
  console.log(`✅ Alice created thread: ${aliceThread.thread_id}`);

  try {
    await bob.threads.get(aliceThread.thread_id);  // returns 404 — filtered by @auth.on
    console.log("❌ Bob should not see Alice's thread!");
  } catch (e) {
    const err = e as { status?: number; message?: string };
    const status = err.status ?? "error";
    console.log(`✅ Bob correctly blocked: ${status} — ${err.message ?? e}`);
  }

  const aliceThreads = await alice.threads.search();
  const bobThreads   = await bob.threads.search();
  console.log(`✅ Alice sees ${aliceThreads.length} thread(s)`);
  console.log(`✅ Bob sees ${bobThreads.length} thread(s)`);
}

main().catch(console.error);
