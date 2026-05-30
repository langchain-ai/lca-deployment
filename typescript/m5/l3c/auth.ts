import { Auth, HTTPException } from "@langchain/langgraph-sdk/auth";

// Stand-in for a real user database. Do not use hardcoded tokens in production.
const VALID_TOKENS: Record<string, { id: string; name: string }> = {
  "alice-token": { id: "user1", name: "Alice" },
  "bob-token":   { id: "user2", name: "Bob" },
  "admin-token": { id: "admin", name: "Admin" },
};

export const auth = new Auth()
  .authenticate(async (request) => {
    // TS langgraph-api runs @auth.authenticate on ALL routes — return an anonymous
    // user for missing tokens so the /ok health check can respond.
    const authorization = request.headers.get("Authorization");
    if (!authorization) {
      return { identity: "", permissions: [] };
    }
    const [scheme, token] = authorization.split(" ");
    if (scheme?.toLowerCase() !== "bearer" || !token || !VALID_TOKENS[token]) {
      throw new HTTPException(401, { message: "Invalid token" });
    }
    return { identity: VALID_TOKENS[token].id, permissions: [] };
  })
  .on("store", ({ value, user }) => {
    if (user.identity === "admin") return;
    const namespace = value.namespace;
    if (!namespace || namespace[0] !== user.identity) {
      throw new HTTPException(403, { message: "Not authorized" });
    }
  });
