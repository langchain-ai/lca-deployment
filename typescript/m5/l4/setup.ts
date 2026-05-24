/**
 * One-time setup — creates Alice and Bob in your Supabase project.
 * Run with: pnpm setup
 */
import "dotenv/config";

const SUPABASE_URL = process.env.SUPABASE_URL!;
const SUPABASE_ANON_KEY = process.env.SUPABASE_ANON_KEY!;

const EMAIL1 = "alice+test@example.com";
const EMAIL2 = "bob+test@example.com";
const PASSWORD = "supersecret123";

async function signUp(email: string, pw: string) {
  const r = await fetch(`${SUPABASE_URL}/auth/v1/signup`, {
    method: "POST",
    headers: { apiKey: SUPABASE_ANON_KEY, "Content-Type": "application/json" },
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
