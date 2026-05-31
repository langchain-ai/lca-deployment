/**
 * One-time setup — creates Alice and Bob in your Supabase project.
 * Run with: pnpm run setup
 */
import dotenv from "dotenv";
dotenv.config({ override: true });

const SUPABASE_URL = process.env.SUPABASE_URL!;
const SUPABASE_PUBLISHABLE_KEY = process.env.SUPABASE_PUBLISHABLE_KEY!;

const EMAIL1 = "alice+test@example.com";
const EMAIL2 = "bob+test@example.com";
const PASSWORD = "supersecret123";

async function signUp(email: string, pw: string) {
  const r = await fetch(`${SUPABASE_URL}/auth/v1/signup`, {
    method: "POST",
    headers: { apiKey: SUPABASE_PUBLISHABLE_KEY, "Content-Type": "application/json" },
    body: JSON.stringify({ email, password: pw }),
  });
  if (!r.ok) {
    throw new Error(`${r.status}: ${await r.text()}`);
  }
  console.log(`✅ Created ${email}`);
}

async function main() {
  await signUp(EMAIL1, PASSWORD);
  await signUp(EMAIL2, PASSWORD);
}

main().catch(console.error);
