import { Auth, HTTPException } from "@langchain/langgraph-sdk/auth";

const SUPABASE_URL = process.env.SUPABASE_URL!;
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY!;

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
      const response = await fetch(`${SUPABASE_URL}/auth/v1/user`, { // Supabase authentication endpoint
        headers: {
          Authorization: authorization,       // verifies the user
          apiKey: SUPABASE_SERVICE_KEY,        // authenticates this handler to Supabase
        },
      });
      if (!response.ok) {
        throw new Error(`Supabase returned ${response.status}`);
      }
      const user = await response.json() as { id: string; email: string };
      return {
        identity: user.id,
        email: user.email,
        is_authenticated: true,
        permissions: [],
      };
    } catch (e) {
      throw new HTTPException(401, { message: String(e) });
    }
  })
  .on(["threads", "assistants"], ({ value, user }) => {
    const filters = { owner: user.identity };
    const v = value as { metadata?: Record<string, unknown> | null };
    v.metadata ??= {};
    (v.metadata as Record<string, unknown>).owner = user.identity;  // written to metadata on write/create actions
    return filters;
  });
