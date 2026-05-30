/**
 * auth.ts — auth handler for the tutor deployment.
 *
 * Wires Supabase JWT validation (.authenticate) and per-user resource scoping
 * (.on for threads/assistants, .on("store") for the Store namespace) on top
 * of the tutor agent.
 */
import { Auth, HTTPException } from "@langchain/langgraph-sdk/auth";

const SUPABASE_URL = process.env.SUPABASE_URL!;
const SUPABASE_SECRET_KEY = process.env.SUPABASE_SECRET_KEY!;

/** Same conversion used by the UI's emailToNamespace. */
function emailToNamespace(email: string): string {
  return email.replace(/\./g, "_");
}

export const auth = new Auth()
  .authenticate(async (request) => {
    // TS langgraph-api applies @auth.authenticate to ALL routes (including custom
    // /register and /login). Missing token → anonymous user so those routes can
    // run; the .on() handlers below still scope every data access by identity/email.
    const authorization = request.headers.get("Authorization");
    if (!authorization) {
      return { identity: "", email: "", is_authenticated: false, permissions: [] };
    }
    const [scheme] = authorization.split(" ");
    if (scheme?.toLowerCase() !== "bearer") {
      throw new HTTPException(401, { message: "Invalid scheme" });
    }
    try {
      console.log("➡️ @auth.authenticate: calling Supabase to validate token");
      const response = await fetch(`${SUPABASE_URL}/auth/v1/user`, { // Supabase authentication endpoint
        headers: {
          Authorization: authorization,       // verifies the user
          apiKey: SUPABASE_SECRET_KEY,        // authenticates this handler to Supabase
        },
      });
      if (!response.ok) {
        throw new Error(`Supabase returned ${response.status}`);
      }
      const user = await response.json() as { id: string; email: string };
      console.log(`✅ authenticated: ${user.email}`);
      return {
        identity: user.id,
        email: user.email,
        is_authenticated: true,
        permissions: [],
      };
    } catch (e) {
      console.log(`❌ authentication failed: ${e}`);
      throw new HTTPException(401, { message: String(e) });
    }
  })
  // Stamp `owner` on writes; return same filter so reads scope to this user.
  .on(["threads", "assistants"], ({ value, user }) => {
    console.log(`🔒 @auth.on: scoping to owner=${user.identity.slice(0, 8)}...`);
    const filters = { owner: user.identity };
    const v = value as { metadata?: Record<string, unknown> | null };
    v.metadata ??= {};
    (v.metadata as Record<string, unknown>).owner = user.identity;  // written to metadata on write/create actions
    return filters;
  })
  // Only allow access to the namespace matching the caller's email.
  // The UI builds the namespace via email.replace(".", "_") — same here.
  .on("store", ({ value, user }) => {
    const email = (user as unknown as { email?: string }).email ?? "";
    const expected = emailToNamespace(email);
    const namespace = value.namespace;
    console.log(`📦 @auth.on.store: ${email} → namespace[0]=${namespace?.[0]}`);
    if (!namespace || namespace[0] !== expected) {
      throw new HTTPException(403, { message: "Not authorized" });
    }
  });
