import { Auth, HTTPException } from "@langchain/langgraph-sdk/auth";

const SUPABASE_URL = process.env.SUPABASE_URL!;
const SUPABASE_SECRET_KEY = process.env.SUPABASE_SECRET_KEY!;

export const auth = new Auth()
  .authenticate(async (request) => {
    const authorization = request.headers.get("Authorization");
    if (!authorization) {
      throw new HTTPException(401, { message: "Missing token" });
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
  .on(["threads", "assistants"], ({ value, user }) => {
    console.log(`🔒 @auth.on: scoping to owner=${user.identity.slice(0, 8)}...`);
    const filters = { owner: user.identity };
    const v = value as { metadata?: Record<string, unknown> | null };
    v.metadata ??= {};
    (v.metadata as Record<string, unknown>).owner = user.identity;  // written to metadata on write/create actions
    return filters;
  });
